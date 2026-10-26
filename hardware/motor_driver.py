try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None
import time

class MotorDriver:
    """Controlador para Eje Z (Enfoque Óptico) mediante NEMA y OKY7417."""
    
    def __init__(self, pin_step: int = 17, pin_dir: int = 27, pin_limit: int = 22):
        self.pin_step = pin_step
        self.pin_dir = pin_dir
        self.pin_limit = pin_limit
        self.current_position = 0
        self.is_homed = False
        
        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin_step, GPIO.OUT)
            GPIO.setup(self.pin_dir, GPIO.OUT)
            GPIO.setup(self.pin_limit, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def home(self):
        """Desciende hasta activar el limit-switch en la base."""
        if not GPIO: return
        
        GPIO.output(self.pin_dir, GPIO.LOW) # Dirección hacia abajo (ajustar según hardware)
        while GPIO.input(self.pin_limit) == GPIO.HIGH:
            self._step(delay=0.002)
            
        self.current_position = 0
        self.is_homed = True
        # Pequeño retroceso para liberar el switch
        self.move_relative(steps=50, direction=GPIO.HIGH)
        self.current_position = 0

    def move_to_z(self, target_steps: int):
        """Mueve el motor a una coordenada Z absoluta."""
        if not self.is_homed:
            raise RuntimeError("El eje Z no está referenciado (Home).")
            
        steps_to_move = target_steps - self.current_position
        direction = GPIO.HIGH if steps_to_move > 0 else GPIO.LOW
        self.move_relative(abs(steps_to_move), direction)
        self.current_position = target_steps

    def move_relative(self, steps: int, direction: int, speed_delay: float = 0.002):
        if not GPIO: return
        GPIO.output(self.pin_dir, direction)
        for _ in range(steps):
            self._step(speed_delay)

    def _step(self, delay: float):
        GPIO.output(self.pin_step, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(self.pin_step, GPIO.LOW)
        time.sleep(delay)