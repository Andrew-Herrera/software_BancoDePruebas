import time
try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

class MotorDriver:
    """Controlador para Eje Z (Enfoque Óptico) mediante NEMA y OKY7417."""
    
    def __init__(self, pin_step: int = 17, pin_dir: int = 27, pin_limit: int = 22,
                 pulsos_por_vuelta: int = 800, vueltas_maximas: float = 23.5):
        self.pin_step = pin_step
        self.pin_dir = pin_dir
        self.pin_limit = pin_limit
        
        # Parametrización del hardware mecánico
        self.pulsos_por_vuelta = pulsos_por_vuelta
        self.vueltas_maximas = vueltas_maximas
        # Timeout de seguridad: margen del 5% extra sobre el recorrido máximo físico
        self.max_steps_security = int(self.pulsos_por_vuelta * self.vueltas_maximas * 1.05) 
        
        self.current_position = 0
        self.is_homed = False
        
        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.pin_step, GPIO.OUT)
            GPIO.setup(self.pin_dir, GPIO.OUT)
            GPIO.setup(self.pin_limit, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def home(self):
        if not GPIO: return
        GPIO.output(self.pin_dir, GPIO.LOW)
        steps_taken = 0
        while GPIO.input(self.pin_limit) == GPIO.HIGH and steps_taken < self.max_steps_security:
            self._step(delay=0.002)
            steps_taken += 1
            
        if steps_taken >= self.max_steps_security:
            self.is_homed = False
            # NUEVO: Detiene la prueba lanzando una excepción
            raise RuntimeError("ERROR CRÍTICO: Limit-switch no detectado. Homing abortado.")
            
        self.current_position = 0
        self.is_homed = True
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
        step_inc = 1 if direction == GPIO.HIGH else -1 # Dirección lógica
        
        for _ in range(steps):
            if direction == GPIO.LOW and GPIO.input(self.pin_limit) == GPIO.LOW:
                print("Límite inferior alcanzado prematuramente.")
                self.current_position = 0 # Obliga al cero físico
                break
            self._step(speed_delay)
            self.current_position += step_inc 

    def _step(self, delay: float):
        GPIO.output(self.pin_step, GPIO.HIGH)
        time.sleep(delay)
        GPIO.output(self.pin_step, GPIO.LOW)
        time.sleep(delay)