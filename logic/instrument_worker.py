# logic/instrument_worker.py

import math
import random
import time

import numpy as np
from PySide6.QtCore import QThread, Signal

# Analíticas para generar datos de demostración
try:
    from logic import pv_analytics
except ImportError:
    pv_analytics = None


class InstrumentWorker(QThread):
    """Ejecuta los barridos I-V en un hilo independiente."""

    point_received = Signal(int, str, float, float)
    sweep_changed = Signal(int, str)
    temp_measured = Signal(int, float)

    # Señal personalizada utilizada por la interfaz existente.
    finished = Signal(object, object, bool)

    error = Signal(str)

    def __init__(self, controller, params: dict, parent=None):
        super().__init__(parent)

        self.controller = controller
        self.params = params
        self.is_running = True

        # Mantener la compatibilidad con la configuración actual.
        config = self.controller.file_manager.load_json_config()
        self.is_demo = config.get("demo_mode", True)

    def run(self):
        """Ejecuta la adquisición y garantiza una rutina de apagado."""

        start_time = time.monotonic()
        all_curves = {}
        error_message = None
        n_cycles = 1

        try:
            # -------------------------------------------------
            # 1. LECTURA Y VALIDACIÓN DE PARÁMETROS
            # -------------------------------------------------
            v_start = float(self.params.get("v_start", -0.2))
            v_stop = float(self.params.get("v_stop", 1.2))

            samples = int(self.params.get("samples", 100))
            delay = float(self.params.get("delay", 0.05))

            n_cycles = int(self.params.get("n_cycles", 1))
            interval = float(self.params.get("interval", 5.0))

            hysteresis = bool(
                self.params.get("hysteresis", False)
            )
            stress_mode = bool(
                self.params.get("stress_mode", False)
            )

            v_bias = float(self.params.get("v_bias", 0.0))

            compliance = float(
                self.params.get("compliance", 0.05)
            )
            nplc = float(self.params.get("nplc", 1.0))

            numeric_values = {
                "v_start": v_start,
                "v_stop": v_stop,
                "delay": delay,
                "interval": interval,
                "v_bias": v_bias,
                "compliance": compliance,
                "nplc": nplc,
            }

            for name, value in numeric_values.items():
                if not math.isfinite(value):
                    raise ValueError(
                        f"El parámetro {name} debe ser finito."
                    )

            if samples < 2:
                raise ValueError(
                    "El número de muestras debe ser al menos 2."
                )

            if n_cycles < 1:
                raise ValueError(
                    "El número de ciclos debe ser al menos 1."
                )

            if delay < 0:
                raise ValueError(
                    "El retardo no puede ser negativo."
                )

            if interval < 0:
                raise ValueError(
                    "El intervalo no puede ser negativo."
                )

            if compliance <= 0:
                raise ValueError(
                    "El límite de corriente debe ser positivo."
                )

            if not 0.01 <= nplc <= 10:
                raise ValueError(
                    "El NPLC debe estar entre 0.01 y 10."
                )

            # Estos límites corresponden al rango de tensión
            # contemplado por el driver modificado.
            if not -20.0 <= v_start <= 20.0:
                raise ValueError(
                    "La tensión inicial debe estar entre -20 y 20 V."
                )

            if not -20.0 <= v_stop <= 20.0:
                raise ValueError(
                    "La tensión final debe estar entre -20 y 20 V."
                )

            if not -20.0 <= v_bias <= 20.0:
                raise ValueError(
                    "La tensión de polarización debe estar "
                    "entre -20 y 20 V."
                )

            if stress_mode and self.is_demo:
                # El modo demo no controla el hardware real.
                pass

            # -------------------------------------------------
            # 2. COMPROBACIÓN Y PREPARACIÓN DEL HARDWARE
            # -------------------------------------------------
            driver = getattr(self.controller, "driver", None)

            if not self.is_demo:
                if driver is None or not driver.is_connected:
                    raise RuntimeError(
                        "La Keithley 2401 no está conectada. "
                        "Conecta la fuente antes de iniciar el ensayo."
                    )

                # Configurar protección y tiempo de integración
                # desde el hilo de adquisición.
                driver.set_protection(
                    compliance=compliance,
                    nplc=nplc,
                )

                # Referenciar el motor si está inicializado.
                motor = getattr(self.controller, "motor", None)

                if motor is not None:
                    motor.home()

                    config = (
                        self.controller.file_manager
                        .load_json_config()
                    )

                    z_focus = float(
                        config.get("z_focus", 0) or 0
                    )

                    if not math.isfinite(z_focus):
                        raise ValueError(
                            "La posición focal Z debe ser finita."
                        )

                    if z_focus > 0:
                        motor.move_to_z(z_focus)

            # Preparar las secuencias de barrido.
            v_fwd = np.linspace(
                v_start, v_stop, samples
            )
            v_rev = np.linspace(
                v_stop, v_start, samples
            )

            sweep_idx = 1

            # -------------------------------------------------
            # 3. EJECUCIÓN DE LOS CICLOS
            # -------------------------------------------------
            for cycle in range(1, n_cycles + 1):

                if not self.is_running:
                    break

                # =============================================
                # BARRIDO DE IDA
                # =============================================
                t_obj_fwd = self._read_temperature()

                self.sweep_changed.emit(
                    sweep_idx, "Fwd"
                )

                if t_obj_fwd is not None:
                    self.temp_measured.emit(
                        sweep_idx, t_obj_fwd
                    )

                current_sweep_data = []

                for v in v_fwd:
                    if not self.is_running:
                        break

                    if self.is_demo:
                        i_meas = self._generate_demo_point(
                            float(v)
                        )

                        # Espera interrumpible para permitir
                        # cancelar desde la interfaz.
                        self._wait_interval(delay)

                    else:
                        # El driver aplica el voltaje, habilita
                        # la salida y devuelve V e I medidos.
                        v_meas, i_meas = (
                            driver.measure_iv_point(
                                float(v),
                                delay,
                            )
                        )

                    # Se utiliza la tensión solicitada para
                    # conservar la compatibilidad con la gráfica.
                    # La lectura de tensión real queda disponible
                    # en v_meas durante el modo hardware.
                    current_sweep_data.append(
                        (float(v), float(i_meas))
                    )

                    self.point_received.emit(
                        sweep_idx,
                        "Fwd",
                        float(v),
                        float(i_meas),
                    )

                # Guardar sólo barridos completados.
                if self.is_running and current_sweep_data:
                    all_curves[sweep_idx] = {
                        "points": current_sweep_data,
                        "temp": t_obj_fwd,
                    }

                sweep_idx += 1

                if not self.is_running:
                    break

                # =============================================
                # BARRIDO DE VUELTA (HISTÉRESIS)
                # =============================================
                if hysteresis:
                    t_obj_rev = self._read_temperature()

                    self.sweep_changed.emit(
                        sweep_idx, "Rev"
                    )

                    if t_obj_rev is not None:
                        self.temp_measured.emit(
                            sweep_idx, t_obj_rev
                        )

                    current_sweep_data = []

                    for v in v_rev:
                        if not self.is_running:
                            break

                        if self.is_demo:
                            i_meas = self._generate_demo_point(
                                float(v)
                            )

                            self._wait_interval(delay)

                        else:
                            v_meas, i_meas = (
                                driver.measure_iv_point(
                                    float(v),
                                    delay,
                                )
                            )

                        current_sweep_data.append(
                            (float(v), float(i_meas))
                        )

                        self.point_received.emit(
                            sweep_idx,
                            "Rev",
                            float(v),
                            float(i_meas),
                        )

                    if self.is_running and current_sweep_data:
                        all_curves[sweep_idx] = {
                            "points": current_sweep_data,
                            "temp": t_obj_rev,
                        }

                    sweep_idx += 1

                if not self.is_running:
                    break

                # =============================================
                # INTERVALO ENTRE CICLOS
                # =============================================
                if cycle < n_cycles and self.is_running:

                    if not self.is_demo:
                        if stress_mode:
                            # Mantener la polarización durante
                            # el intervalo de estrés.
                            driver.set_bias_voltage(v_bias)
                        else:
                            # En reposo, desactivar la salida.
                            # No dejar una fuente habilitada
                            # a 0 V conectada a la celda.
                            driver.disable_output()

                    self._wait_interval(interval)

            # Fin de los ciclos.

        except Exception as e:
            error_message = (
                f"Error durante la adquisición: {e}"
            )

        finally:
            # -------------------------------------------------
            # 4. APAGADO Y LIMPIEZA
            # -------------------------------------------------
            self._safe_shutdown()

        elapsed = time.monotonic() - start_time

        # -----------------------------------------------------
        # 5. NOTIFICAR EL RESULTADO A LA INTERFAZ
        # -----------------------------------------------------
        if error_message is not None:
            self.error.emit(error_message)
        else:
            stats = {
                "min": 0,
                "max": elapsed,
                "avg": elapsed / n_cycles,
            }

            cancelled = not self.is_running

            self.finished.emit(
                all_curves,
                stats,
                cancelled,
            )

    def _read_temperature(self):
        """Lee la temperatura superficial si existe el sensor."""

        if self.is_demo:
            return None

        thermal = getattr(
            self.controller, "thermal", None
        )

        if thermal is None:
            return None

        try:
            t_amb, t_obj = thermal.get_temperatures()

            if t_obj is None:
                return None

            t_obj = float(t_obj)

            if not math.isfinite(t_obj):
                return None

            self.temp_measured  # Referencia a la señal de temperatura
            return t_obj

        except Exception as e:
            # El fallo del sensor térmico no debe convertirse
            # automáticamente en una corriente inventada ni
            # interrumpir el barrido eléctrico.
            print(
                f"Advertencia: no se pudo leer "
                f"la temperatura: {e}"
            )
            return None

    def _generate_demo_point(self, v):
        """Genera una curva ilustrativa sin utilizar hardware real."""

        if pv_analytics is not None:
            demo_function = getattr(
                pv_analytics, "generate_demo_point", None
            )

            if callable(demo_function):
                try:
                    value = float(demo_function(v))

                    if (
                        math.isfinite(value)
                        and abs(value) < 1.0
                    ):
                        return value

                except Exception:
                    pass

        # Modelo lineal simplificado para demostraciones.
        # No representa una caracterización experimental real.
        isc = 0.015   # A
        voc = 0.6     # V

        current = isc * (1.0 - float(v) / voc)

        noise = random.uniform(-2e-5, 2e-5)

        return current + noise

    def _wait_interval(self, seconds: float):
        """Espera comprobando periódicamente si se solicitó detener."""

        deadline = time.monotonic() + max(0.0, seconds)

        while self.is_running:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                break

            time.sleep(min(0.1, remaining))

    def _safe_shutdown(self):
        """Apaga la fuente e intenta devolver el motor a Home."""

        if self.is_demo:
            return

        # 1. Apagar la salida de la Keithley.
        driver = getattr(
            self.controller, "driver", None
        )

        if driver is not None and driver.is_connected:
            try:
                driver.disable_output()
            except Exception as e:
                print(
                    "ALERTA: no se pudo solicitar "
                    f"el apagado de la Keithley: {e}"
                )

        # 2. Intentar devolver el motor a su posición de Home.
        motor = getattr(
            self.controller, "motor", None
        )

        if motor is not None:
            try:
                motor.home()
            except Exception as e:
                print(
                    "Advertencia: no se pudo regresar "
                    f"el motor a Home: {e}"
                )

    def stop(self):
        """Solicita detener la adquisición de manera controlada."""
        self.is_running = False