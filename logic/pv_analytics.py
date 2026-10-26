# logic/pv_analytics.py
import numpy as np
import random
from typing import Dict, Any

def calculate_pv_parameters(
    voltage: list, 
    current: list, 
    area_cm2: float = 0.09, 
    irradiance_w_m2: float = 1000.0
) -> Dict[str, float]:
    """
    Capa Analítica: Calcula las figuras de mérito fotovoltaicas.
    Soporta polaridad invertida, interpola cruces por cero y preserva valores ultra bajos.
    """
    nan_dict = {"voc": np.nan, "isc": np.nan, "jsc": np.nan, "ff": np.nan, "eta": np.nan, "pmax": np.nan}
    
    try:
        v_raw = np.array(voltage, dtype=float)
        i_raw = np.array(current, dtype=float)
        
        if len(v_raw) < 5 or len(i_raw) < 5:
            return nan_dict

        # 1. Pmax y Eficiencia (Independientes de los cruces por cero)
        # Se calcula la potencia absoluta en todos los cuadrantes para soportar cualquier polaridad
        p_array = np.abs(v_raw * i_raw)
        pmax = float(np.max(p_array))
        
        p_in = (irradiance_w_m2 / 10000.0) * area_cm2
        eta = (pmax / p_in) * 100.0 if p_in > 0 else 0.0

        # 2. Corriente de Cortocircuito (Isc) mediante interpolación real
        # Ordenamos respecto al voltaje para garantizar una interpolación matemática válida
        sort_v_idx = np.argsort(v_raw)
        v_sorted = v_raw[sort_v_idx]
        i_sorted_by_v = i_raw[sort_v_idx]

        has_isc = (np.min(v_sorted) * np.max(v_sorted)) <= 0
        if has_isc:
            isc = np.abs(np.interp(0.0, v_sorted, i_sorted_by_v))
            jsc = (isc * 1000.0) / area_cm2
        else:
            isc, jsc = np.nan, np.nan

        # 3. Voltaje de Circuito Abierto (Voc) mediante interpolación real
        # Ordenamos respecto a la corriente para interpolar el voltaje en I=0
        sort_i_idx = np.argsort(i_raw)
        i_sorted = i_raw[sort_i_idx]
        v_sorted_by_i = v_raw[sort_i_idx]

        has_voc = (np.min(i_sorted) * np.max(i_sorted)) <= 0
        if has_voc:
            voc = np.abs(np.interp(0.0, i_sorted, v_sorted_by_i))
        else:
            voc = np.nan

        # 4. Factor de Llenado (FF)
        # Solo calculable si existen cruces por cero válidos
        if not np.isnan(voc) and not np.isnan(isc) and (voc * isc) > 0:
            ff = (pmax / (voc * isc)) * 100.0
        else:
            ff = np.nan

        return {
            "voc": float(voc) if not np.isnan(voc) else np.nan,
            "isc": float(isc) if not np.isnan(isc) else np.nan,
            "jsc": float(jsc) if not np.isnan(jsc) else np.nan,
            "ff": float(ff) if not np.isnan(ff) else np.nan,
            "eta": float(eta) if not np.isnan(eta) else np.nan,
            "pmax": float(pmax) if not np.isnan(pmax) else np.nan
        }
        
    except Exception as e:
        print(f"Error Analítico PV: {e}")
        return nan_dict

def generate_demo_point(voltage: float, degradation: float = 1.0) -> float:
    """
    Simulador Matemático Aislado.
    Genera curvas J-V ideales de celdas orgánicas usando la ecuación de Shockley.
    """
    isc_simulated = 0.0145 * degradation  # ~14.5 mA Corriente 
    voc_simulated = 0.685                 # ~685 mV Voltaje
    
    current_theoretical = isc_simulated * (1.0 - np.exp((voltage - voc_simulated) / 0.0259))
    noise = np.random.normal(0, 0.00005)
    return float(current_theoretical + noise)