# presentation/config_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QFormLayout, QComboBox, QCheckBox, QLineEdit, QPushButton,
    QMessageBox
)
from presentation.touch_keyboard import TouchKeyboard

class ConfigDialog(QDialog):
    # Se añade el parámetro 'controller' para interactuar con hardware y motores
    def __init__(self, parent, current_config: dict, texts: dict, controller=None):
        super().__init__(parent)
        self.config = current_config.copy()
        self.t = texts
        self.controller = controller
        
        self.setWindowTitle("Configuración del Sistema / System Settings")
        self.setFixedSize(540, 420)
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
            
        self._setup_ui()
        self._load_config_values()
        self._on_demo_toggled() # Ajustar el estado visual inicial

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- Tab 1: Hardware & SCPI ---
        self.tab_hw = QWidget()
        f_hw = QFormLayout(self.tab_hw)
        self.cb_demo = QCheckBox("Modo Simulación (Demo Mode)")
        self.cb_demo.stateChanged.connect(self._on_demo_toggled) # Evento para la casilla
        
        self.txt_gpib = self._create_input("10")
        
        self.cb_baud = QComboBox()
        self.cb_baud.addItems(["9600", "19200", "38400", "57600", "115200"])
        
        self.cb_term = QComboBox()
        self.cb_term.addItems(["\\r\\n", "\\n", "\\r"])
        
        self.cb_route = QComboBox()
        self.cb_route.addItems(["Front (FRONT)", "Rear (REAR)"])
        
        self.cb_wire = QComboBox()
        self.cb_wire.addItems(["2 Wire (LOCAL)", "4 Wire (REMOTE)"])
        
        self.btn_connect = QPushButton(self.t.get("btn_connect", "Probar Conexión Hardware"))
        self.btn_connect.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold;")
        self.btn_connect.clicked.connect(self._test_hardware_connection) # Acción conectada
        
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

        # --- Tab 3: Calibración Óptica (Eje Z) ---
        self.tab_cnc = QWidget()
        f_cnc = QFormLayout(self.tab_cnc)
        
        self.btn_home = QPushButton("Ir a Posición Segura (Home limit-switch)")
        self.btn_home.clicked.connect(self._motor_home)
        
        box_jog = QHBoxLayout()
        self.btn_z_up = QPushButton("▲ Acercar (Subir)")
        self.btn_z_down = QPushButton("▼ Alejar (Bajar)")
        self.btn_z_up.clicked.connect(lambda: self._motor_jog(50))
        self.btn_z_down.clicked.connect(lambda: self._motor_jog(-50))
        box_jog.addWidget(self.btn_z_down)
        box_jog.addWidget(self.btn_z_up)
        
        self.txt_z_focus = self._create_input("0")
        self.btn_save_z = QPushButton("Guardar Posición Actual como Z óptimo")
        self.btn_save_z.clicked.connect(self._save_current_z)
        
        f_cnc.addRow(self.btn_home)
        f_cnc.addRow("Control Manual Z:", box_jog)
        f_cnc.addRow("Z focal guardado (pasos):", self.txt_z_focus)
        f_cnc.addRow(self.btn_save_z)
        self.tabs.addTab(self.tab_cnc, "Óptica CNC")

        # --- Tab 4: UI & Preferencias ---
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

    def _on_demo_toggled(self):
        """Activa o desactiva la sección de hardware en base al Modo Demo"""
        is_demo = self.cb_demo.isChecked()
        self.txt_gpib.setEnabled(not is_demo)
        self.btn_connect.setEnabled(not is_demo)
        # Cambiamos visualmente para indicar que está inhabilitado
        color = "#757575" if is_demo else "#1976D2"
        self.btn_connect.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")

    def _test_hardware_connection(self):
        """Intenta realizar la comunicación con la Keithley utilizando la dirección ingresada"""
        if not self.controller or not hasattr(self.controller, 'driver') or not self.controller.driver:
            QMessageBox.warning(self, "Error", "El controlador de hardware no está inicializado en la aplicación principal.")
            return
            
        # Asignamos temporalmente el GPIB que el usuario haya escrito en la caja de texto
        self.controller.driver.gpib_id = self.txt_gpib.text().strip()
        
        QMessageBox.information(self, "Conectando...", "Intentando comunicación SCPI, esto podría tardar un momento...")
        if self.controller.driver.connect():
            QMessageBox.information(self, "Conexión Exitosa", "Instrumento Keithley detectado y configurado correctamente.")
        else:
            QMessageBox.critical(self, "Fallo de Conexión", "No se pudo conectar al hardware. Compruebe la dirección GPIB, los cables y que el equipo esté encendido.")

    def _motor_home(self):
        if self.controller and hasattr(self.controller, 'motor') and self.controller.motor:
            self.controller.motor.home()
            self.txt_z_focus.setText("0")
        else:
            QMessageBox.warning(self, "Hardware", "Motor no configurado en el sistema.")

    def _motor_jog(self, steps: int):
        if self.controller and hasattr(self.controller, 'motor') and self.controller.motor:
            if not self.controller.motor.is_homed:
                QMessageBox.warning(self, "Advertencia", "El eje Z debe enviarse a Home primero.")
                return
            direction = 1 if steps > 0 else 0
            self.controller.motor.move_relative(abs(steps), direction)
            self.txt_z_focus.setText(str(self.controller.motor.current_position))

    def _save_current_z(self):
        if self.controller and hasattr(self.controller, 'motor') and self.controller.motor:
            pos = self.controller.motor.current_position
            self.txt_z_focus.setText(str(pos))
            QMessageBox.information(self, "Guardado", f"Posición Z={pos} establecida como distancia focal óptima.")

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
        
        self.txt_z_focus.setText(str(self.config.get("z_focus", 0)))
        
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
            
        try: self.config["z_focus"] = int(self.txt_z_focus.text())
        except ValueError: self.config["z_focus"] = 0
            
        self.config["graph_polarity"] = self.cb_polarity.currentText()
        self.config["strict_validation"] = self.cb_strict.isChecked()
        
        self.config["lang"] = self.cb_lang.currentText()
        self.config["dark_mode"] = self.cb_dark.isChecked()
        self.config["touch_mode"] = self.cb_touch.isChecked()
        
        self.accept()