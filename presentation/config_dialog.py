# presentation/config_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QFormLayout, QComboBox, QCheckBox, QLineEdit, QPushButton
)
from presentation.touch_keyboard import TouchKeyboard

class ConfigDialog(QDialog):
    def __init__(self, parent, current_config: dict, texts: dict):
        super().__init__(parent)
        self.config = current_config.copy()
        self.t = texts
        
        self.setWindowTitle("Configuración del Sistema / System Settings")
        self.setFixedSize(520, 400)
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
            
        self._setup_ui()
        self._load_config_values()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- Tab 1: Hardware & SCPI ---
        self.tab_hw = QWidget()
        f_hw = QFormLayout(self.tab_hw)
        self.cb_demo = QCheckBox("Modo Simulación (Demo Mode)")
        self.txt_gpib = self._create_input("10")
        
        self.cb_baud = QComboBox()
        self.cb_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
        
        self.cb_term = QComboBox()
        self.cb_term.addItems(["\\r\\n", "\\n", "\\r"])
        self.cb_route = QComboBox()
        self.cb_route.addItems(["Front (FRONT)", "Rear (REAR)"])
        self.cb_wire = QComboBox()
        self.cb_wire.addItems(["2 Wire (LOCAL)", "4 Wire (REMOTE)"])
        self.btn_connect = QPushButton(self.t.get("btn_connect", "Conectar Hardware"))
        
        f_hw.addRow(self.cb_demo)
        f_hw.addRow("Dirección GPIB:", self.txt_gpib)
        f_hw.addRow("Baudrate:", self.cb_baud)
        f_hw.addRow("Terminación SCPI:", self.cb_term)
        f_hw.addRow("Ruta de Terminales:", self.cb_route)
        f_hw.addRow("Modo de Conexión (Sense):", self.cb_wire)
        f_hw.addWidget(self.btn_connect)
        self.tabs.addTab(self.tab_hw, "Hardware")

        # --- Tab 2: Metrología ---
        self.tab_metro = QWidget()
        f_metro = QFormLayout(self.tab_metro)
        
        self.txt_sensor = self._create_input("BPW20RF", mode="alpha")
        self.txt_calib_date = self._create_input("2026-04-09", mode="alpha")
        self.txt_remind_days = self._create_input("10")
        
        self.cb_polarity = QComboBox()
        self.cb_polarity.addItems(["Direct (PV - Quadrant I)", "Reverse (Quadrant III)"])
        self.btn_calib = QPushButton(self.t.get("btn_calib", "Protocolo de Calibración"))
        
        f_metro.addRow("Sensor de Referencia:", self.txt_sensor)
        f_metro.addRow("Última Calibración:", self.txt_calib_date)
        f_metro.addRow("Días de Recordatorio:", self.txt_remind_days)
        f_metro.addRow("Polaridad de Gráfico:", self.cb_polarity)
        f_metro.addWidget(self.btn_calib)
        self.tabs.addTab(self.tab_metro, "Metrología")

        # --- Tab 3: UI & Preferencias ---
        self.tab_ui = QWidget()
        f_ui = QFormLayout(self.tab_ui)
        self.cb_lang = QComboBox()
        self.cb_lang.addItems(["Español", "English"])
        self.cb_dark = QCheckBox("Modo Oscuro (Dark Theme)")
        self.cb_touch = QCheckBox("Teclado Táctil Virtual (7\")")
        self.cb_strict = QCheckBox("Validación Metrológica Estricta")
        
        f_ui.addRow("Idioma / Language:", self.cb_lang)
        f_ui.addRow(self.cb_dark)
        f_ui.addRow(self.cb_touch)
        f_ui.addRow(self.cb_strict)
        self.tabs.addTab(self.tab_ui, "UI & Pantalla")

        main_layout.addWidget(self.tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton("Guardar / Save")
        self.btn_save.setFixedSize(130, 40)
        self.btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self._save_config)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFixedSize(110, 40)
        self.btn_cancel.setStyleSheet("background-color: #C62828; color: white; font-weight: bold;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        main_layout.addLayout(btn_layout)

    def _create_input(self, text: str, mode: str = "numeric") -> QLineEdit:
        line = QLineEdit(text)
        line.mousePressEvent = lambda e: self._open_touch(line, mode)
        return line

    def _open_touch(self, target: QLineEdit, mode: str):
        if self.config.get('touch_mode', True):
            kbd = TouchKeyboard(self, target, mode=mode, dark_mode=self.config.get('dark_mode', True))
            kbd.exec()

    def _load_config_values(self):
        self.cb_demo.setChecked(self.config.get("demo_mode", True))
        self.txt_gpib.setText(str(self.config.get("gpib_id", "10")))
        self.cb_baud.setCurrentText(str(self.config.get("baud", "9600")))
        self.cb_term.setCurrentText(self.config.get("termination", "\\r\\n"))
        self.cb_route.setCurrentText(self.config.get("term_route", "Front (FRONT)"))
        self.cb_wire.setCurrentText(self.config.get("wire_mode", "2 Wire (LOCAL)"))
        
        self.txt_sensor.setText(self.config.get("sensor", "BPW20RF"))
        self.txt_calib_date.setText(self.config.get("last_calib", "2026-04-09"))
        self.txt_remind_days.setText(str(self.config.get("remind_days", 10)))
        self.cb_polarity.setCurrentText(self.config.get("graph_polarity", "Direct (PV - Quadrant I)"))
        self.cb_strict.setChecked(self.config.get("strict_validation", True))
        
        self.cb_lang.setCurrentText(self.config.get("lang", "Español"))
        self.cb_dark.setChecked(self.config.get("dark_mode", True))
        self.cb_touch.setChecked(self.config.get("touch_mode", True))

    def _save_config(self):
        self.config["demo_mode"] = self.cb_demo.isChecked()
        self.config["gpib_id"] = self.txt_gpib.text().strip()
        self.config["baud"] = self.cb_baud.currentText()
        self.config["termination"] = self.cb_term.currentText()
        self.config["term_route"] = self.cb_route.currentText()
        self.config["wire_mode"] = self.cb_wire.currentText()
        
        self.config["sensor"] = self.txt_sensor.text().strip()
        self.config["last_calib"] = self.txt_calib_date.text().strip()
        try: self.config["remind_days"] = int(self.txt_remind_days.text())
        except ValueError: self.config["remind_days"] = 10
            
        self.config["graph_polarity"] = self.cb_polarity.currentText()
        self.config["strict_validation"] = self.cb_strict.isChecked()
        
        self.config["lang"] = self.cb_lang.currentText()
        self.config["dark_mode"] = self.cb_dark.isChecked()
        self.config["touch_mode"] = self.cb_touch.isChecked()
        
        self.accept()