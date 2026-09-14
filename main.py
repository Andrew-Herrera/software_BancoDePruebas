# main.py
import sys
import os
from PySide6.QtWidgets import QApplication

# Importación de las distintas capas de la arquitectura N-Tier
from storage.database_manager import DatabaseManager
from storage.file_manager import FileManager
from hardware.keithley_driver import KeithleyDriver
from logic.solar_controller import SolarController
from presentation.main_window import MainWindow


def main():
    # 1. Definir BASE_DIR y asegurar que el directorio de trabajo sea el de este script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)

    # 2. Inicializar la aplicación Qt
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Base limpia para aplicar nuestro QSS (StyleManager)

    # 3. Inicializar la Capa de Almacenamiento y cargar configuraciones
    DATA_DIR = os.path.join(BASE_DIR, "data")
    DB_PATH = os.path.join(DATA_DIR, "solar_project.db")
    
    file_manager = FileManager(data_dir=DATA_DIR)
    db_manager = DatabaseManager(db_path=DB_PATH)
    
    # Carga de preferencias antes de inicializar el hardware
    config = file_manager.load_json_config()
    gpib_id = config.get("gpib_id", "10")

    # 4. Inicializar la Capa de Hardware utilizando el GPIB configurado
    keithley_driver = KeithleyDriver(gpib_id=gpib_id)

    # 5. Inicializar la Capa de Lógica de Negocio (Logic Layer)
    controller = SolarController(
        db_manager=db_manager, 
        file_manager=file_manager,
        keithley_driver=keithley_driver
    )

    # 6. Inicializar la Capa de Presentación (Presentation Layer)
    window = MainWindow(controller=controller)
    window.show()

    # 7. Ejecutar el bucle principal de eventos de la aplicación
    sys.exit(app.exec())


if __name__ == "__main__":
    main()