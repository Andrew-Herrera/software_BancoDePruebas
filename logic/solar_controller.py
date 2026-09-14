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
    def __init__(self, db_manager, file_manager, keithley_driver=None):
        self.db = db_manager
        self.file_manager = file_manager
        self.driver = keithley_driver
        self.active_worker = None

    def start_sweep_execution(self, params: dict, parent_ui=None):
        """Instancia el worker de adquisición. Delega el inicio a la vista."""
        compliance = float(params.get("compliance", 0.05))
        if hasattr(self, 'driver') and self.driver and getattr(self.driver, 'is_connected', False):
            self.driver.set_protection(compliance=compliance)

        self.active_worker = InstrumentWorker(controller=self, params=params, parent=parent_ui)
        return self.active_worker

    def calculate_metrics(self, v_list: list, i_list: list, area_cm2: float, irradiance: float) -> dict:
        """Calcula métricas fotovoltaicas puras filtrando fallos matemáticos."""
        metrics = {"voc": None, "jsc": None, "isc": None, "ff": None, "eta": None}
        
        if pv_analytics and hasattr(pv_analytics, 'calculate_pv_parameters'):
            try:
                i_arr = np.array(i_list)
                i_calc = i_arr if np.mean(i_arr) < 0 else -i_arr 
                
                calc = pv_analytics.calculate_pv_parameters(
                    voltage=[float(x) for x in v_list], 
                    current=[float(x) for x in i_calc.tolist()], 
                    area_cm2=float(area_cm2),
                    irradiance_w_m2=float(irradiance)
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