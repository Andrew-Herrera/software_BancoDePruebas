# utils/text.py

TEXTS = {
    "Español": {
        "title": "Sistema de Caracterización J-V - UPIITA",
        "institutional_lbl": "Laboratorio de Dispositivos Orgánicos - UPIITA IPN",
        
        # Pestañas y Grupos
        "group_common": "Parámetros Comunes de Barrido",
        "tab_fast": "Barridos Rápidos",
        "tab_stress": "Pruebas de Estrés",
        
        # Labels de Parámetros
        "irr": "Irradiancia:",
        "start_v": "V Inicial [V]:",
        "stop_v": "V Final [V]:",
        "samples": "Muestras:",
        "delay": "Delay [s]:",
        "compliance": "Compliance [A]:",
        "nplc": "NPLC (Ciclos):",
        "hist": "Activar Histéresis",
        
        "n_sweeps": "Barridos:",
        "interval": "Intervalo [s]:",
        "duration": "Duración [h]:",
        "b_per_hr": "Barridos/Hr:",
        "v_bias": "V Bias [V]:",
        
        # Botones y Status
        "start_btn": "INICIAR PRUEBA",
        "cancel_btn": "CANCELAR",
        "stopping": "DETENIENDO...",
        "btn_export": "Exportar Datos",
        "compare_btn": "Historial SQL",
        "btn_config": "Config",
        "btn_gestor": "📊 Gestor de Curvas",
        "btn_auto": "⛶ Auto-Escalar",
        
        "status_lbl": "Estado:",
        "demo_lbl": "MODO DEMO ACTIVE",
        "connected": "Conectado",
        "disconnected": "DESCONECTADO",
        "time": "Tiempo est.:",
        
        # Gráfica y Diálogos
        "graph_v": "Tensión Aplicada (V)",
        "graph_i": "Corriente Medida (A)",
        "alert_acq_title": "Adquisición Finalizada",
        "alert_acq_msg": "El barrido ha concluido exitosamente.",
        "alert_error_title": "Error de Hardware",
        "alert_no_data_title": "Gestor de Curvas",
        "alert_no_data_msg": "No hay curvas activas en el lienzo.",
        "alert_export_empty": "No hay datos visibles para exportar.",
        
        # Diálogos Internos
        "curves_mgr_title": "Gestor y Filtro de Curvas",
        "select_all": "Seleccionar / Limpiar Todas",
        "btn_accept": "Aceptar",
        "btn_connect": "Conectar Hardware",
        "btn_disconnect": "Desconectar Hardware",
        "btn_calib": "Protocolo de Calibración",
        "exp_grp1": "Trazos a Exportar (Visibles en Gráfica)",
        "exp_grp2": "Datos de la Celda Orgánica",
        "exp_grp3": "Opciones de Destino y Formato",
        "col_isc": "Isc [mA]"
    },
    "English": {
        "title": "J-V Characterization System - UPIITA",
        "institutional_lbl": "Organic Devices Laboratory - UPIITA IPN",
        
        "group_common": "Common Sweep Parameters",
        "tab_fast": "Fast Sweeps",
        "tab_stress": "Stress Tests",
        
        "irr": "Irradiance:",
        "start_v": "V Start [V]:",
        "stop_v": "V Stop [V]:",
        "samples": "Samples:",
        "delay": "Delay [s]:",
        "compliance": "Compliance [A]:",
        "nplc": "NPLC (Cycles):",
        "hist": "Enable Hysteresis",
        
        "n_sweeps": "No. Sweeps:",
        "interval": "Interval [s]:",
        "duration": "Duration [h]:",
        "b_per_hr": "Sweeps/Hr:",
        "v_bias": "V Bias [V]:",
        
        "start_btn": "START TEST",
        "cancel_btn": "CANCEL",
        "stopping": "STOPPING...",
        "btn_export": "Export Data",
        "compare_btn": "SQL History",
        "btn_config": "Config",
        "btn_gestor": "📊 Curve Manager",
        "btn_auto": "⛶ Auto-Range",
        
        "status_lbl": "Status:",
        "demo_lbl": "DEMO MODE ACTIVE",
        "connected": "Connected",
        "disconnected": "DISCONNECTED",
        "time": "Est. Time:",
        
        "graph_v": "Applied Voltage (V)",
        "graph_i": "Measured Current (A)",
        "alert_acq_title": "Acquisition Complete",
        "alert_acq_msg": "The sweep has finished successfully.",
        "alert_error_title": "Hardware Error",
        "alert_no_data_title": "Curve Manager",
        "alert_no_data_msg": "No active curves on the canvas.",
        "alert_export_empty": "No visible data available to export.",
        
        "curves_mgr_title": "Curve Manager and Filter",
        "select_all": "Select / Clear All",
        "btn_accept": "Accept",
        "btn_connect": "Connect Hardware",
        "btn_disconnect": "Disconnect Hardware",
        "btn_calib": "Calibration Protocol",
        "exp_grp1": "Sweeps to Export (Visible on Graph)",
        "exp_grp2": "Organic Cell Data",
        "exp_grp3": "Destination and Format Options",
        "col_isc": "Isc [mA]"
    }
}