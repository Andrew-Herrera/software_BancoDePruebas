# hardware/keithley_driver.py

import math
import re
import time

import pyvisa


class KeithleyDriver:
    """Controlador para Keithley 2401 mediante VISA y GPIB."""

    def __init__(self, gpib_id: str = "24"):
        self.gpib_id = str(gpib_id).strip()

        self.device = None
        self.rm = None
        self.is_connected = False

        # Información para diagnóstico
        self.idn = ""
        self.last_error = ""
        self.output_enabled = False

        self.timeout_ms = 5000
        self.resource_string = (
            f"GPIB0::{self.gpib_id}::INSTR"
        )

    def _validate_identity(self, idn: str) -> None:
        """Comprueba que el instrumento sea un Keithley 2401."""

        is_keithley = "KEITHLEY" in idn.upper()

        is_model_2401 = re.search(
            r"\bMODEL\s*2401\b",
            idn,
            flags=re.IGNORECASE,
        ) is not None

        if not is_keithley or not is_model_2401:
            raise RuntimeError(
                "El dispositivo encontrado no corresponde "
                f"a una Keithley 2401. Respuesta recibida: {idn!r}"
            )

    def _require_connection(self) -> None:
        """Impide enviar comandos si no existe conexión válida."""

        if (
            not self.is_connected
            or self.device is None
        ):
            raise RuntimeError(
                "La Keithley 2401 no está conectada. "
                "Ejecuta connect() y verifica la dirección GPIB."
            )

    @staticmethod
    def _validate_voltage(voltage: float) -> float:
        """Valida que el voltaje sea numérico y finito."""

        voltage = float(voltage)

        if not math.isfinite(voltage):
            raise ValueError("El voltaje debe ser un número finito.")

        # Límite de tensión del modelo; el ensayo debe usar
        # límites operativos específicos y conservadores.
        if not -20.0 <= voltage <= 20.0:
            raise ValueError(
                "El voltaje solicitado está fuera del rango "
                "de ±20 V del modelo."
            )

        return voltage

    def connect(self) -> bool:
        """
        Abre la comunicación GPIB, identifica el modelo y
        prepara el instrumento con la salida apagada.
        """

        self.last_error = ""

        # Si ya existe una conexión, comprobar que sigue respondiendo.
        if self.is_connected and self.device is not None:
            try:
                idn = self.device.query("*IDN?").strip()
                self._validate_identity(idn)
                self.idn = idn
                return True
            except Exception:
                self.is_connected = False
                self.device = None
                self.output_enabled = False

        identified_2401 = False

        try:
            if self.rm is None:
                # Backend PyVISA-Py.
                self.rm = pyvisa.ResourceManager("@py")

            # Dirección GPIB: para tu equipo, GPIB0::24::INSTR.
            self.resource_string = (
                f"GPIB0::{self.gpib_id}::INSTR"
            )

            self.device = self.rm.open_resource(
                self.resource_string
            )

            self.device.timeout = self.timeout_ms
            self.device.read_termination = "\n"
            self.device.write_termination = "\n"

            # 1. Consultar la identidad antes de configurar.
            idn = self.device.query("*IDN?").strip()
            self.idn = idn

            self._validate_identity(idn)
            identified_2401 = True

            print(f"Instrumento detectado: {self.idn}")
            print(f"Recurso VISA: {self.resource_string}")

            # 2. Apagar la salida antes de preparar el equipo.
            self.device.write(":OUTP OFF")

            # 3. Restablecer y limpiar el estado del instrumento.
            self.device.write("*RST")
            self.device.write("*CLS")

            # 4. Asegurar nuevamente que la salida esté apagada.
            self.device.write(":OUTP OFF")

            # 5. Configurar la fuente en modo de voltaje fijo.
            self.device.write(":SOUR:FUNC VOLT")
            self.device.write(":SOUR:VOLT:MODE FIXED")
            self.device.write(":SOUR:VOLT 0")

            # 6. Configurar la medición de corriente.
            self.device.write(':SENS:FUNC "CURR"')
            self.device.write(":SENS:CURR:RANG:AUTO ON")

            # 7. Formato de respuesta: tensión y corriente.
            self.device.write(":FORM:ELEM VOLT,CURR")

            # 8. Comprobar que la salida realmente esté apagada.
            output_status = (
                self.device.query(":OUTP?").strip().upper()
            )

            if output_status not in ("0", "+0", "OFF"):
                self.device.write(":OUTP OFF")

                output_status = (
                    self.device.query(":OUTP?").strip().upper()
                )

                if output_status not in ("0", "+0", "OFF"):
                    raise RuntimeError(
                        "No fue posible confirmar que "
                        "la salida estuviera apagada."
                    )

            self.is_connected = True
            self.output_enabled = False

            print("Conexión con Keithley 2401 establecida.")
            print("Salida de la fuente: APAGADA.")

            return True

        except Exception as e:
            # Si ya confirmamos que es una 2401, intentar apagar
            # la salida antes de cerrar la comunicación.
            if identified_2401 and self.device is not None:
                try:
                    self.device.write(":OUTP OFF")
                except Exception:
                    pass

            self.last_error = (
                f"No se pudo conectar con {self.resource_string}: {e}"
            )

            print(f"ERROR: {self.last_error}")

            if self.device is not None:
                try:
                    self.device.close()
                except Exception:
                    pass

            self.device = None
            self.is_connected = False
            self.output_enabled = False

            return False

    def enable_output(self) -> None:
        """Activa la salida durante una operación de medida."""

        self._require_connection()

        if not self.output_enabled:
            try:
                self.device.write(":OUTP ON")
                self.output_enabled = True
            except Exception as e:
                self.disable_output()
                raise RuntimeError(
                    f"No fue posible activar la salida: {e}"
                ) from e

    def set_protection(
        self,
        compliance: float,
        nplc: float = 1.0,
    ) -> None:
        """Configura y verifica el límite de corriente y el NPLC."""

        self._require_connection()

        compliance = float(compliance)
        nplc = float(nplc)

        if not math.isfinite(compliance) or compliance <= 0:
            raise ValueError(
                "El límite de corriente debe ser positivo y finito."
            )

        if not math.isfinite(nplc) or not 0.01 <= nplc <= 10:
            raise ValueError(
                "El NPLC debe estar entre 0.01 y 10."
            )

        try:
            self.device.write(
                f":SENS:CURR:PROT {compliance}"
            )
            self.device.write(
                f":SENS:CURR:NPLC {nplc}"
            )

            actual_comp = float(
                self.device.query(":SENS:CURR:PROT?").strip()
            )

            actual_nplc = float(
                self.device.query(":SENS:CURR:NPLC?").strip()
            )

            tolerance = max(1e-9, abs(compliance) * 1e-3)

            if abs(actual_comp - compliance) > tolerance:
                raise RuntimeError(
                    f"Compliance solicitado: {compliance} A; "
                    f"configurado: {actual_comp} A."
                )

            if not math.isclose(
                actual_nplc,
                nplc,
                rel_tol=1e-3,
                abs_tol=1e-6,
            ):
                raise RuntimeError(
                    f"NPLC solicitado: {nplc}; "
                    f"configurado: {actual_nplc}."
                )

        except Exception as e:
            self.disable_output()
            raise RuntimeError(
                f"Error al configurar las protecciones: {e}"
            ) from e

    def set_bias_voltage(self, v_bias: float) -> None:
        """Aplica una tensión de polarización durante el ensayo."""

        self._require_connection()
        v_bias = self._validate_voltage(v_bias)

        try:
            self.device.write(f":SOUR:VOLT {v_bias}")
            self.enable_output()

        except Exception as e:
            self.disable_output()
            raise RuntimeError(
                f"Error al aplicar la polarización: {e}"
            ) from e

    def measure_iv_point(
        self,
        voltage: float,
        delay_s: float,
    ) -> tuple[float, float]:
        """
        Aplica un punto del barrido I-V y devuelve:
        (tensión medida en V, corriente medida en A).
        """

        self._require_connection()

        voltage = self._validate_voltage(voltage)
        delay_s = float(delay_s)

        if not math.isfinite(delay_s) or delay_s < 0:
            raise ValueError(
                "El tiempo de espera debe ser positivo o cero."
            )

        try:
            # Establecer el nivel antes de activar la salida.
            self.device.write(f":SOUR:VOLT {voltage}")

            # La salida sólo se activa cuando se solicita medir.
            self.enable_output()

            if delay_s > 0:
                time.sleep(delay_s)

            raw_response = self.device.query(":READ?").strip()
            values = raw_response.split(",")

            if len(values) < 2:
                raise RuntimeError(
                    f"Respuesta de medición inesperada: "
                    f"{raw_response!r}"
                )

            measured_voltage = float(values[0])
            measured_current = float(values[1])

            if not (
                math.isfinite(measured_voltage)
                and math.isfinite(measured_current)
            ):
                raise RuntimeError(
                    f"La medición contiene valores no finitos: "
                    f"{raw_response!r}"
                )

            return measured_voltage, measured_current

        except Exception as e:
            self.disable_output()
            raise RuntimeError(
                f"Fallo al medir en {voltage} V. "
                f"Se solicitó apagar la salida. Detalle: {e}"
            ) from e

    def disable_output(self) -> None:
        """Intenta apagar la salida, incluso ante un error."""

        if self.device is None:
            self.output_enabled = False
            return

        output_off_confirmed = False

        # Priorizar apagar la salida.
        try:
            self.device.write(":OUTP OFF")
            self.output_enabled = False
            output_off_confirmed = True
        except Exception as e:
            print(
                "ALERTA CRÍTICA: no se pudo confirmar "
                f"el apagado de la salida: {e}"
            )

        # Intentar llevar el nivel programado a cero.
        try:
            self.device.write(":SOUR:VOLT 0")
        except Exception as e:
            print(
                f"ALERTA: no se pudo establecer 0 V: {e}"
            )

        if not output_off_confirmed:
            # No afirmar que la salida está apagada si no
            # se pudo enviar el comando.
            self.output_enabled = None

    def close_session(self) -> None:
        """Apaga la salida y cierra la sesión VISA."""

        if self.device is not None:
            self.disable_output()

            try:
                self.device.close()
            except Exception as e:
                print(
                    f"Error al cerrar la sesión VISA: {e}"
                )

        self.device = None
        self.is_connected = False
        self.output_enabled = False

        if self.rm is not None:
            try:
                self.rm.close()
            except Exception:
                pass

            self.rm = None