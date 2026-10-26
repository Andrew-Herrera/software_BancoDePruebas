try:
    from smbus2 import SMBus
    from mlx90614 import MLX90614
except ImportError:
    SMBus, MLX90614 = None, None

class ThermalSensor:
    """Lector de temperatura infrarroja GY-906 (MLX90614)."""
    
    def __init__(self, bus_number: int = 1):
        self.bus_number = bus_number
        self.sensor = None
        self.is_connected = False
        
        if SMBus and MLX90614:
            try:
                self.bus = SMBus(self.bus_number)
                self.sensor = MLX90614(self.bus, address=0x5A)
                self.is_connected = True
            except Exception as e:
                print(f"Error conectando sensor térmico: {e}")

    def get_temperatures(self) -> tuple[float, float]:
        """Devuelve (Temp_Ambiente, Temp_Objeto). Retorna (NaN, NaN) si falla."""
        if not self.is_connected or not self.sensor:
            return float('nan'), float('nan')
            
        try:
            t_amb = self.sensor.get_ambient()
            t_obj = self.sensor.get_object_1()
            return round(t_amb, 2), round(t_obj, 2)
        except Exception as e:
            print(f"Error de lectura térmica I2C: {e}")
            return float('nan'), float('nan')