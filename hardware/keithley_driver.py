# hardware/keithley_driver.py
import time
import numpy as np

class KeithleyDriver:
    """
    Hardware Layer: Low-level driver for Keithley 2401 SourceMeter 
    using SCPI commands over PyVISA.
    """
    
    def __init__(self, gpib_id: str):
        self.gpib_id = gpib_id
        self.device = None
        self.is_connected = False

    def connect(self) -> bool:
        """
        Initializes PyVISA Resource Manager (@py backend for Raspberry Pi)
        and establishes connection with the Keithley instrument.
        """
        try:
            import pyvisa
            rm = pyvisa.ResourceManager('@py')
            resource_string = f"GPIB0::{self.gpib_id}::INSTR"
            
            self.device = rm.open_resource(resource_string, timeout=1000)
            
            # Reset and initialization sequence
            self.device.clear()
            self.device.write("*RST")
            self.device.write("*CLS")
            self.device.write(":SYSTEM:REMOTE")
            self.device.write(":FORM:ELEM VOLT, CURR")
            self.device.write(":OUTP ON")
            
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Hardware Connection Warning: {e}. Switching to DEMO mode.")
            self.device = None
            self.is_connected = False
            return False

    def set_protection(self, compliance: float, nplc: float = 1.0):
        """Sets current compliance limit and ADC integration time (NPLC)."""
        if self.device and self.is_connected:
            try:
                self.device.write(f":SENS:CURR:PROT {compliance}")
                self.device.write(f":SENS:CURR:NPLC {nplc}")
            except Exception as e:
                print(f"Error setting compliance: {e}")

    def set_bias_voltage(self, v_bias: float):
        """Applies a constant voltage bias."""
        if self.device and self.is_connected:
            try:
                self.device.write(f":SOUR:VOLT {v_bias}")
            except Exception as e:
                print(f"Error setting bias voltage: {e}")

    def measure_iv_point(self, voltage: float, delay_s: float) -> tuple[float, float]:
        """
        Applies a voltage step, waits for ionic/thermal stabilization, 
        and reads the resulting voltage and current from the ADC.
        """
        if not self.device or not self.is_connected:
            # Fallback to simulated demo point
            return voltage, self.generate_demo_point(voltage)

        try:
            self.device.write(f":SOUR:VOLT {voltage}")
            if delay_s > 0:
                time.sleep(delay_s)
            
            raw_response = self.device.query(":READ?").split(',')
            measured_voltage = float(raw_response[0])
            measured_current = float(raw_response[1])
            return measured_voltage, measured_current
        except Exception as e:
            print(f"Measurement error at {voltage}V: {e}")
            return voltage, self.generate_demo_point(voltage)

    def disable_output(self):
        """Safely powers off Keithley output stage and closes VISA session."""
        if self.device:
            try:
                self.device.write(":SOUR:VOLT 0")
                self.device.write(":OUTP OFF")
                self.device.close()
            except Exception as e:
                print(f"Error disabling output: {e}")
            finally:
                self.device = None
                self.is_connected = False

    @staticmethod
    def generate_demo_point(voltage: float, degradation: float = 1.0) -> float:
        """
        Mathematical simulator for DEMO MODE.
        Generates realistic organic solar cell J-V curves using modified Shockley equation.
        """
        isc_simulated = 0.0145 * degradation  # ~14.5 mA Photocurrent
        voc_simulated = 0.685                  # ~685 mV Open-Circuit Voltage
        
        # Modified Shockley diode equation
        current_theoretical = isc_simulated * (1.0 - np.exp((voltage - voc_simulated) / 0.05))
        noise = np.random.normal(0, 0.00005)
        
        return float(current_theoretical + noise)