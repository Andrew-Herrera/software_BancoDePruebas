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
from hardware.motor_driver import MotorDriver          
from hardware.thermal_sensor import ThermalSensor


def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)

    app = QApplication(sys.argv)
    app.setStyle("Fusion") 

    DATA_DIR = os.path.join(BASE_DIR, "data")
    DB_PATH = os.path.join(DATA_DIR, "solar_project.db")
    
    file_manager = FileManager(data_dir=DATA_DIR)
    db_manager = DatabaseManager(db_path=DB_PATH)

    config = file_manager.load_json_config()
    gpib_id = config.get("gpib_id", "24")
    pasos_rev = int(config.get("motor_steps_rev", 3200))

    # 1. Inicializar Hardware
    keithley_driver = KeithleyDriver(gpib_id=gpib_id)
    motor = MotorDriver(pulsos_por_vuelta=pasos_rev, vueltas_maximas=23.5)
    thermal = ThermalSensor(bus_number=1)                            

    # 2. Inyectar en el controlador central
    controller = SolarController(
        db_manager=db_manager, 
        file_manager=file_manager,
        keithley_driver=keithley_driver,
        motor=motor,                                                 
        thermal=thermal                                              
    )

    window = MainWindow(controller=controller)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()