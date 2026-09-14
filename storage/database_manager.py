# storage/database_manager.py
import sqlite3
import os

class DatabaseManager:
    """
    Capa de Almacenamiento: Gestión de la base de datos relacional (SQLite).
    Diseñado para operaciones institucionales internas del Laboratorio de Dispositivos Orgánicos (UPIITA).
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """Genera una conexión a SQLite con el soporte de claves foráneas activado."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Inicializa el esquema relacional asegurando integridad referencial y soporte histórico."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabla Holders (Sustratos)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS holders (
                    id TEXT PRIMARY KEY,
                    autor TEXT,
                    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla Celdas (Ahora incluye area_cm2)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS celdas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    holder_id TEXT,
                    posicion INTEGER,
                    area_cm2 REAL DEFAULT 0.09,
                    FOREIGN KEY (holder_id) REFERENCES holders(id),
                    UNIQUE(holder_id, posicion)
                )
            """)
            
            # Tabla Experimentos (Ahora incluye isc y notas)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experimentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    celda_id INTEGER,
                    tipo_prueba TEXT,
                    irradiancia_objetivo REAL,
                    voc REAL,
                    isc REAL,
                    jsc REAL,
                    ff REAL,
                    eficiencia REAL,
                    temperatura_avg REAL DEFAULT 25.0,
                    notas TEXT,
                    fecha_hora DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (celda_id) REFERENCES celdas(id)
                )
            """)
            
            # Tabla Puntos (V, I, Sentido)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS barridos_puntos (
                    experimento_id INTEGER,
                    voltaje REAL,
                    corriente REAL,
                    sentido TEXT,
                    FOREIGN KEY (experimento_id) REFERENCES experimentos(id)
                )
            """)

            # Tabla: calibracion (Motor y BPW20RF)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibracion (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_pasos INTEGER,
                    irradiancia_medida REAL,
                    corriente_sensor REAL,
                    fecha_calibracion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def create_or_get_holder(self, holder_id: str, autor: str) -> str:
        """Asegura la existencia del sustrato (holder) en la base de datos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM holders WHERE id = ?", (holder_id,))
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "INSERT INTO holders (id, autor) VALUES (?, ?)", 
                    (holder_id, autor)
                )
                conn.commit()
            return holder_id

    def create_or_get_celda(self, holder_id: str, posicion: int, area: float = 0.09) -> int:
        """Recupera el ID de una celda, o la crea guardando su área activa."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM celdas WHERE holder_id = ? AND posicion = ?", (holder_id, posicion))
            row = cursor.fetchone()
            if row:
                # Si la celda ya existe, actualizamos su área por si el usuario la midió con más precisión
                celda_id = row['id']
                cursor.execute("UPDATE celdas SET area_cm2 = ? WHERE id = ?", (area, celda_id))
                return celda_id
            else:
                # Si es nueva, la insertamos con su área
                cursor.execute(
                    "INSERT INTO celdas (holder_id, posicion, area_cm2) VALUES (?, ?, ?)", 
                    (holder_id, posicion, area)
                )
                return cursor.lastrowid
            
    def save_experiment_sweep(self, celda_id: int, tipo_prueba: str, irradiancia: float, metrics: dict, points: list, sentido: str = "ida", notas: str = "") -> int:
        """Guarda un barrido completo con todas sus métricas calculadas y notas del operador."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Usar None en lugar de 0.0 si las analíticas fallaron o no ocurrieron
            voc = metrics.get('voc', None)
            isc = metrics.get('isc', None)
            jsc = metrics.get('jsc', None)
            ff = metrics.get('ff', None)
            eta = metrics.get('eta', None)
            
            # 1. Guardar metadatos del experimento
            cursor.execute("""
                INSERT INTO experimentos 
                (celda_id, tipo_prueba, irradiancia_objetivo, voc, isc, jsc, ff, eficiencia, notas) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (celda_id, tipo_prueba, irradiancia, voc, isc, jsc, ff, eta, notas))
            
            exp_id = cursor.lastrowid
            
            # 2. Guardar todos los puntos coordenados (V, I)
            puntos_db = [(exp_id, p[0], p[1], sentido) for p in points]
            cursor.executemany("""
                INSERT INTO barridos_puntos (experimento_id, voltaje, corriente, sentido)
                VALUES (?, ?, ?, ?)
            """, puntos_db)
            
            return exp_id
        
    def get_full_history(self) -> list:
        """Recupera el historial completo unificando experimentos, celdas y holders."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Actualizado para coincidir exactamente con el esquema de la base de datos
                query = """
                    SELECT 
                        e.id as exp_id, 
                        e.tipo_prueba, 
                        e.irradiancia_objetivo, 
                        e.voc, 
                        e.isc, 
                        e.jsc, 
                        e.ff, 
                        e.eficiencia, 
                        e.temperatura_avg, 
                        e.notas,
                        e.fecha_hora,
                        c.posicion as cell_num,
                        c.area_cm2, 
                        h.id as holder_id, 
                        h.autor 
                    FROM experimentos e
                    JOIN celdas c ON e.celda_id = c.id
                    JOIN holders h ON c.holder_id = h.id
                    ORDER BY h.id, c.posicion, e.id ASC
                """
                cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error consultando historial SQL: {e}")
            return []
        
    def get_sweep_points(self, experiment_id: int) -> list:
        """Recupera los puntos de un barrido utilizando el esquema actualizado."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT voltaje, corriente 
                    FROM barridos_puntos 
                    WHERE experimento_id = ? 
                    ORDER BY rowid ASC
                """, (experiment_id,))
                return [(row['voltaje'], row['corriente']) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error recuperando puntos: {e}")
            return []

    def delete_experiments(self, exp_ids: list) -> bool:
        """Borra experimentos y sus puntos en cascada respetando las Foreign Keys."""
        if not exp_ids: return False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Crear los placeholders (?, ?, ?) según la cantidad de IDs
                placeholders = ",".join("?" for _ in exp_ids)
                
                # 1. Borrar primero los puntos asociados (Hijos)
                cursor.execute(f"DELETE FROM barridos_puntos WHERE experimento_id IN ({placeholders})", exp_ids)
                
                # 2. Borrar los metadatos del experimento (Padres)
                cursor.execute(f"DELETE FROM experimentos WHERE id IN ({placeholders})", exp_ids)
                
                conn.commit()
            return True
        except Exception as e:
            print(f"Error borrando experimentos: {e}")
            return False

    def get_all_holders(self) -> list:
        """Devuelve una lista con todos los nombres de los holders."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM holders")
                return [row['id'] for row in cursor.fetchall()]
        except Exception:
            return []
            
    def get_experiment_meta(self, exp_id: int) -> dict:
        """Extrae la metadata agrupada de un experimento para el Historial SQL."""
        try:
            with self._get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.*, c.holder_id, c.posicion 
                    FROM experimentos e JOIN celdas c ON e.celda_id = c.id
                    WHERE e.id = ?
                """, (exp_id,))
                row = cur.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}