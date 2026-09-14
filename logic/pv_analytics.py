# logic/pv_analytics.py
import numpy as np
from typing import Dict, Any

def calculate_pv_parameters(
    voltage: list, 
    current: list, 
    area_cm2: float = 0.09, 
    irradiance_w_m2: float = 1000.0
) -> Dict[str, float]:
    """
    Logic/Analytics Layer: Calculates PV Merit Figures (Voc, Isc, Jsc, FF, Eta, Pmax).
    Includes zero-crossing validation and 4th-quadrant physical filtering.
    """
    nan_dict = {"voc": np.nan, "isc": np.nan, "jsc": np.nan, "ff": np.nan, "eta": np.nan, "pmax": np.nan}
    
    try:
        v_raw = np.array(voltage, dtype=float)
        i_raw = np.array(current, dtype=float)
        
        # Minimum points validation
        if len(v_raw) < 5 or len(i_raw) < 5:
            return nan_dict

        # --- ZERO-CROSSING VALIDATION ---
        has_isc = (np.min(v_raw) * np.max(v_raw)) <= 0
        has_voc = (np.min(i_raw) * np.max(i_raw)) <= 0

        # Work with absolute magnitudes for power & sign-invariant processing
        v = v_raw.copy()
        i = np.abs(i_raw.copy())

        # Sort by voltage monotonically
        sort_indices = np.argsort(v)
        v = v[sort_indices]
        i = i[sort_indices]

        # 1. Short-Circuit Current (Isc & Jsc at V = 0)
        if has_isc:
            isc = float(np.abs(np.interp(0.0, v, i)))
            jsc = float((isc * 1000.0) / area_cm2)  # mA/cm²
        else:
            isc, jsc = np.nan, np.nan

        # 2. Open-Circuit Voltage (Voc at I = 0)
        if has_voc:
            # Interpolate Voltage as a function of Current using absolute distance to zero
            zero_i_idx = np.argmin(i)
            # Interpolate around the minimum current point
            voc = float(np.abs(v[zero_i_idx]))
        else:
            voc = np.nan

        # 3. Maximum Power Point (Pmax), Fill Factor (FF), and Efficiency (Eta)
        if has_isc and has_voc and not np.isnan(voc) and not np.isnan(isc):
            # Restrict search strictly to the power generation quadrant (0 <= V <= Voc)
            gen_mask = (v >= 0.0) & (v <= voc)
            if np.any(gen_mask):
                p_curve = np.abs(v[gen_mask] * i[gen_mask])
                pmax = float(np.max(p_curve))
            else:
                pmax = 0.0

            denominator_ff = voc * isc
            ff = (pmax / denominator_ff) * 100.0 if denominator_ff > 1e-9 else 0.0
            
            # Pin (Watts) = (Irradiance W/m² / 10000 cm²/m²) * Active Area (cm²)
            p_in = (irradiance_w_m2 / 10000.0) * area_cm2
            eta = (pmax / p_in) * 100.0 if p_in > 0 else 0.0

            # Physical Boundaries & Dark Curve Filtering
            if ff > 100.0 or ff < 0.0: 
                ff = 0.0
            if eta > 100.0 or eta < 0.0: 
                eta = 0.0
            if pmax <= 0.0 or isc <= 1e-9:
                pmax, ff, eta = 0.0, 0.0, 0.0
        else:
            pmax, ff, eta = np.nan, np.nan, np.nan

        return {
            "voc": round(float(voc), 4) if not np.isnan(voc) else np.nan,
            "isc": round(float(isc), 6) if not np.isnan(isc) else np.nan,
            "jsc": round(float(jsc), 2) if not np.isnan(jsc) else np.nan,
            "ff": round(float(ff), 2) if not np.isnan(ff) else np.nan,
            "eta": round(float(eta), 2) if not np.isnan(eta) else np.nan,
            "pmax": round(float(pmax), 6) if not np.isnan(pmax) else np.nan
        }
        
    except Exception as e:
        print(f"PV Analytics Error: {e}")
        return nan_dict