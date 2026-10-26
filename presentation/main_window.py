# presentation/main_window.py
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QTabWidget, QFormLayout, QLineEdit, QComboBox, 
    QMessageBox, QCheckBox, QGroupBox, QScrollArea, QFrame,
    QDialog
)
from PySide6.QtGui import QBrush, QColor
from PySide6.QtCore import Qt

from utils.text import TEXTS
from utils.style_manager import StyleManager
from presentation.config_dialog import ConfigDialog
from presentation.export_dialog import ExportDialog
from presentation.comparison_dialog import ComparisonDialog
from presentation.curves_dialog import CurvesDialog
from presentation.touch_keyboard import TouchKeyboard

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        
        if hasattr(self.controller, 'file_manager'):
            self.config = self.controller.file_manager.load_json_config()
        else:
            self.config = {}

        self.t = TEXTS.get(self.config.get("lang", "Español"), TEXTS["Español"])
        self.curve_metadata = {}
        self.worker = None

        self._setup_ui()
        self.apply_settings()
        self.actualizar_indicador_status()
        self.recalculate_time()

    def _setup_ui(self):
        self.setMinimumSize(1024, 600)
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.main_ly = QVBoxLayout(self.central)
        
        self.top_bar = QHBoxLayout()
        self.lbl_st_t = QLabel()
        self.lbl_st_v = QLabel()
        self.top_bar.addWidget(self.lbl_st_t)
        self.top_bar.addWidget(self.lbl_st_v)
        self.top_bar.addStretch()
        
        self.btn_compare = QPushButton()
        self.btn_cfg = QPushButton("⚙")
        self.btn_export = QPushButton()
        
        self.btn_compare.setFixedSize(140, 38)
        self.btn_cfg.setFixedSize(45, 38)
        self.btn_export.setFixedSize(140, 38)
        
        self.btn_compare.clicked.connect(self.open_history)
        self.btn_cfg.clicked.connect(self.open_config)
        self.btn_export.clicked.connect(self.open_export)
        
        self.top_bar.addWidget(self.btn_compare)
        self.top_bar.addWidget(self.btn_cfg)
        self.top_bar.addWidget(self.btn_export)
        self.main_ly.addLayout(self.top_bar)

        self.work_area = QHBoxLayout()
        self.scroll_left = QScrollArea()
        self.scroll_left.setWidgetResizable(True)
        self.scroll_left.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_left.setFixedWidth(275)
        self.scroll_left.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.scroll_left_widget = QWidget()
        self.left_panel = QVBoxLayout(self.scroll_left_widget)
        self.left_panel.setContentsMargins(0, 0, 5, 0)
        
        self.group_common = QGroupBox()
        self.f_common = QFormLayout(self.group_common)
        self.f_common.setVerticalSpacing(4)
        
        self.cb_irr = QComboBox()
        self.cb_irr.addItems(["1000 W/m² (1 Sol)", "500 W/m² (0.5 Sol)", "100 W/m² (0.1 Sol)", "Oscuridad"])
        
        self.v_start = self._create_input("-0.200")
        self.v_stop = self._create_input("1.200")
        self.samples = self._create_input("100")
        self.delay = self._create_input("0.05")
        self.sp_comp = self._create_input("0.05")
        self.sp_nplc = self._create_input("1.0")
        self.chk_hist = QCheckBox()
        
        self.lbl_irr, self.lbl_vs, self.lbl_vf = QLabel(), QLabel(), QLabel()
        self.lbl_smp, self.lbl_dly = QLabel(), QLabel()
        self.lbl_comp, self.lbl_nplc = QLabel(), QLabel()
        
        self.f_common.addRow(self.lbl_irr, self.cb_irr)
        self.f_common.addRow(self.lbl_vs, self.v_start)
        self.f_common.addRow(self.lbl_vf, self.v_stop)
        self.f_common.addRow(self.lbl_smp, self.samples)
        self.f_common.addRow(self.lbl_dly, self.delay)
        self.f_common.addRow(self.lbl_comp, self.sp_comp)
        self.f_common.addRow(self.lbl_nplc, self.sp_nplc)
        self.f_common.addRow(self.chk_hist)
        self.left_panel.addWidget(self.group_common)

        self.tabs = QTabWidget()
        self.tab_fast = QWidget()
        self.ly_fast = QFormLayout(self.tab_fast)
        self.n_sweeps = self._create_input("10")
        self.int_sweeps = self._create_input("5.0")
        self.lbl_nb, self.lbl_int = QLabel(), QLabel()
        self.ly_fast.addRow(self.lbl_nb, self.n_sweeps)
        self.ly_fast.addRow(self.lbl_int, self.int_sweeps)
        self.tabs.addTab(self.tab_fast, "")
        
        self.tab_stress = QWidget()
        self.ly_stress = QFormLayout(self.tab_stress)
        self.dur_hrs = self._create_input("1.0")
        self.b_per_hr = self._create_input("10")
        self.v_bias = self._create_input("0.0")
        self.lbl_dur, self.lbl_bph, self.lbl_vbias = QLabel(), QLabel(), QLabel()
        self.ly_stress.addRow(self.lbl_dur, self.dur_hrs)
        self.ly_stress.addRow(self.lbl_bph, self.b_per_hr)
        self.ly_stress.addRow(self.lbl_vbias, self.v_bias)
        self.tabs.addTab(self.tab_stress, "")
        self.left_panel.addWidget(self.tabs)

        self.inputs = [self.cb_irr, self.v_start, self.v_stop, self.samples, self.delay, 
                       self.sp_comp, self.sp_nplc, self.chk_hist, self.n_sweeps, 
                       self.int_sweeps, self.dur_hrs, self.b_per_hr, self.v_bias, self.tabs]
        
        # Etiqueta de tiempo restaurada
        self.lbl_time = QLabel("Tiempo est.: 0.00 min")
        self.lbl_time.setStyleSheet("font-weight: bold; color: #1E88E5; font-size: 14px;")
        
        self.btn_start = QPushButton()
        self.btn_start.setFixedHeight(40)
        self.btn_start.clicked.connect(self.start_or_cancel_test)
        
        self.left_panel.addWidget(self.lbl_time)
        self.left_panel.addWidget(self.btn_start)
        self.left_panel.addStretch()
        
        self.scroll_left.setWidget(self.scroll_left_widget)
        self.work_area.addWidget(self.scroll_left, 0)

        self.plot_container = QVBoxLayout()
        self.plot_container.setContentsMargins(5, 0, 5, 0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.getPlotItem().hideButtons()
        self.plot_container.addWidget(self.plot_widget)
        
        self.bottom_tools_ly = QHBoxLayout()
        self.bottom_tools_ly.addStretch()
        
        self.btn_gestor = QPushButton()
        self.btn_gestor.setFixedHeight(30)
        self.btn_gestor.setFixedWidth(160)
        self.btn_gestor.setStyleSheet("background-color: #546E7A; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_gestor.clicked.connect(self.abrir_gestor_curvas)
        
        self.btn_autorange = QPushButton()
        self.btn_autorange.setFixedHeight(30)
        self.btn_autorange.setFixedWidth(130)
        self.btn_autorange.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_autorange.clicked.connect(lambda: self.plot_widget.getPlotItem().enableAutoRange())
        
        self.bottom_tools_ly.addWidget(self.btn_gestor)
        self.bottom_tools_ly.addWidget(self.btn_autorange)
        self.plot_container.addLayout(self.bottom_tools_ly)
        self.work_area.addLayout(self.plot_container, 1)
        self.main_ly.addLayout(self.work_area)

        # Conectar eventos de tiempo
        for w in [self.samples, self.delay, self.n_sweeps, self.int_sweeps, self.dur_hrs, self.b_per_hr]:
            w.textChanged.connect(self.recalculate_time)
        self.chk_hist.stateChanged.connect(self.recalculate_time)
        self.tabs.currentChanged.connect(self.recalculate_time)

    def recalculate_time(self):
        try:
            mode = self.tabs.currentIndex()
            if mode == 0:
                smp = int(self.samples.text() or 100)
                dly = float(self.delay.text() or 0.05)
                n_swp = int(self.n_sweeps.text() or 1)
                interval = float(self.int_sweeps.text() or 5.0)
                hist = self.chk_hist.isChecked()
                
                time_per_sweep = smp * dly
                n_cycles = max(1, n_swp // 2) if hist else n_swp
                
                total_sec = (time_per_sweep * (2 if hist else 1) * n_cycles) + (interval * (n_cycles - 1))
                self.lbl_time.setText(f"{self.t.get('time', 'Tiempo est.:')} {total_sec / 60:.2f} min")
            else:
                # Si es estrés, mostramos directamente la duración solicitada en horas
                dur = float(self.dur_hrs.text() or 1.0)
                self.lbl_time.setText(f"{self.t.get('time', 'Tiempo est.:')} {dur:.2f} hrs")
        except Exception:
            self.lbl_time.setText(f"{self.t.get('time', 'Tiempo est.:')} --")

    def actualizar_indicador_status(self):
        if not hasattr(self, 'lbl_st_v'): return
        
        is_demo = self.config.get('demo_mode', True)
        
        # Evaluar el estado real de la conexión del hardware
        driver_connected = False
        if hasattr(self, 'controller') and self.controller:
            if hasattr(self.controller, 'driver') and self.controller.driver:
                driver_connected = self.controller.driver.is_connected

        if is_demo:
            self.lbl_st_v.setText(self.t.get("demo_lbl", "MODO DEMO"))
            self.lbl_st_v.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 14px;")
        elif driver_connected:
            self.lbl_st_v.setText(self.t.get("connected", "CONECTADO"))
            self.lbl_st_v.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        else:
            self.lbl_st_v.setText(self.t.get("disconnected", "DESCONECTADO"))
            self.lbl_st_v.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 14px;")

    def apply_settings(self):
        lang = self.config.get("lang", "Español")
        self.t = TEXTS.get(lang, TEXTS["Español"])
        
        self.setWindowTitle(self.t.get("title", ""))
        self.group_common.setTitle(self.t.get("group_common", "Parámetros Comunes"))
        
        self.tabs.setTabText(0, self.t.get("tab_fast", "Barridos Rápidos"))
        self.tabs.setTabText(1, self.t.get("tab_stress", "Estrés"))
        
        self.lbl_st_t.setText(self.t.get("status_lbl", "Estado:"))
        self.lbl_irr.setText(self.t.get("irr", ""))
        self.lbl_vs.setText(self.t.get("start_v", ""))
        self.lbl_vf.setText(self.t.get("stop_v", ""))
        self.lbl_smp.setText(self.t.get("samples", ""))
        self.lbl_dly.setText(self.t.get("delay", ""))
        self.lbl_comp.setText(self.t.get("compliance", ""))
        self.lbl_nplc.setText(self.t.get("nplc", ""))
        self.chk_hist.setText(self.t.get("hist", ""))
        
        self.lbl_nb.setText(self.t.get("n_sweeps", ""))
        self.lbl_int.setText(self.t.get("interval", ""))
        self.lbl_dur.setText(self.t.get("duration", ""))
        self.lbl_bph.setText(self.t.get("b_per_hr", ""))
        self.lbl_vbias.setText(self.t.get("v_bias", ""))
        
        self.btn_start.setText(self.t.get("start_btn", "INICIAR"))
        self.btn_compare.setText(self.t.get("compare_btn", "Historial"))
        self.btn_export.setText(self.t.get("btn_export", "Exportar"))
        self.btn_gestor.setText(self.t.get("btn_gestor", "Gestor"))
        self.btn_autorange.setText(self.t.get("btn_auto", "Auto-Escalar"))
        
        self.plot_widget.setLabel('left', self.t.get("graph_i", "Corriente (A)"))
        self.plot_widget.setLabel('bottom', self.t.get("graph_v", "Voltaje (V)"))
        
        estilo_botones_top = "background-color: #1565C0; color: white; font-weight: bold; border: 1px solid #0d47a1; border-radius: 4px;"
        self.btn_compare.setStyleSheet(estilo_botones_top)
        self.btn_cfg.setStyleSheet(estilo_botones_top)
        self.btn_export.setStyleSheet(estilo_botones_top)
        
        is_dark = self.config.get("dark_mode", True)
        is_touch = self.config.get("touch_mode", True)
        self.setStyleSheet(StyleManager.get_style(dark_mode=is_dark, touch_mode=is_touch))
        self.plot_widget.setBackground('#121212' if is_dark else '#FFFFFF')
        
        if not is_dark:
            self.lbl_st_t.setStyleSheet("color: #212121; font-weight: bold;")
        else:
            self.lbl_st_t.setStyleSheet("color: #e0e0e0; font-weight: bold;")
        self.toggle_ui(False)
        self.recalculate_time()

    def _create_input(self, val):
        le = QLineEdit(val)
        le.setFixedSize(65, 26)
        le.mousePressEvent = lambda e: self.evaluar_despliegue_teclado(le)
        return le

    def evaluar_despliegue_teclado(self, target, mode="numeric"):
        if self.config.get('touch_mode', True):
            tk = TouchKeyboard(self, target_widget=target, mode=mode, dark_mode=self.config.get('dark_mode', True))
            tk.move(self.geometry().center() - tk.rect().center())
            if tk.exec() == QDialog.DialogCode.Accepted:
                # El teclado se encarga de rellenar el widget internamente.
                pass

    def open_config(self):
        dialog = ConfigDialog(self, self.config, self.t, controller=self.controller)
        dialog.move(self.geometry().center() - dialog.rect().center())
        if dialog.exec():
            self.config = dialog.config
            if self.controller:
                self.controller.save_settings(self.config)
            self.apply_settings()
            self.actualizar_indicador_status()

    def abrir_gestor_curvas(self):
        if not self.curve_metadata:
            self.show_alert(QMessageBox.Icon.Information, "Gestor", "No hay curvas.")
            return
        mode = self.tabs.currentIndex()
        try: b_per_hr = int(self.b_per_hr.text())
        except ValueError: b_per_hr = 10
            
        dialog = CurvesDialog(self, self.curve_metadata, mode, b_per_hr, self.config, self.t)
        # Posicionar el gestor pegado a la izquierda
        dialog.move(self.geometry().x() + 20, self.geometry().center().y() - dialog.rect().height() // 2)
        dialog.exec()

    def open_export(self):
        visibles = [idx for idx, m in self.curve_metadata.items() if m['line'].isVisible()]
        if not visibles:
            self.show_alert(QMessageBox.Icon.Warning, "Exportar", "No hay curvas visibles para exportar.")
            return
            
        dialog = ExportDialog(self, self.curve_metadata, self.config, self.t, self.controller)
        dialog.move(self.geometry().center() - dialog.rect().center())
        dialog.exec()

    def open_history(self):
        dialog = ComparisonDialog(self, self.config, self.t, self.controller)
        dialog.move(self.geometry().center() - dialog.rect().center())
        if dialog.exec():
            if dialog.selected_experiments:
                # Solo limpiar la grafica si seleccionaron algo y le dieron Aceptar
                self.clear_plot()
                self.plot_historical_curves(dialog.selected_experiments)

    def _get_safe_param(self, input_widget, param_type: type, default_val):
        try: return param_type(input_widget.text().strip())
        except ValueError:
            input_widget.setText(str(default_val))
            return default_val

    def start_or_cancel_test(self):
        if self.worker and self.worker.isRunning():
            self.btn_start.setText(self.t.get("stopping", "DETENIENDO..."))
            self.worker.stop()
        else:
            self.start_test()

    def start_test(self):
        mode = self.tabs.currentIndex()
        
        # Extracción de parámetros
        v_start_val = self._get_safe_param(self.v_start, float, -0.2)
        v_stop_val = self._get_safe_param(self.v_stop, float, 1.2)
        samples_val = self._get_safe_param(self.samples, int, 100)
        delay_val = self._get_safe_param(self.delay, float, 0.05)
        compliance_val = self._get_safe_param(self.sp_comp, float, 0.05)
        nplc_val = self._get_safe_param(self.sp_nplc, float, 1.0)
        
        v_bias_val = self._get_safe_param(self.v_bias, float, 0.0) if mode == 1 else 0.0
        n_swp = self._get_safe_param(self.n_sweeps, int, 1) if mode == 0 else 1
        
        # Validación Integral Estricta
        if self.config.get("strict_validation", True):
            errores = []
            if not (-2.0 <= v_start_val <= 20.0) or not (-2.0 <= v_stop_val <= 20.0):
                errores.append("- Las tensiones deben estar dentro del rango [-2.0 20].")
            if compliance_val <= 0 or compliance_val > 1.05:
                errores.append("- La corriente de compliance debe ser positiva y máxima 1.05A.")
            if samples_val < 2 or samples_val > 2500:
                errores.append("- El número de muestras debe ser entre 2 y 2500.")
            if delay_val < 0.05:
                errores.append("- El delay mínimo para visualización segura es 0.05s.")
            if mode == 1 and not (-2.0 <= v_bias_val <= 20.0):
                errores.append("- La tensión de estrés excede los límites físicos.")
            if n_swp < 1:
                errores.append("- Los ciclos o barridos deben ser al menos 1.")
                
            if errores:
                from PySide6.QtWidgets import QMessageBox
                mensaje = "Validación Metrológica Fallida:\n\n" + "\n".join(errores)
                self.show_alert(QMessageBox.Icon.Warning, "Validación", mensaje)
                return

        params = {
            "v_start": v_start_val,
            "v_stop": v_stop_val,
            "samples": samples_val,
            "delay": delay_val,
            "compliance": compliance_val,
            "nplc": nplc_val,
            "hysteresis": self.chk_hist.isChecked()
        }

        if mode == 0:
            params["n_cycles"] = max(1, n_swp // 2) if params["hysteresis"] else n_swp
            params["interval"] = self._get_safe_param(self.int_sweeps, float, 5.0)
            params["stress_mode"] = False
            params["v_bias"] = 0.0
        else:
            dur_hrs = self._get_safe_param(self.dur_hrs, float, 1.0)
            b_per_hr = self._get_safe_param(self.b_per_hr, int, 10)
            params["n_cycles"] = int(dur_hrs * b_per_hr)
            params["interval"] = 3600.0 / b_per_hr if b_per_hr > 0 else 0.0
            params["stress_mode"] = True
            params["v_bias"] = v_bias_val

        self.total_sweeps_expected = params["n_cycles"] * (2 if params["hysteresis"] else 1)
        
        irr_text = self.cb_irr.currentText()
        params['irradiance'] = 1000.0 if "1000" in irr_text else (500.0 if "500" in irr_text else (100.0 if "100" in irr_text else 0.0))
        self.config["last_irr"] = params['irradiance']
        
        self.toggle_ui(True)
        self.clear_plot()

        if self.controller:
            self.worker = self.controller.start_sweep_execution(params, self)
            if self.worker:
                self.worker.sweep_changed.connect(self.new_sweep_line)
                self.worker.point_received.connect(self.update_plot)
                self.worker.finished.connect(self.on_finished)
                self.worker.error.connect(self.on_error)
                self.worker.start()

    def toggle_ui(self, locked):
        color = "#C62828" if locked else "#2E7D32"
        self.btn_start.setText(self.t.get("cancel_btn", "CANCELAR") if locked else self.t.get("start_btn", "INICIAR"))
        self.btn_start.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")
        for w in self.inputs: w.setEnabled(not locked)
        self.btn_export.setEnabled(not locked)
        self.btn_compare.setEnabled(not locked)
        self.btn_cfg.setEnabled(not locked)

    def clear_plot(self):
        self.plot_widget.clear()
        self.curve_metadata.clear()
        self.historical_colors = {}

    def new_sweep_line(self, sweep_idx: int, direction: str):
        mode = self.tabs.currentIndex()
        key = f"{sweep_idx}_{direction}" 
        
        if mode == 0:
            # Un lote siempre agrupa 10 barridos
            batch_idx = (sweep_idx - 1) // 10
            base_idx = batch_idx * 2
            
            if self.chk_hist.isChecked():
                # Lógica Histéresis: Todas las Idas (Fwd) del lote 10 usan el color base. 
                # Todas las Vueltas (Rev) del lote 10 usan el color base + 1.
                c_idx = base_idx if direction == "Fwd" else base_idx + 1
            else:
                # Sin histéresis: Alternamos los dos colores asignados al lote por cada barrido
                c_idx = base_idx if sweep_idx % 2 != 0 else base_idx + 1
                
            color_hex = StyleManager.CURVE_COLORS[c_idx % len(StyleManager.CURVE_COLORS)]
            color = QColor(color_hex)
        else:
            try: 
                total_sweeps = float(self.dur_hrs.text()) * int(self.b_per_hr.text())
            except ValueError: 
                total_sweeps = 50 
            color = self._get_heatmap_color(sweep_idx, total_sweeps)
            
        dir_short = "Fwd" if "Fwd" in direction or "ida" in direction.lower() else "Rev"
        short_name = f"S{sweep_idx} ({dir_short})"
        line = self.plot_widget.plot(pen=pg.mkPen(color, width=2.5), name=short_name)
        
        self.curve_metadata[key] = {
            'line': line, 'color': color.name(), 'x': [], 'y': [], 
            'hist': False, 'name': short_name, 'idx_real': sweep_idx
        }

    def update_plot(self, sweep_idx: int, direction: str, v: float, i: float):
        key = f"{sweep_idx}_{direction}"
        if key in self.curve_metadata:
            # 1. Almacenamiento RAW en RAM (Mantiene la polaridad real de tu celda y equipo)
            self.curve_metadata[key]['x'].append(v)
            self.curve_metadata[key]['y'].append(i)
            
            # 2. Multiplicador exclusivamente visual para la gráfica
            es_directa = "Direct" in self.config.get("graph_polarity", "") or "Directa" in self.config.get("graph_polarity", "")
            multiplicador = -1.0 if es_directa else 1.0
            
            y_visual = [val * multiplicador for val in self.curve_metadata[key]['y']]
            self.curve_metadata[key]['line'].setData(self.curve_metadata[key]['x'], y_visual)

    def plot_historical_curves(self, exp_ids: list):
        if not self.controller: return
        current_idx = max([m.get('idx_real', 0) for m in self.curve_metadata.values()] + [0]) + 1
        group_counters = {}
        if not hasattr(self, 'historical_colors'): self.historical_colors = {}
            
        for exp_id in exp_ids:
            points = self.controller.db.get_sweep_points(exp_id)
            meta_db = self.controller.db.get_experiment_meta(exp_id)
            if not points or not meta_db: continue
            
            holder = meta_db.get('holder_id', 'Desconocido')
            celda = meta_db.get('posicion', '0')
            fecha_hora = str(meta_db.get('fecha_hora', ''))[:16] 
            
            group_id = f"hist_{holder}_C{celda}_{fecha_hora}"
            # GESTOR DE CURVAS: Incluye Holder, Celda, Fecha y HORA.
            group_name = f"{holder} | Celda {celda} | {fecha_hora}"
            
            if group_id not in group_counters: group_counters[group_id] = 0
            group_counters[group_id] += 1
            local_idx = group_counters[group_id]
            
            if group_id not in self.historical_colors:
                c_idx = len(self.historical_colors) % len(StyleManager.CURVE_COLORS)
                self.historical_colors[group_id] = StyleManager.CURVE_COLORS[c_idx]
            
            color_hex = self.historical_colors[group_id]
            
            x_vals = [p[0] for p in points]
            y_vals = [abs(p[1]) if ("Direct" in self.config.get("graph_polarity", "") or "Directa" in self.config.get("graph_polarity", "")) else p[1] for p in points]
            pen = pg.mkPen(color=color_hex, width=2, style=Qt.PenStyle.DashLine)
            
            sentido_db = meta_db.get("tipo_prueba", "Ida")
            dir_short = "Rev" if "Vuelta" in sentido_db or "Histéresis" in sentido_db else "Fwd"
            name = f"Barrido {local_idx} ({dir_short})"
            
            line = self.plot_widget.plot(x_vals, y_vals, pen=pen, name=name)
            
            key = f"hist_{exp_id}"
            self.curve_metadata[key] = {
                'line': line, 'color': color_hex, 'x': x_vals, 'y': y_vals, 
                'hist': True, 'exp_id': exp_id, 'name': name,
                'group_id': group_id, 'group_name': group_name, 'idx_real': current_idx
            }
            current_idx += 1

    def _get_heatmap_color(self, current_idx, total_sweeps):
        ratio = current_idx / max(1, total_sweeps)
        ratio = min(1.0, max(0.0, ratio)) 
        r = int(33 + (244 - 33) * ratio)
        g = int(150 + (67 - 150) * ratio)
        b = int(243 + (54 - 243) * ratio)
        return QColor(r, g, b)

    def on_finished(self, curves: dict, t_stats: dict, aborted: bool):
        self.toggle_ui(False)
        self.last_results = t_stats
        if not aborted:
            self.show_alert(QMessageBox.Icon.Information, self.t.get("alert_acq_title", "Finalizado"), self.t.get("alert_acq_msg", "Prueba concluida."))

    def on_error(self, err_msg: str):
        self.toggle_ui(False)
        self.show_alert(QMessageBox.Icon.Warning, self.t.get("alert_error_title", "Error"), err_msg)

    def show_alert(self, icon_type, title: str, message: str):
        box = QMessageBox(self)
        box.setIcon(icon_type)
        box.setWindowTitle(str(title))
        box.setText(str(message))
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    def closeEvent(self, event):
        """Intercepta el cierre de la ventana para garantizar el apagado seguro."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
            
        if self.controller and hasattr(self.controller, 'driver'):
            if self.controller.driver:
                self.controller.driver.close_session()
                
        event.accept()