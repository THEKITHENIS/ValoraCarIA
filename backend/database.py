# =============================================================================
# SENTINEL PRO - DATABASE MANAGER
# Gestión completa de base de datos SQLite para sistema de flotas
# =============================================================================

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import os

class DatabaseManager:
    """Gestor de base de datos para SENTINEL PRO Fleet Management"""

    def __init__(self, db_path: str = '../db/sentinel.db'):
        """
        Inicializa el gestor de base de datos

        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path
        self._ensure_db_directory()
        self._initialize_database()

    def _ensure_db_directory(self):
        """Asegura que el directorio de la base de datos existe"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """
        Obtiene una conexión a la base de datos

        Returns:
            Conexión SQLite configurada
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
        return conn

    def _initialize_database(self):
        """Crea las tablas si no existen"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Tabla de vehículos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vin TEXT UNIQUE,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    fuel_type TEXT NOT NULL,
                    transmission TEXT NOT NULL,
                    mileage INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    active BOOLEAN DEFAULT 1,
                    notes TEXT
                )
            ''')

            # Tabla de viajes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trips (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    distance REAL DEFAULT 0,
                    duration INTEGER DEFAULT 0,
                    avg_speed REAL DEFAULT 0,
                    max_speed REAL DEFAULT 0,
                    avg_rpm REAL DEFAULT 0,
                    max_rpm REAL DEFAULT 0,
                    avg_load REAL DEFAULT 0,
                    fuel_consumed REAL DEFAULT 0,
                    health_score INTEGER DEFAULT 100,
                    gps_data TEXT,
                    csv_file TEXT,
                    active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            ''')

            # Tabla de mantenimiento
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS maintenance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    mileage INTEGER,
                    cost REAL DEFAULT 0,
                    mechanic TEXT,
                    next_service_km INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            ''')

            # Tabla de datos OBD (optimizada para alta frecuencia)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS obd_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    rpm REAL,
                    speed REAL,
                    coolant_temp REAL,
                    intake_temp REAL,
                    maf REAL,
                    engine_load REAL,
                    throttle_pos REAL,
                    fuel_pressure REAL,
                    latitude REAL,
                    longitude REAL,
                    FOREIGN KEY (trip_id) REFERENCES trips(id)
                )
            ''')

            # Tabla de alertas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    trip_id INTEGER,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    value REAL,
                    threshold REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    acknowledged BOOLEAN DEFAULT 0,
                    acknowledged_at TIMESTAMP,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                    FOREIGN KEY (trip_id) REFERENCES trips(id)
                )
            ''')

            # Tabla de reglas de alertas (configuración)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER,
                    name TEXT NOT NULL,
                    parameter TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    severity TEXT NOT NULL,
                    message_template TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    notify_email BOOLEAN DEFAULT 0,
                    notify_sound BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            ''')

            # Tabla de importaciones CSV
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS imports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER,
                    source_type TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    rows_total INTEGER DEFAULT 0,
                    rows_imported INTEGER DEFAULT 0,
                    rows_skipped INTEGER DEFAULT 0,
                    trips_created INTEGER DEFAULT 0,
                    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    imported_by TEXT,
                    can_rollback BOOLEAN DEFAULT 1,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            ''')

            # Tabla de perfiles de PIDs por vehículo
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vehicle_pids_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER NOT NULL,
                    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_pids INTEGER NOT NULL,
                    pids_data TEXT NOT NULL,
                    protocol TEXT,
                    FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
                )
            ''')

            # Tabla de datos OBD extendidos (OBDb) - NO MODIFICAR obd_data original
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS obd_extended (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trip_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- Fuel system
                    fuel_trim_short_1 REAL,
                    fuel_trim_long_1 REAL,
                    fuel_trim_short_2 REAL,
                    fuel_trim_long_2 REAL,
                    fuel_system_status TEXT,
                    fuel_level REAL,

                    -- O2 sensors
                    o2_b1s1 REAL,
                    o2_b1s2 REAL,
                    o2_b2s1 REAL,
                    o2_b2s2 REAL,
                    lambda_b1s1 REAL,
                    lambda_b1s2 REAL,

                    -- Emissions
                    egr_commanded REAL,
                    egr_error REAL,
                    evap_purge REAL,
                    evap_vapor_pressure REAL,

                    -- Exhaust
                    exhaust_temp_b1s1 REAL,
                    exhaust_temp_b1s2 REAL,
                    exhaust_temp_b2s1 REAL,
                    exhaust_temp_b2s2 REAL,
                    catalyst_temp_b1s1 REAL,
                    catalyst_temp_b2s1 REAL,

                    -- DPF (diesel)
                    dpf_temperature REAL,
                    dpf_pressure REAL,
                    dpf_soot_load REAL,

                    -- Battery (hybrid/electric)
                    battery_voltage REAL,
                    battery_current REAL,
                    battery_soc REAL,

                    -- Diagnostics
                    mil_status BOOLEAN,
                    dtc_count INTEGER,
                    monitor_status TEXT,

                    FOREIGN KEY (trip_id) REFERENCES trips(id)
                )
            ''')

            # Índices para mejorar performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_vehicle ON trips(vehicle_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trips_start ON trips(start_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_obd_trip ON obd_data(trip_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_obd_timestamp ON obd_data(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle ON maintenance(vehicle_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_vehicle ON alerts(vehicle_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_rules_vehicle ON alert_rules(vehicle_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_rules_enabled ON alert_rules(enabled)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_imports_vehicle ON imports(vehicle_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_imports_hash ON imports(file_hash)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pids_profiles_vehicle ON vehicle_pids_profiles(vehicle_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pids_profiles_date ON vehicle_pids_profiles(scan_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_obd_extended_trip ON obd_extended(trip_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_obd_extended_timestamp ON obd_extended(timestamp)')

            conn.commit()
            print("[DB] ✓ Base de datos inicializada correctamente")

        except Exception as e:
            print(f"[DB] ✗ Error inicializando base de datos: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    # =========================================================================
    # GESTIÓN DE VEHÍCULOS
    # =========================================================================

    def create_vehicle(self, vin: str, brand: str, model: str, year: int,
                      fuel_type: str, transmission: str, mileage: int = 0,
                      notes: str = None) -> int:
        """
        Crea un nuevo vehículo en la base de datos

        Args:
            vin: VIN del vehículo
            brand: Marca
            model: Modelo
            year: Año
            fuel_type: Tipo de combustible
            transmission: Tipo de transmisión
            mileage: Kilometraje inicial
            notes: Notas adicionales

        Returns:
            ID del vehículo creado
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO vehicles (vin, brand, model, year, fuel_type,
                                    transmission, mileage, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (vin, brand, model, year, fuel_type, transmission, mileage, notes))

            vehicle_id = cursor.lastrowid
            conn.commit()
            print(f"[DB] ✓ Vehículo creado: {brand} {model} (ID: {vehicle_id})")
            return vehicle_id

        except sqlite3.IntegrityError:
            print(f"[DB] ✗ VIN duplicado: {vin}")
            raise ValueError("VIN ya existe en la base de datos")
        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error creando vehículo: {e}")
            raise
        finally:
            conn.close()

    def get_vehicle(self, vehicle_id: int) -> Optional[Dict]:
        """
        Obtiene un vehículo por ID

        Args:
            vehicle_id: ID del vehículo

        Returns:
            Diccionario con datos del vehículo o None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM vehicles WHERE id = ? AND active = 1', (vehicle_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        finally:
            conn.close()

    def get_all_vehicles(self, active_only: bool = True) -> List[Dict]:
        """
        Obtiene todos los vehículos

        Args:
            active_only: Solo vehículos activos

        Returns:
            Lista de vehículos
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if active_only:
                cursor.execute('SELECT * FROM vehicles WHERE active = 1 ORDER BY created_at DESC')
            else:
                cursor.execute('SELECT * FROM vehicles ORDER BY created_at DESC')

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def update_vehicle(self, vehicle_id: int, **kwargs) -> bool:
        """
        Actualiza un vehículo

        Args:
            vehicle_id: ID del vehículo
            **kwargs: Campos a actualizar

        Returns:
            True si se actualizó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Campos permitidos para actualizar
            allowed_fields = ['brand', 'model', 'year', 'fuel_type', 'transmission',
                            'mileage', 'notes', 'vin']

            updates = []
            values = []

            for key, value in kwargs.items():
                if key in allowed_fields:
                    updates.append(f"{key} = ?")
                    values.append(value)

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(vehicle_id)

            query = f"UPDATE vehicles SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)

            conn.commit()
            print(f"[DB] ✓ Vehículo {vehicle_id} actualizado")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error actualizando vehículo: {e}")
            raise
        finally:
            conn.close()

    def delete_vehicle(self, vehicle_id: int, hard_delete: bool = False) -> bool:
        """
        Elimina (desactiva) un vehículo

        Args:
            vehicle_id: ID del vehículo
            hard_delete: Eliminar permanentemente (no recomendado)

        Returns:
            True si se eliminó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if hard_delete:
                cursor.execute('DELETE FROM vehicles WHERE id = ?', (vehicle_id,))
            else:
                cursor.execute('UPDATE vehicles SET active = 0 WHERE id = ?', (vehicle_id,))

            conn.commit()
            print(f"[DB] ✓ Vehículo {vehicle_id} {'eliminado' if hard_delete else 'desactivado'}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error eliminando vehículo: {e}")
            raise
        finally:
            conn.close()

    # =========================================================================
    # GESTIÓN DE VIAJES
    # =========================================================================

    def start_trip(self, vehicle_id: int) -> int:
        """
        Inicia un nuevo viaje

        Args:
            vehicle_id: ID del vehículo

        Returns:
            ID del viaje creado
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO trips (vehicle_id, start_time, active)
                VALUES (?, CURRENT_TIMESTAMP, 1)
            ''', (vehicle_id,))

            trip_id = cursor.lastrowid
            conn.commit()
            print(f"[DB] ✓ Viaje iniciado: ID {trip_id} para vehículo {vehicle_id}")
            return trip_id

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error iniciando viaje: {e}")
            raise
        finally:
            conn.close()

    def end_trip(self, trip_id: int, stats: Dict = None) -> bool:
        """
        Finaliza un viaje

        Args:
            trip_id: ID del viaje
            stats: Estadísticas del viaje

        Returns:
            True si se finalizó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if stats:
                cursor.execute('''
                    UPDATE trips
                    SET end_time = CURRENT_TIMESTAMP,
                        distance = ?,
                        duration = ?,
                        avg_speed = ?,
                        max_speed = ?,
                        avg_rpm = ?,
                        max_rpm = ?,
                        avg_load = ?,
                        fuel_consumed = ?,
                        health_score = ?,
                        active = 0
                    WHERE id = ?
                ''', (
                    stats.get('distance', 0),
                    stats.get('duration', 0),
                    stats.get('avg_speed', 0),
                    stats.get('max_speed', 0),
                    stats.get('avg_rpm', 0),
                    stats.get('max_rpm', 0),
                    stats.get('avg_load', 0),
                    stats.get('fuel_consumed', 0),
                    stats.get('health_score', 100),
                    trip_id
                ))
            else:
                cursor.execute('''
                    UPDATE trips
                    SET end_time = CURRENT_TIMESTAMP, active = 0
                    WHERE id = ?
                ''', (trip_id,))

            conn.commit()
            print(f"[DB] ✓ Viaje {trip_id} finalizado")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error finalizando viaje: {e}")
            raise
        finally:
            conn.close()

    def save_obd_data_batch(self, trip_id: int, data_points: List[Dict]) -> bool:
        """
        Guarda múltiples puntos de datos OBD (batch insert)

        Args:
            trip_id: ID del viaje
            data_points: Lista de puntos de datos OBD

        Returns:
            True si se guardó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.executemany('''
                INSERT INTO obd_data (
                    trip_id, timestamp, rpm, speed, coolant_temp, intake_temp,
                    maf, engine_load, throttle_pos, fuel_pressure, latitude, longitude
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', [
                (
                    trip_id,
                    point.get('timestamp', datetime.now().isoformat()),
                    point.get('rpm'),
                    point.get('speed'),
                    point.get('coolant_temp'),
                    point.get('intake_temp'),
                    point.get('maf'),
                    point.get('engine_load'),
                    point.get('throttle_pos'),
                    point.get('fuel_pressure'),
                    point.get('latitude'),
                    point.get('longitude')
                ) for point in data_points
            ])

            conn.commit()
            print(f"[DB] ✓ {len(data_points)} puntos OBD guardados para viaje {trip_id}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error guardando datos OBD: {e}")
            raise
        finally:
            conn.close()

    def save_extended_signals(self, trip_id: int, extended_signals: Dict) -> bool:
        """
        Guarda señales OBDb extendidas en la tabla obd_extended.

        Args:
            trip_id: ID del viaje
            extended_signals: Dict con señales categorizadas

        Returns:
            True si se guardó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Extraer valores específicos de cada categoría
            fuel_system = extended_signals.get('fuel_system', {})
            o2_sensors = extended_signals.get('o2_sensors', {})
            emissions = extended_signals.get('emissions', {})
            exhaust = extended_signals.get('exhaust', {})
            dpf = extended_signals.get('dpf', {})
            battery = extended_signals.get('battery', {})
            diagnostics = extended_signals.get('diagnostics', {})

            cursor.execute('''
                INSERT INTO obd_extended (
                    trip_id,
                    fuel_trim_short_1, fuel_trim_long_1,
                    fuel_trim_short_2, fuel_trim_long_2,
                    fuel_system_status, fuel_level,
                    o2_b1s1, o2_b1s2, o2_b2s1, o2_b2s2,
                    lambda_b1s1, lambda_b1s2,
                    egr_commanded, egr_error, evap_purge, evap_vapor_pressure,
                    exhaust_temp_b1s1, exhaust_temp_b1s2,
                    catalyst_temp_b1s1,
                    dpf_temperature, dpf_pressure, dpf_soot_load,
                    battery_voltage, battery_current, battery_soc,
                    mil_status, dtc_count, monitor_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trip_id,
                # Fuel system
                self._extract_signal_value(fuel_system, 'SHORT_FUEL_TRIM_1'),
                self._extract_signal_value(fuel_system, 'LONG_FUEL_TRIM_1'),
                self._extract_signal_value(fuel_system, 'SHORT_FUEL_TRIM_2'),
                self._extract_signal_value(fuel_system, 'LONG_FUEL_TRIM_2'),
                self._extract_signal_value(fuel_system, 'FUEL_SYSTEM_STATUS'),
                self._extract_signal_value(fuel_system, 'FUEL_LEVEL'),
                # O2 sensors
                self._extract_signal_value(o2_sensors, 'O2_B1S1'),
                self._extract_signal_value(o2_sensors, 'O2_B1S2'),
                self._extract_signal_value(o2_sensors, 'O2_B2S1'),
                self._extract_signal_value(o2_sensors, 'O2_B2S2'),
                self._extract_signal_value(o2_sensors, 'LAMBDA_B1S1'),
                self._extract_signal_value(o2_sensors, 'LAMBDA_B1S2'),
                # Emissions
                self._extract_signal_value(emissions, 'COMMANDED_EGR'),
                self._extract_signal_value(emissions, 'EGR_ERROR'),
                self._extract_signal_value(emissions, 'EVAP_PURGE'),
                self._extract_signal_value(emissions, 'EVAP_VAPOR_PRESSURE'),
                # Exhaust
                self._extract_signal_value(exhaust, 'EXHAUST_TEMP_B1S1'),
                self._extract_signal_value(exhaust, 'EXHAUST_TEMP_B1S2'),
                self._extract_signal_value(exhaust, 'CATALYST_TEMP_B1S1'),
                # DPF
                self._extract_signal_value(dpf, 'DPF_TEMPERATURE'),
                self._extract_signal_value(dpf, 'DPF_PRESSURE'),
                self._extract_signal_value(dpf, 'DPF_SOOT_LOAD'),
                # Battery
                self._extract_signal_value(battery, 'BATTERY_VOLTAGE'),
                self._extract_signal_value(battery, 'BATTERY_CURRENT'),
                self._extract_signal_value(battery, 'BATTERY_SOC'),
                # Diagnostics
                self._extract_signal_value(diagnostics, 'MIL_STATUS'),
                self._extract_signal_value(diagnostics, 'DTC_COUNT'),
                self._extract_signal_value(diagnostics, 'MONITOR_STATUS')
            ))

            conn.commit()
            print(f"[DB] ✓ Señales extendidas guardadas para viaje {trip_id}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error guardando señales extendidas: {e}")
            return False
        finally:
            conn.close()

    def _extract_signal_value(self, signal_dict: Dict, signal_id: str):
        """
        Extrae valor de una señal del dict de señales.

        Args:
            signal_dict: Dict de señales
            signal_id: ID de la señal

        Returns:
            Valor de la señal o None
        """
        if signal_id in signal_dict:
            signal_info = signal_dict[signal_id]
            if isinstance(signal_info, dict):
                return signal_info.get('value')
            return signal_info
        return None

    def get_trip(self, trip_id: int) -> Optional[Dict]:
        """
        Obtiene un viaje por ID

        Args:
            trip_id: ID del viaje

        Returns:
            Diccionario con datos del viaje
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM trips WHERE id = ?', (trip_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        finally:
            conn.close()

    def get_vehicle_trips(self, vehicle_id: int, limit: int = 50) -> List[Dict]:
        """
        Obtiene viajes de un vehículo

        Args:
            vehicle_id: ID del vehículo
            limit: Número máximo de viajes

        Returns:
            Lista de viajes
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM trips
                WHERE vehicle_id = ?
                ORDER BY start_time DESC
                LIMIT ?
            ''', (vehicle_id, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_trip_obd_data(self, trip_id: int) -> List[Dict]:
        """
        Obtiene datos OBD de un viaje

        Args:
            trip_id: ID del viaje

        Returns:
            Lista de puntos de datos OBD
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM obd_data
                WHERE trip_id = ?
                ORDER BY timestamp ASC
            ''', (trip_id,))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    # =========================================================================
    # GESTIÓN DE MANTENIMIENTO
    # =========================================================================

    def add_maintenance(self, vehicle_id: int, date: str, type: str,
                       description: str = None, mileage: int = None,
                       cost: float = 0, mechanic: str = None,
                       next_service_km: int = None) -> int:
        """
        Registra un mantenimiento

        Args:
            vehicle_id: ID del vehículo
            date: Fecha del mantenimiento
            type: Tipo de mantenimiento
            description: Descripción
            mileage: Kilometraje
            cost: Coste
            mechanic: Mecánico
            next_service_km: Próximo servicio en km

        Returns:
            ID del registro de mantenimiento
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO maintenance (
                    vehicle_id, date, type, description, mileage,
                    cost, mechanic, next_service_km
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (vehicle_id, date, type, description, mileage, cost, mechanic, next_service_km))

            maintenance_id = cursor.lastrowid
            conn.commit()
            print(f"[DB] ✓ Mantenimiento registrado: ID {maintenance_id}")
            return maintenance_id

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error registrando mantenimiento: {e}")
            raise
        finally:
            conn.close()

    def get_vehicle_maintenance(self, vehicle_id: int, limit: int = 50) -> List[Dict]:
        """
        Obtiene historial de mantenimiento de un vehículo

        Args:
            vehicle_id: ID del vehículo
            limit: Número máximo de registros

        Returns:
            Lista de mantenimientos
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM maintenance
                WHERE vehicle_id = ?
                ORDER BY date DESC
                LIMIT ?
            ''', (vehicle_id, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    # =========================================================================
    # ESTADÍSTICAS Y ANALYTICS
    # =========================================================================

    def get_vehicle_stats(self, vehicle_id: int,
                         start_date: str = None,
                         end_date: str = None) -> Dict:
        """
        Obtiene estadísticas de un vehículo

        Args:
            vehicle_id: ID del vehículo
            start_date: Fecha inicio (opcional)
            end_date: Fecha fin (opcional)

        Returns:
            Diccionario con estadísticas
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Query base
            base_query = 'SELECT * FROM trips WHERE vehicle_id = ? AND active = 0'
            params = [vehicle_id]

            if start_date:
                base_query += ' AND start_time >= ?'
                params.append(start_date)

            if end_date:
                base_query += ' AND start_time <= ?'
                params.append(end_date)

            cursor.execute(base_query, params)
            trips = [dict(row) for row in cursor.fetchall()]

            if not trips:
                return {
                    'total_trips': 0,
                    'total_distance': 0,
                    'total_duration': 0,
                    'avg_speed': 0,
                    'avg_health_score': 100
                }

            total_distance = sum(t.get('distance', 0) for t in trips)
            total_duration = sum(t.get('duration', 0) for t in trips)
            avg_speed = sum(t.get('avg_speed', 0) for t in trips) / len(trips)
            avg_health = sum(t.get('health_score', 100) for t in trips) / len(trips)

            return {
                'total_trips': len(trips),
                'total_distance': round(total_distance, 2),
                'total_duration': total_duration,
                'avg_speed': round(avg_speed, 2),
                'max_speed': max(t.get('max_speed', 0) for t in trips),
                'avg_health_score': round(avg_health, 2),
                'trips': trips
            }

        finally:
            conn.close()

    def get_fleet_stats(self) -> Dict:
        """
        Obtiene estadísticas de toda la flota

        Returns:
            Diccionario con estadísticas de la flota
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Total vehículos activos
            cursor.execute('SELECT COUNT(*) as count FROM vehicles WHERE active = 1')
            total_vehicles = cursor.fetchone()['count']

            # Total viajes
            cursor.execute('SELECT COUNT(*) as count FROM trips WHERE active = 0')
            total_trips = cursor.fetchone()['count']

            # Distancia total
            cursor.execute('SELECT SUM(distance) as total FROM trips WHERE active = 0')
            total_distance = cursor.fetchone()['total'] or 0

            # Viajes activos
            cursor.execute('SELECT COUNT(*) as count FROM trips WHERE active = 1')
            active_trips = cursor.fetchone()['count']

            return {
                'total_vehicles': total_vehicles,
                'total_trips': total_trips,
                'total_distance': round(total_distance, 2),
                'active_trips': active_trips
            }

        finally:
            conn.close()

    # =========================================================================
    # SISTEMA DE ALERTAS
    # =========================================================================

    def create_alert(self, vehicle_id: int, alert_type: str, severity: str,
                    message: str, value: float = None, threshold: float = None,
                    trip_id: int = None) -> int:
        """
        Crea una alerta

        Args:
            vehicle_id: ID del vehículo
            alert_type: Tipo de alerta
            severity: Severidad (low, medium, high, critical)
            message: Mensaje
            value: Valor que disparó la alerta
            threshold: Umbral
            trip_id: ID del viaje (opcional)

        Returns:
            ID de la alerta
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO alerts (
                    vehicle_id, trip_id, alert_type, severity,
                    message, value, threshold
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (vehicle_id, trip_id, alert_type, severity, message, value, threshold))

            alert_id = cursor.lastrowid
            conn.commit()
            print(f"[DB] ⚠️  Alerta creada: {alert_type} - {message}")
            return alert_id

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error creando alerta: {e}")
            raise
        finally:
            conn.close()

    def get_vehicle_alerts(self, vehicle_id: int,
                          acknowledged: bool = None,
                          limit: int = 100) -> List[Dict]:
        """
        Obtiene alertas de un vehículo

        Args:
            vehicle_id: ID del vehículo
            acknowledged: Filtrar por estado de reconocimiento
            limit: Número máximo de alertas

        Returns:
            Lista de alertas
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if acknowledged is None:
                cursor.execute('''
                    SELECT * FROM alerts
                    WHERE vehicle_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (vehicle_id, limit))
            else:
                cursor.execute('''
                    SELECT * FROM alerts
                    WHERE vehicle_id = ? AND acknowledged = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (vehicle_id, 1 if acknowledged else 0, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_all_alerts(self, acknowledged: bool = None, limit: int = 100) -> List[Dict]:
        """
        Obtiene todas las alertas de la flota

        Args:
            acknowledged: Filtrar por estado de reconocimiento
            limit: Número máximo de alertas

        Returns:
            Lista de alertas con información del vehículo
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if acknowledged is None:
                cursor.execute('''
                    SELECT a.*, v.brand, v.model, v.vin
                    FROM alerts a
                    JOIN vehicles v ON a.vehicle_id = v.id
                    ORDER BY a.timestamp DESC
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT a.*, v.brand, v.model, v.vin
                    FROM alerts a
                    JOIN vehicles v ON a.vehicle_id = v.id
                    WHERE a.acknowledged = ?
                    ORDER BY a.timestamp DESC
                    LIMIT ?
                ''', (1 if acknowledged else 0, limit))

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def acknowledge_alert(self, alert_id: int) -> bool:
        """
        Marca una alerta como reconocida

        Args:
            alert_id: ID de la alerta

        Returns:
            True si se actualizó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE alerts
                SET acknowledged = 1, acknowledged_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (alert_id,))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error reconociendo alerta: {e}")
            raise
        finally:
            conn.close()

    def acknowledge_all_alerts(self, vehicle_id: int = None) -> int:
        """
        Marca todas las alertas como reconocidas

        Args:
            vehicle_id: ID del vehículo (opcional, todas si None)

        Returns:
            Número de alertas reconocidas
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if vehicle_id:
                cursor.execute('''
                    UPDATE alerts
                    SET acknowledged = 1, acknowledged_at = CURRENT_TIMESTAMP
                    WHERE vehicle_id = ? AND acknowledged = 0
                ''', (vehicle_id,))
            else:
                cursor.execute('''
                    UPDATE alerts
                    SET acknowledged = 1, acknowledged_at = CURRENT_TIMESTAMP
                    WHERE acknowledged = 0
                ''')

            count = cursor.rowcount
            conn.commit()
            print(f"[DB] ✓ {count} alertas reconocidas")
            return count

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error reconociendo alertas: {e}")
            raise
        finally:
            conn.close()

    # =========================================================================
    # GESTIÓN DE REGLAS DE ALERTAS
    # =========================================================================

    def create_alert_rule(self, vehicle_id: int, name: str, parameter: str,
                         condition: str, threshold: float, severity: str,
                         message_template: str = None, notify_email: bool = False,
                         notify_sound: bool = True) -> int:
        """
        Crea una regla de alerta

        Args:
            vehicle_id: ID del vehículo (None para regla global)
            name: Nombre de la regla
            parameter: Parámetro a monitorear (rpm, speed, coolant_temp, etc.)
            condition: Condición (>, <, >=, <=, ==, !=)
            threshold: Valor umbral
            severity: Severidad (low, medium, high, critical)
            message_template: Plantilla del mensaje
            notify_email: Enviar notificación por email
            notify_sound: Reproducir sonido de alerta

        Returns:
            ID de la regla creada
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO alert_rules (
                    vehicle_id, name, parameter, condition, threshold,
                    severity, message_template, notify_email, notify_sound
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (vehicle_id, name, parameter, condition, threshold, severity,
                  message_template, 1 if notify_email else 0, 1 if notify_sound else 0))

            rule_id = cursor.lastrowid
            conn.commit()
            print(f"[DB] ✓ Regla de alerta creada: {name} (ID: {rule_id})")
            return rule_id

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error creando regla de alerta: {e}")
            raise
        finally:
            conn.close()

    def get_alert_rule(self, rule_id: int) -> Optional[Dict]:
        """
        Obtiene una regla de alerta por ID

        Args:
            rule_id: ID de la regla

        Returns:
            Diccionario con la regla o None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM alert_rules WHERE id = ?', (rule_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

        finally:
            conn.close()

    def get_alert_rules(self, vehicle_id: int = None, enabled_only: bool = True) -> List[Dict]:
        """
        Obtiene reglas de alertas

        Args:
            vehicle_id: ID del vehículo (None para todas)
            enabled_only: Solo reglas habilitadas

        Returns:
            Lista de reglas
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if vehicle_id is not None:
                if enabled_only:
                    cursor.execute('''
                        SELECT * FROM alert_rules
                        WHERE (vehicle_id = ? OR vehicle_id IS NULL) AND enabled = 1
                        ORDER BY created_at DESC
                    ''', (vehicle_id,))
                else:
                    cursor.execute('''
                        SELECT * FROM alert_rules
                        WHERE vehicle_id = ? OR vehicle_id IS NULL
                        ORDER BY created_at DESC
                    ''', (vehicle_id,))
            else:
                if enabled_only:
                    cursor.execute('''
                        SELECT * FROM alert_rules
                        WHERE enabled = 1
                        ORDER BY created_at DESC
                    ''')
                else:
                    cursor.execute('SELECT * FROM alert_rules ORDER BY created_at DESC')

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        finally:
            conn.close()

    def update_alert_rule(self, rule_id: int, **kwargs) -> bool:
        """
        Actualiza una regla de alerta

        Args:
            rule_id: ID de la regla
            **kwargs: Campos a actualizar

        Returns:
            True si se actualizó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            allowed_fields = ['name', 'parameter', 'condition', 'threshold',
                            'severity', 'message_template', 'enabled',
                            'notify_email', 'notify_sound']

            updates = []
            values = []

            for key, value in kwargs.items():
                if key in allowed_fields:
                    updates.append(f"{key} = ?")
                    values.append(value)

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.append(rule_id)

            query = f"UPDATE alert_rules SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)

            conn.commit()
            print(f"[DB] ✓ Regla de alerta {rule_id} actualizada")
            return True

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error actualizando regla de alerta: {e}")
            raise
        finally:
            conn.close()

    def delete_alert_rule(self, rule_id: int) -> bool:
        """
        Elimina una regla de alerta

        Args:
            rule_id: ID de la regla

        Returns:
            True si se eliminó correctamente
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
            conn.commit()
            print(f"[DB] ✓ Regla de alerta {rule_id} eliminada")
            return cursor.rowcount > 0

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error eliminando regla de alerta: {e}")
            raise
        finally:
            conn.close()

    def toggle_alert_rule(self, rule_id: int, enabled: bool) -> bool:
        """
        Activa/desactiva una regla de alerta

        Args:
            rule_id: ID de la regla
            enabled: True para activar, False para desactivar

        Returns:
            True si se actualizó correctamente
        """
        return self.update_alert_rule(rule_id, enabled=1 if enabled else 0)

    # =========================================================================
    # GESTIÓN DE PERFILES DE PIDs
    # =========================================================================

    def save_vehicle_pids_profile(self, vehicle_id: int, profile_data: dict) -> int:
        """
        Guarda el perfil de PIDs disponibles de un vehículo

        Args:
            vehicle_id: ID del vehículo
            profile_data: Diccionario con información del perfil:
                - total_pids: Número total de PIDs disponibles
                - pids: Lista de PIDs con sus datos
                - protocol: Protocolo OBD del vehículo
                - scan_date: Fecha del escaneo

        Returns:
            ID del perfil creado
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO vehicle_pids_profiles (vehicle_id, total_pids, pids_data, protocol)
                VALUES (?, ?, ?, ?)
            ''', (
                vehicle_id,
                profile_data.get('total_pids', 0),
                json.dumps(profile_data),
                profile_data.get('protocol', 'Unknown')
            ))

            conn.commit()
            profile_id = cursor.lastrowid

            print(f"[DB] ✓ Perfil de PIDs guardado para vehículo {vehicle_id}: {profile_data.get('total_pids', 0)} PIDs")

            return profile_id

        except Exception as e:
            conn.rollback()
            print(f"[DB] ✗ Error guardando perfil de PIDs: {e}")
            raise
        finally:
            conn.close()

    def get_vehicle_pids_profile(self, vehicle_id: int) -> Optional[dict]:
        """
        Obtiene el perfil de PIDs más reciente de un vehículo

        Args:
            vehicle_id: ID del vehículo

        Returns:
            Diccionario con el perfil de PIDs o None si no existe
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT pids_data, scan_date, total_pids, protocol
                FROM vehicle_pids_profiles
                WHERE vehicle_id = ?
                ORDER BY scan_date DESC
                LIMIT 1
            ''', (vehicle_id,))

            row = cursor.fetchone()

            if row:
                profile = json.loads(row[0])
                profile['scan_date'] = row[1]
                profile['total_pids'] = row[2]
                profile['protocol'] = row[3]
                return profile

            return None

        except Exception as e:
            print(f"[DB] ✗ Error obteniendo perfil de PIDs: {e}")
            return None
        finally:
            conn.close()

    def get_all_pids_profiles(self, vehicle_id: int) -> List[dict]:
        """
        Obtiene todos los perfiles de PIDs históricos de un vehículo

        Args:
            vehicle_id: ID del vehículo

        Returns:
            Lista de perfiles ordenados por fecha (más reciente primero)
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT id, scan_date, total_pids, protocol
                FROM vehicle_pids_profiles
                WHERE vehicle_id = ?
                ORDER BY scan_date DESC
            ''', (vehicle_id,))

            profiles = []
            for row in cursor.fetchall():
                profiles.append({
                    'id': row[0],
                    'scan_date': row[1],
                    'total_pids': row[2],
                    'protocol': row[3]
                })

            return profiles

        except Exception as e:
            print(f"[DB] ✗ Error obteniendo perfiles de PIDs: {e}")
            return []
        finally:
            conn.close()


# Inicialización global
_db_instance = None

def get_db() -> DatabaseManager:
    """
    Obtiene instancia singleton del DatabaseManager

    Returns:
        Instancia de DatabaseManager
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


if __name__ == "__main__":
    # Test de inicialización
    print("=" * 70)
    print("SENTINEL PRO - DATABASE MANAGER TEST")
    print("=" * 70)

    db = DatabaseManager()
    print("\n[TEST] Base de datos inicializada correctamente")

    # Test: Crear vehículo
    try:
        vehicle_id = db.create_vehicle(
            vin="TEST123456789",
            brand="Seat",
            model="León 2.0 TDI",
            year=2018,
            fuel_type="diesel",
            transmission="manual",
            mileage=95000,
            notes="Vehículo de prueba"
        )
        print(f"[TEST] ✓ Vehículo creado con ID: {vehicle_id}")

        # Test: Obtener vehículo
        vehicle = db.get_vehicle(vehicle_id)
        print(f"[TEST] ✓ Vehículo obtenido: {vehicle['brand']} {vehicle['model']}")

        # Test: Iniciar viaje
        trip_id = db.start_trip(vehicle_id)
        print(f"[TEST] ✓ Viaje iniciado con ID: {trip_id}")

        # Test: Finalizar viaje
        db.end_trip(trip_id, {
            'distance': 25.5,
            'duration': 1800,
            'avg_speed': 51,
            'max_speed': 120
        })
        print(f"[TEST] ✓ Viaje finalizado")

        # Test: Estadísticas
        stats = db.get_vehicle_stats(vehicle_id)
        print(f"[TEST] ✓ Estadísticas: {stats['total_trips']} viajes, {stats['total_distance']} km")

    except Exception as e:
        print(f"[TEST] ✗ Error: {e}")

    print("\n✓ Tests completados")
