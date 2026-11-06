# logic/pv_analytics.py
import numpy as np
import random
from typing import Dict, Any

def calculate_pv_parameters(
    voltage: list, current: list, area_cm2: float = 0.09, 
    irradiance_w_m2: float = 1000.0, polarity: str = "Direct"
) -> Dict[str, float]:
    nan_dict = {"voc": np.nan, "isc": np.nan, "jsc": np.nan, "ff": np.nan, "eta": np.nan, "pmax": np.nan}
    try:
        v_raw = np.array(voltage, dtype=float)
        i_raw = np.array(current, dtype=float)
        
        if len(v_raw) < 5 or len(i_raw) < 5: return nan_dict
        
        # 1. Convención de Corriente Única Explícita
        # Si polarity es Direct (Generador en Cuadrante I de la gráfica), I debe ser positiva.
        # Físicamente la celda entrega corriente, por lo que SMU mide negativo. Lo invertimos.
        if polarity.startswith("Direct"):
            i_calc = -i_raw 
        else:
            i_calc = i_raw
            
        # 2. Búsqueda secuencial de cruces por cero (evita errores por ordenamiento)
        voc, isc = np.nan, np.nan
        
        # Buscar Voc (cruce de corriente por 0)
        for i in range(len(i_calc) - 1):
            if (i_calc[i] * i_calc[i+1]) <= 0:
                # Interpolación lineal simple entre puntos adyacentes
                m = (v_raw[i+1] - v_raw[i]) / (i_calc[i+1] - i_calc[i]) if (i_calc[i+1] - i_calc[i]) != 0 else 0
                voc = v_raw[i] + m * (0 - i_calc[i])
                break
                
        # Buscar Isc (cruce de voltaje por 0)
        for i in range(len(v_raw) - 1):
            if (v_raw[i] * v_raw[i+1]) <= 0:
                m = (i_calc[i+1] - i_calc[i]) / (v_raw[i+1] - v_raw[i]) if (v_raw[i+1] - v_raw[i]) != 0 else 0
                isc = i_calc[i] + m * (0 - v_raw[i])
                break

        jsc = (isc * 1000.0) / area_cm2 if not np.isnan(isc) else np.nan

        # 3. Potencia máxima delimitada al cuadrante de generación fotovoltaica
        # Solo calculamos potencia donde V e I_calc son ambos positivos (Generación PV)
        power_array = v_raw * i_calc
        generative_power = power_array[(v_raw >= 0) & (i_calc >= 0)]
        
        pmax = float(np.max(generative_power)) if len(generative_power) > 0 else np.nan
        
        p_in = (irradiance_w_m2 / 10000.0) * area_cm2
        eta = (pmax / p_in) * 100.0 if (p_in > 0 and not np.isnan(pmax)) else np.nan
        
        # 4. Factor de Llenado Físicamente Consistente
        ff = np.nan
        if not np.isnan(voc) and not np.isnan(isc) and not np.isnan(pmax):
            if (voc * isc) > 0:
                ff = (pmax / (voc * isc)) * 100.0
                if ff > 100.0 or ff < 0: 
                    ff = np.nan # Límite físico: celda ideal = 100%

        return {
            "voc": float(voc), "isc": float(isc), "jsc": float(jsc),
            "ff": float(ff), "eta": float(eta), "pmax": float(pmax)
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