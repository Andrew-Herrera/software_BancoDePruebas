# utils/style_manager.py
class StyleManager:
    CURVE_COLORS = [
        '#E53935', '#1E88E5', '#43A047', '#FDD835', '#8E24AA',
        '#00ACC1', '#F4511E', '#7CB342', '#3949AB', '#00897B',
        '#D81B60', '#5E35B1', '#C0CA33', '#FFB300', '#6D4C41',
        '#F06292', '#4DD0E1', '#81C784', '#FF8A65', '#90A4AE'
    ]

    @staticmethod
    def get_style(dark_mode: bool = True, touch_mode: bool = True) -> str:
        if dark_mode:
            base_style = """
                QMainWindow, QDialog, QWidget { background-color: #121212; color: #e0e0e0; font-family: "Segoe UI", Arial, sans-serif; }
                QGroupBox { border: 1px solid #333333; border-radius: 6px; margin-top: 12px; font-weight: bold; color: #90CAF9; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
                QLineEdit, QComboBox, QSpinBox, QTextEdit { background-color: #1e1e1e; color: #ffffff; border: 1px solid #424242; border-radius: 4px; padding: 4px; }
                QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #1976D2; }
                QPushButton { background-color: #333333; color: #ffffff; border: 1px solid #424242; border-radius: 4px; padding: 6px; }
                QPushButton:hover { background-color: #424242; }
                QPushButton:pressed { background-color: #212121; }
                QTabWidget::pane { border: 1px solid #333333; border-radius: 4px; }
                QTabBar::tab { background: #1e1e1e; color: #9e9e9e; padding: 8px 16px; border: 1px solid #333333; border-bottom: none; }
                QTabBar::tab:selected { background: #1976D2; color: white; font-weight: bold; }
                QLabel, QCheckBox { color: #e0e0e0; }
                QTreeWidget { background-color: #1e1e1e; color: #ffffff; border: 1px solid #333333; }
                QTreeWidget::item:hover { background-color: #333333; }
                QTreeWidget::item:selected { background-color: #1976D2; color: white; }
            """
        else:
            base_style = """
                QMainWindow, QDialog, QWidget { background-color: #f5f5f5; color: #212121; font-family: "Segoe UI", Arial, sans-serif; }
                QGroupBox { border: 1px solid #bdbdbd; border-radius: 6px; margin-top: 12px; font-weight: bold; color: #1565C0; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
                QLineEdit, QComboBox, QSpinBox, QTextEdit { background-color: #ffffff; color: #212121; border: 1px solid #bdbdbd; border-radius: 4px; padding: 4px; }
                QLineEdit:focus, QComboBox:focus, QTextEdit:focus { border: 1px solid #1976D2; }
                QPushButton { background-color: #e0e0e0; color: #212121; border: 1px solid #bdbdbd; border-radius: 4px; padding: 6px; }
                QPushButton:hover { background-color: #eeeeee; }
                QPushButton:pressed { background-color: #bdbdbd; }
                QTabWidget::pane { border: 1px solid #bdbdbd; border-radius: 4px; }
                QTabBar::tab { background: #e0e0e0; color: #616161; padding: 8px 16px; border: 1px solid #bdbdbd; border-bottom: none; }
                QTabBar::tab:selected { background: #1976D2; color: white; font-weight: bold; }
                QLabel, QCheckBox { color: #212121; }
                QTreeWidget { background-color: #ffffff; color: #212121; border: 1px solid #bdbdbd; }
                QTreeWidget::item:hover { background-color: #eeeeee; }
                QTreeWidget::item:selected { background-color: #1976D2; color: white; }
            """

        if touch_mode:
            # Se han removido las restricciones de tamaño forzado para QLineEdit y QComboBox
            touch_style = """
                QCheckBox::indicator { width: 22px; height: 22px; }
                QTabBar::tab { padding: 10px 20px; font-size: 14px; }
                QTreeWidget::item { padding: 6px; }
            """
            base_style += touch_style

        return base_style