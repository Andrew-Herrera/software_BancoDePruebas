# presentation/touch_keyboard.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QHBoxLayout, QPushButton, QLineEdit
from PySide6.QtCore import Qt

class TouchKeyboard(QDialog):
    """Teclado Virtual Táctil con soporte universal para QLineEdit y QTextEdit."""
    
    def __init__(self, parent=None, target_widget=None, mode="alphanumeric", dark_mode=True):
        super().__init__(parent)
        self.target_widget = target_widget
        self.mode = mode
        
        self.setWindowTitle("Teclado Virtual")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(680, 420) if mode == "alpha" else self.setFixedSize(320, 420)
        
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
            
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Visor Superior ---
        self.display = QLineEdit()
        
        # Extraer texto según el tipo de widget destino (QLineEdit vs QTextEdit)
        if self.target_widget:
            if hasattr(self.target_widget, 'text'):
                self.display.setText(self.target_widget.text())
            elif hasattr(self.target_widget, 'toPlainText'):
                self.display.setText(self.target_widget.toPlainText())
        
        self.display.setStyleSheet("font-size: 22px; font-weight: bold; padding: 10px; border: 2px solid #1565C0; border-radius: 6px;")
        main_layout.addWidget(self.display)
        
        # --- Construcción Dinámica ---
        if self.mode == "numeric":
            main_layout.addLayout(self._build_numeric_layout())
        else:
            main_layout.addLayout(self._build_alphanumeric_layout())

    def _build_numeric_layout(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(6)
        keys = [['7', '8', '9'], ['4', '5', '6'], ['1', '2', '3'], ['.', '0', '-']]
        for row_idx, row in enumerate(keys):
            for col_idx, key in enumerate(row):
                btn = QPushButton(key)
                btn.setFixedSize(90, 65)
                btn.setStyleSheet("font-size: 18px; font-weight: bold; border: 1px solid #757575; border-radius: 5px;")
                btn.clicked.connect(lambda checked, k=key: self.append_character(k))
                grid.addWidget(btn, row_idx, col_idx)
                
        btn_del = QPushButton("Borrar")
        btn_del.setFixedHeight(55)
        btn_del.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold; font-size: 16px; border-radius: 5px;")
        btn_del.clicked.connect(self.backspace_character)
        
        btn_acc = QPushButton("Aceptar")
        btn_acc.setFixedHeight(55)
        btn_acc.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; font-size: 16px; border-radius: 5px;")
        btn_acc.clicked.connect(self._accept_and_update_target)

        grid.addWidget(btn_del, 4, 0, 1, 1)
        grid.addWidget(btn_acc, 4, 1, 1, 2)
        return grid

    def _build_alphanumeric_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        keys = [
            ['1','2','3','4','5','6','7','8','9','0'],
            ['Q','W','E','R','T','Y','U','I','O','P'],
            ['A','S','D','F','G','H','J','K','L','Ñ'],
            ['Z','X','C','V','B','N','M','_','-','.']
        ]
        for row in keys:
            h_layout = QHBoxLayout()
            h_layout.setSpacing(4)
            for key in row:
                btn = QPushButton(key)
                btn.setFixedSize(60, 55)
                btn.setStyleSheet("font-size: 18px; font-weight: bold; border: 1px solid #757575; border-radius: 5px;")
                btn.clicked.connect(lambda checked, k=key: self.append_character(k))
                h_layout.addWidget(btn)
            layout.addLayout(h_layout)
            
        btn_layout = QHBoxLayout()
        btn_del = QPushButton("Borrar")
        btn_del.setFixedHeight(55)
        btn_del.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold; font-size: 16px; border-radius: 5px;")
        btn_del.clicked.connect(self.backspace_character)
        
        btn_space = QPushButton("Espacio")
        btn_space.setFixedHeight(55)
        btn_space.setStyleSheet("font-weight: bold; font-size: 16px; border: 1px solid #757575; border-radius: 5px;")
        btn_space.clicked.connect(lambda: self.append_character(" "))
        
        btn_acc = QPushButton("Aceptar")
        btn_acc.setFixedHeight(55)
        btn_acc.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; font-size: 16px; border-radius: 5px;")
        btn_acc.clicked.connect(self._accept_and_update_target)
        
        btn_layout.addWidget(btn_del)
        btn_layout.addWidget(btn_space)
        btn_layout.addWidget(btn_acc)
        layout.addLayout(btn_layout)
        return layout

    def append_character(self, character: str):
        self.display.insert(character)

    def backspace_character(self):
        self.display.backspace()

    def get_value(self) -> str:
        return self.display.text()

    def _accept_and_update_target(self):
        if self.target_widget:
            if hasattr(self.target_widget, 'setText'):
                self.target_widget.setText(self.get_value())
            elif hasattr(self.target_widget, 'setPlainText'):
                self.target_widget.setPlainText(self.get_value())
        self.accept()