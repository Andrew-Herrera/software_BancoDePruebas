# logic/instrument_worker.py
import time, random
import numpy as np
from PySide6.QtCore import QThread, Signal

class InstrumentWorker(QThread):
    point_received = Signal(int, str, float, float)
    sweep_changed = Signal(int, str)
    finished = Signal(object, object, bool)
    error = Signal(str)

    def __init__(self, controller, params: dict, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.params = params
        self.is_running = True
        self.is_demo = self.controller.file_manager.load_json_config().get("demo_mode", True)

    def run(self):
        try:
            v_start = self.params.get("v_start", -0.2)
            v_stop = self.params.get("v_stop", 1.2)
            samples = self.params.get("samples", 100)
            delay = self.params.get("delay", 0.05)
            
            # Nueva lógica: Ciclos físicos reales
            n_cycles = self.params.get("n_cycles", 1)
            interval = self.params.get("interval", 5.0)
            hysteresis = self.params.get("hysteresis", False)
            stress_mode = self.params.get("stress_mode", False)
            v_bias = self.params.get("v_bias", 0.0)
            
            if not self.is_demo and hasattr(self.controller, 'driver') and self.controller.driver:
                self.controller.driver.enable_output()

            v_fwd = np.linspace(v_start, v_stop, samples)
            v_rev = np.linspace(v_stop, v_start, samples)

            all_curves = {}
            start_time = time.time()
            
            sweep_idx = 1 # Contador global de trazos para la gráfica

            for cycle in range(1, n_cycles + 1):
                if not self.is_running: break
                
                # --- 1. BARRIDO DE IDA (FWD) ---
                self.sweep_changed.emit(sweep_idx, "Fwd")
                current_sweep_data = []
                for v in v_fwd:
                    if not self.is_running: break
                    if self.is_demo:
                        i_meas = 0.015 - 1e-9 * (np.exp(v / 0.0259) - 1) + random.uniform(-2e-5, 2e-5)
                        time.sleep(delay / 5.0)
                    else:
                        self.controller.driver.set_voltage(v)
                        time.sleep(delay)
                        i_meas = self.controller.driver.read_current()
                    current_sweep_data.append((v, i_meas))
                    self.point_received.emit(sweep_idx, "Fwd", float(v), float(i_meas))

                if self.is_running and current_sweep_data:
                    all_curves[sweep_idx] = current_sweep_data
                sweep_idx += 1

                # --- 2. BARRIDO DE VUELTA INMEDIATO (REV) ---
                if hysteresis and self.is_running:
                    self.sweep_changed.emit(sweep_idx, "Rev")
                    current_sweep_data = []
                    for v in v_rev:
                        if not self.is_running: break
                        if self.is_demo:
                            i_meas = 0.015 - 1e-9 * (np.exp(v / 0.0259) - 1) + random.uniform(-2e-5, 2e-5)
                            time.sleep(delay / 5.0)
                        else:
                            self.controller.driver.set_voltage(v)
                            time.sleep(delay)
                            i_meas = self.controller.driver.read_current()
                        current_sweep_data.append((v, i_meas))
                        self.point_received.emit(sweep_idx, "Rev", float(v), float(i_meas))

                    if self.is_running and current_sweep_data:
                        all_curves[sweep_idx] = current_sweep_data
                    sweep_idx += 1

                # --- 3. APLICACIÓN DE ESTRÉS O ESPERA ---
                # Se aplica el v_bias ÚNICAMENTE entre ciclos, nunca durante el barrido de medición.
                if cycle < n_cycles and self.is_running:
                    if stress_mode and not self.is_demo:
                        self.controller.driver.set_voltage(v_bias)
                    elif not self.is_demo:
                        self.controller.driver.set_voltage(0.0) # Reposo a 0V para barridos rápidos
                        
                    self._wait_interval(interval)

            self._safe_shutdown()
            elapsed = time.time() - start_time
            self.finished.emit(all_curves, {"min": 0, "max": elapsed, "avg": elapsed/n_cycles}, not self.is_running)

        except Exception as e:
            self.error.emit(str(e))
            self._safe_shutdown()

    def _wait_interval(self, seconds: float):
        start = time.time()
        while time.time() - start < seconds:
            if not self.is_running: break
            time.sleep(0.1)

    def _safe_shutdown(self):
        if not self.is_demo and hasattr(self.controller, 'driver') and getattr(self.controller.driver, 'is_connected', False):
            try:
                self.controller.driver.set_voltage(0.0)
                self.controller.driver.disable_output()
            except Exception:
                pass

    def stop(self):
        self.is_running = False