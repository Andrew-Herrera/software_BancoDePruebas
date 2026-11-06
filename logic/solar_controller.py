# logic/solar_controller.py
import numpy as np
import math
import traceback

# Importación segura de analíticas
try:
    from logic import pv_analytics
except Exception as e:
    print("CRÍTICO: No se pudo importar pv_analytics.py")
    traceback.print_exc()
    pv_analytics = None

from logic.instrument_worker import InstrumentWorker

class SolarController:
    """Capa Lógica: Gestiona la comunicación entre UI, Hardware y Almacenamiento."""
    def __init__(self, db_manager, file_manager, keithley_driver=None, motor=None, thermal=None):
        self.db = db_manager
        self.file_manager = file_manager
        self.driver = keithley_driver
        self.motor = motor
        self.thermal = thermal
        self.active_worker = None

    def start_sweep_execution(self, params: dict, parent_ui=None):
        """Prepara el hardware y crea el worker de adquisición."""

        config = self.file_manager.load_json_config()
        demo_mode = config.get("demo_mode", True)

        if not demo_mode:
            if not self.driver or not self.driver.is_connected:
                raise RuntimeError(
                    "La Keithley 2401 no está conectada. "
                    "Conecta y verifica el instrumento antes de iniciar."
                )

        self.active_worker = InstrumentWorker(
            controller=self,
            params=params,
            parent=parent_ui
        )

        return self.active_worker

    def calculate_metrics(self, v_list: list, i_list: list, area_cm2: float, irradiance: float) -> dict:
        """Calcula métricas fotovoltaicas puras filtrando fallos matemáticos."""
        metrics = {"voc": None, "jsc": None, "isc": None, "ff": None, "eta": None}
        
        if pv_analytics and hasattr(pv_analytics, 'calculate_pv_parameters'):
            try:
                i_arr = np.array(i_list)
                i_calc = i_arr if np.mean(i_arr) < 0 else -i_arr 
                
                config = self.file_manager.load_json_config()
                polarity = config.get("graph_polarity", "Direct")

                calc = pv_analytics.calculate_pv_parameters(
                    voltage=[float(x) for x in v_list],
                    current=[float(x) for x in i_list], # Crudos
                    area_cm2=float(area_cm2),
                    irradiance_w_m2=float(irradiance),
                    polarity=polarity # Se pasa a la capa analítica
                )

                if calc:
                    for k, v in calc.items():
                        clean_val = v
                        if v is None or (isinstance(v, float) and math.isnan(v)):
                            clean_val = None
                        metrics[k.lower()] = clean_val
                        
            except Exception as calc_err:
                print("\n--- AVISO: Fallo interno en pv_analytics.py ---")
                print(f"Motivo: {calc_err}")
        return metrics

    def delete_experiments(self, exp_ids: list) -> bool:
        if hasattr(self, 'db'):
            return self.db.delete_experiments(exp_ids)
        return False
        
    def export_report(self, filepath: str, meta_file: dict, curves_points: dict, curves_metrics: dict) -> bool:
        if filepath.endswith('.csv'):
            return self.file_manager.write_csv_report(filepath, meta_file, curves_points, curves_metrics)
        elif filepath.endswith('.xlsx'):
            return self.file_manager.write_excel_report(filepath, meta_file, curves_points, curves_metrics)
        return False

    def save_settings(self, config_dict: dict):
        self.file_manager.save_json_config(config_dict)

    def get_full_history(self):
        return self.db.get_full_history()

    def get_historical_metrics(self, exp_id: int):
        meta = self.db.get_experiment_meta(exp_id)
        if not meta: return {}
        return {
            "voc": meta.get("voc"), "isc": meta.get("isc"), 
            "jsc": meta.get("jsc"), "ff": meta.get("ff"), "eta": meta.get("eficiencia")
        }

    def calculate_motor_steps(self, target_irradiance: float) -> int:
        """
        Calcula la posición del motor en pasos para alcanzar la irradiancia objetivo.
        Soporta modo 'Tabla' (interpolación) o 'Ecuacion'.
        """
        if target_irradiance <= 0:
            return 0 # Si pide oscuridad, se envía el motor a Home.
        
        config = self.file_manager.load_json_config()
        # z_limit representa la posición focal guardada por el usuario, que 
        # asumiremos es el punto óptimo para 1 Sol (1000 W/m2).
        z_limit = int(config.get("z_focus", 20000)) 
        calc_mode = config.get("calib_mode", "Tabla (Interpolación)")
        
        if "Tabla" in calc_mode:
            calib_data = self.db.get_calibration_data() 
            if not calib_data:
                print("No hay datos de calibración. Usando límite Z focal por defecto.")
                raise RuntimeError("No hay tabla de calibración guardada. Realiza el barrido óptico primero.")
                
            pasos_arr = np.array([row['numero_pasos'] for row in calib_data])
            irr_arr = np.array([row['irradiancia_medida'] for row in calib_data])
            
            sort_idx = np.argsort(irr_arr)
            target_steps = np.interp(target_irradiance, irr_arr[sort_idx], pasos_arr[sort_idx])
            
            return max(0, int(target_steps))
            
        else:
            # --- MODO ECUACIÓN (Caracterización Óptica FHL-102) ---
            P = 0.004          # Paso del husillo de bolas (4 mm/rev) en metros
            steps_rev = int(config.get("motor_steps_rev", 3200))
            PASOS_POR_METRO = steps_rev / P 
            
            H_1SOL = 0.04915   # 49.15 mm de distancia focal caracterizada
            K_OPT = 1500.0
            N_EXP = 1.85
            H0_OFFSET = 0.02
            
            if target_irradiance == 1000.0:
                h_destino = H_1SOL
            else:
                # Limitamos G para evitar raíces negativas o divisiones por cero
                g_safe = max(1.0, target_irradiance)
                h_destino = (K_OPT / g_safe)**(1.0 / N_EXP) - H0_OFFSET
                
            # Calculamos la diferencia de altura respecto al foco calibrado (1 Sol).
            # Si h_destino > H_1SOL (ej. 500 W/m2), delta_h es positivo (estamos más lejos).
            delta_h = h_destino - H_1SOL
            
            # Convertimos la diferencia lineal en pasos. 
            # Como acercar la celda (distancia menor) requiere pasos positivos (subir),
            # restamos la diferencia multiplicada por la constante mecánica.
            target_steps = z_limit + int(round(-delta_h * PASOS_POR_METRO))
            
            # Limitamos el mínimo a 0 para no estrellar el mecanismo contra la base
            return max(0, target_steps)