# logic/calibration_worker.py
import time
from PySide6.QtCore import QThread, Signal

class CalibrationWorker(QThread):
    """Ejecuta el barrido óptico automatizado para mapear la Irradiancia vs Pasos."""
    
    progress = Signal(int, int, str) # (pasos_actuales, pasos_totales, mensaje)
    finished = Signal(bool)
    error = Signal(str)

    def __init__(self, controller, z_limit: int, step_increment: int = 800, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.z_limit = z_limit
        self.step_increment = step_increment 
        self.is_running = True

    def run(self):
        try:
            motor = getattr(self.controller, "motor", None)
            driver = getattr(self.controller, "driver", None)
            
            if not motor or not driver:
                raise RuntimeError("El hardware (Motor o Keithley) no está inicializado.")
            
            # 1. Posicionamiento en el límite lejano
            self.progress.emit(0, self.z_limit, "Haciendo Home...")
            motor.home()
            
            # 2. Configurar Keithley como Amperímetro (Polarización 0V)
            # Esto asume que el BPW20RF está conectado en polaridad directa.
            driver.set_bias_voltage(0.0) 
            
            calibration_data = []
            current_steps = 0
            
            # NOTA METROLÓGICA: Factor de conversión de Amperes a W/m².
            # Necesitas colocar aquí el factor real de tu sensor BPW20RF.
            # Ejemplo ficticio: Si 1 Sol (1000 W/m²) produce 5 mA (0.005 A), el factor es 200,000.
            conversion_factor = 200000.0 
            
            # 3. Barrido Espacial
            while current_steps <= self.z_limit and self.is_running:
                self.progress.emit(current_steps, self.z_limit, f"Midiendo a {current_steps} pasos...")
                
                # Medimos corriente permitiendo que el instrumento se estabilice
                v_meas, i_meas = driver.measure_iv_point(0.0, delay_s=0.2)
                
                corriente_abs = abs(i_meas)
                irradiancia = corriente_abs * conversion_factor
                
                calibration_data.append((current_steps, irradiancia, corriente_abs))
                
                # Mover al siguiente punto
                next_step = current_steps + self.step_increment
                if next_step <= self.z_limit:
                    motor.move_to_z(next_step)
                    current_steps = next_step
                else:
                    break
                    
            # 4. Apagado y Guardado
            driver.disable_output()
            
            if self.is_running:
                self.controller.db.save_calibration_data(calibration_data)
                
                # Actualizar la fecha de calibración en la configuración
                from datetime import datetime
                config = self.controller.file_manager.load_json_config()
                config["last_calib"] = datetime.now().strftime("%Y-%m-%d")
                self.controller.file_manager.save_json_config(config)
                
                self.finished.emit(True)
            else:
                self.finished.emit(False) # Fue cancelado por el usuario
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if driver:
                driver.disable_output()
    def stop(self):
        self.is_running = False