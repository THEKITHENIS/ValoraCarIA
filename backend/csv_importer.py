"""
SENTINEL PRO - CSV Importer Module
Sistema avanzado de importación de datos CSV de múltiples fuentes
"""

import csv
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import re


class CSVImporter:
    """
    Importador universal de archivos CSV de diagnóstico automotriz
    Soporta múltiples formatos: Torque Pro, OBD11, Carista, VCDS, etc.
    """

    # Configuraciones de fuentes soportadas
    SUPPORTED_SOURCES = {
        'torque': {
            'name': 'Torque Pro',
            'identifier': ['Device Time', 'Longitude', 'Latitude', 'GPS Speed'],
            'mappings': {
                'timestamp': 'Device Time',
                'rpm': 'Engine RPM(rpm)',
                'speed': 'Speed (OBD)(km/h)',
                'coolant_temp': 'Engine Coolant Temperature(°C)',
                'intake_temp': 'Intake Air Temperature(°C)',
                'maf': 'Mass Air Flow Rate(g/s)',
                'engine_load': 'Engine Load(%)',
                'throttle_pos': 'Throttle Position(Manifold)(%)',
                'fuel_pressure': 'Fuel Pressure(kPa)',
                'latitude': 'Latitude',
                'longitude': 'Longitude',
            },
            'timestamp_format': '%Y-%m-%d %H:%M:%S.%f',
            'encoding': 'utf-8'
        },
        'obd11': {
            'name': 'OBD11',
            'identifier': ['Time', 'Engine Speed', 'Vehicle Speed'],
            'mappings': {
                'timestamp': 'Time',
                'rpm': 'Engine Speed',
                'speed': 'Vehicle Speed',
                'coolant_temp': 'Coolant Temperature',
                'intake_temp': 'Intake Air Temperature',
                'maf': 'MAF',
                'engine_load': 'Engine Load',
                'throttle_pos': 'Throttle Position'
            },
            'timestamp_format': '%Y-%m-%d %H:%M:%S',
            'encoding': 'utf-8'
        },
        'carista': {
            'name': 'Carista',
            'identifier': ['Timestamp', 'RPM', 'Speed'],
            'mappings': {
                'timestamp': 'Timestamp',
                'rpm': 'RPM',
                'speed': 'Speed',
                'coolant_temp': 'Coolant Temp',
                'intake_temp': 'Intake Air Temperature',
                'engine_load': 'Load',
                'throttle_pos': 'Throttle'
            },
            'timestamp_format': '%d/%m/%Y %H:%M:%S',
            'encoding': 'utf-8'
        },
        'vcds': {
            'name': 'VCDS/VAG-COM',
            'identifier': ['Time', 'RPM', 'Speed'],
            'mappings': {
                'timestamp': 'Time',
                'rpm': 'RPM',
                'speed': 'Speed (km/h)',
                'coolant_temp': 'Coolant',
                'intake_temp': 'Intake',
                'maf': 'Mass Air Flow',
                'engine_load': 'Load'
            },
            'timestamp_format': '%H:%M:%S.%f',
            'encoding': 'latin-1'
        },
        'sentinel_pro': {
            'name': 'SENTINEL PRO (Nativo)',
            'identifier': ['timestamp', 'rpm', 'speed', 'vehicle_id'],
            'mappings': {
                'timestamp': 'timestamp',
                'rpm': 'rpm',
                'speed': 'speed',
                'coolant_temp': 'coolant_temp',
                'intake_temp': 'intake_temp',
                'maf': 'maf',
                'engine_load': 'engine_load',
                'throttle_pos': 'throttle_pos',
                'fuel_pressure': 'fuel_pressure',
                'latitude': 'latitude',
                'longitude': 'longitude'
            },
            'timestamp_format': '%Y-%m-%d %H:%M:%S',
            'encoding': 'utf-8'
        },
        'generic': {
            'name': 'Genérico (Mapeo Manual)',
            'identifier': [],
            'mappings': {},
            'timestamp_format': None,
            'encoding': 'utf-8'
        }
    }

    def __init__(self, db_manager=None):
        """
        Inicializar importador

        Args:
            db_manager: Instancia de DatabaseManager para guardar datos
        """
        self.db = db_manager

    def detect_source(self, csv_path: str) -> Tuple[str, Dict]:
        """
        Detecta automáticamente el origen del CSV analizando headers

        Args:
            csv_path: Ruta al archivo CSV

        Returns:
            Tuple (source_type, config_dict)
        """
        try:
            # Intentar leer con diferentes encodings
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(csv_path, 'r', encoding=encoding) as f:
                        reader = csv.DictReader(f)
                        headers = reader.fieldnames

                        if not headers:
                            continue

                        # Comparar con identificadores de cada fuente
                        for source, config in self.SUPPORTED_SOURCES.items():
                            if source == 'generic':
                                continue

                            identifiers = config['identifier']
                            # Todos los identificadores deben estar presentes
                            if all(any(id.lower() in h.lower() for h in headers) for id in identifiers):
                                print(f"[CSV-IMPORTER] ✓ Detectado: {config['name']}")
                                return source, config

                        # Si llegamos aquí, no se detectó ninguna fuente conocida
                        print(f"[CSV-IMPORTER] No se detectó fuente conocida. Headers: {headers}")
                        return 'generic', self.SUPPORTED_SOURCES['generic']

                except UnicodeDecodeError:
                    continue

            # Si no se pudo leer con ningún encoding
            return 'generic', self.SUPPORTED_SOURCES['generic']

        except Exception as e:
            print(f"[CSV-IMPORTER] Error detectando fuente: {e}")
            return 'generic', self.SUPPORTED_SOURCES['generic']

    def analyze_csv(self, csv_path: str, source_type: Optional[str] = None) -> Dict:
        """
        Analiza un CSV y devuelve información detallada

        Args:
            csv_path: Ruta al archivo CSV
            source_type: Tipo de fuente (si ya se conoce)

        Returns:
            Dict con información del análisis
        """
        try:
            # Detectar fuente si no se especificó
            if not source_type:
                source_type, config = self.detect_source(csv_path)
            else:
                config = self.SUPPORTED_SOURCES.get(source_type, self.SUPPORTED_SOURCES['generic'])

            # Calcular hash del archivo
            file_hash = self._calculate_file_hash(csv_path)

            # Leer CSV
            encoding = config.get('encoding', 'utf-8')
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                headers = list(reader.fieldnames)

                # Contar filas y obtener preview
                rows = list(reader)
                total_rows = len(rows)
                preview_data = rows[:10] if rows else []

                # Detectar rango de fechas
                date_range = self._detect_date_range(rows, config)

                # Detectar vehículos (si el CSV tiene identificadores)
                vehicles_detected = self._detect_vehicles(rows, config)

                # Generar warnings
                warnings = self._generate_warnings(headers, config)

            return {
                'source_detected': source_type,
                'source_name': config['name'],
                'total_rows': total_rows,
                'columns_found': headers,
                'mappings': config.get('mappings', {}),
                'date_range': date_range,
                'vehicles_detected': vehicles_detected,
                'preview_data': [dict(row) for row in preview_data],
                'warnings': warnings,
                'file_hash': file_hash,
                'encoding': encoding
            }

        except Exception as e:
            print(f"[CSV-IMPORTER] Error analizando CSV: {e}")
            return {
                'error': str(e),
                'source_detected': 'unknown'
            }

    def import_csv(self, csv_path: str, vehicle_id: int,
                   source_type: str, column_mappings: Dict,
                   create_trips: bool = True, trip_gap_minutes: int = 30,
                   skip_invalid_rows: bool = True) -> Dict:
        """
        Importa datos del CSV a la base de datos

        Args:
            csv_path: Ruta al archivo CSV
            vehicle_id: ID del vehículo destino
            source_type: Tipo de fuente
            column_mappings: Mapeo de columnas personalizado
            create_trips: Si True, divide en viajes automáticamente
            trip_gap_minutes: Minutos de inactividad para nuevo viaje
            skip_invalid_rows: Si True, omite filas inválidas

        Returns:
            Dict con resultado de la importación
        """
        if not self.db:
            return {'success': False, 'error': 'No database manager available'}

        try:
            config = self.SUPPORTED_SOURCES.get(source_type, self.SUPPORTED_SOURCES['generic'])
            encoding = config.get('encoding', 'utf-8')

            # Leer CSV
            with open(csv_path, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Limpiar y validar datos
            cleaned_data = []
            errors = []

            for idx, row in enumerate(rows):
                try:
                    cleaned_row = self._clean_row(row, column_mappings, config)
                    cleaned_data.append(cleaned_row)
                except ValidationError as e:
                    if not skip_invalid_rows:
                        raise
                    errors.append(f"Fila {idx + 2}: {str(e)}")
                except Exception as e:
                    if not skip_invalid_rows:
                        raise
                    errors.append(f"Fila {idx + 2}: Error desconocido - {str(e)}")

            # Dividir en viajes si se solicitó
            trips_created = 0
            rows_imported = 0

            if create_trips:
                trips = self._split_into_trips(cleaned_data, trip_gap_minutes)

                for trip_data in trips:
                    # Crear viaje en BD
                    trip_id = self.db.start_trip(vehicle_id)

                    # Guardar datos del viaje
                    success = self.db.save_obd_data_batch(trip_id, trip_data)

                    if success:
                        # Calcular estadísticas del viaje
                        stats = self._calculate_trip_stats(trip_data)
                        self.db.end_trip(trip_id, stats)

                        trips_created += 1
                        rows_imported += len(trip_data)
            else:
                # Importar todo como un solo viaje
                trip_id = self.db.start_trip(vehicle_id)
                success = self.db.save_obd_data_batch(trip_id, cleaned_data)

                if success:
                    stats = self._calculate_trip_stats(cleaned_data)
                    self.db.end_trip(trip_id, stats)

                    trips_created = 1
                    rows_imported = len(cleaned_data)

            # Registrar importación
            file_hash = self._calculate_file_hash(csv_path)
            import_id = self._register_import(
                vehicle_id, source_type, csv_path, file_hash,
                len(rows), rows_imported, len(errors), trips_created
            )

            return {
                'success': True,
                'vehicle_id': vehicle_id,
                'trips_created': trips_created,
                'rows_imported': rows_imported,
                'rows_skipped': len(errors),
                'errors': errors,
                'import_id': import_id
            }

        except Exception as e:
            print(f"[CSV-IMPORTER] Error importando: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _clean_row(self, row: Dict, mappings: Dict, config: Dict) -> Dict:
        """
        Limpia y valida una fila de datos

        Args:
            row: Fila original del CSV
            mappings: Mapeo de columnas
            config: Configuración de la fuente

        Returns:
            Dict con datos limpios y validados
        """
        cleaned = {}

        # Timestamp
        timestamp_col = mappings.get('timestamp')
        if timestamp_col and timestamp_col in row:
            timestamp = self._parse_datetime(
                row[timestamp_col],
                config.get('timestamp_format')
            )
            if not timestamp:
                raise ValidationError("Fecha inválida")
            cleaned['timestamp'] = timestamp.isoformat()
        else:
            raise ValidationError("Timestamp faltante")

        # RPM: 0-8000 rpm
        rpm_col = mappings.get('rpm')
        if rpm_col and rpm_col in row:
            rpm = self._parse_float(row[rpm_col])
            if rpm is not None and (rpm < 0 or rpm > 8000):
                raise ValidationError(f"RPM fuera de rango: {rpm}")
            cleaned['rpm'] = rpm

        # Speed: 0-300 km/h
        speed_col = mappings.get('speed')
        if speed_col and speed_col in row:
            speed = self._parse_float(row[speed_col])
            if speed is not None and (speed < 0 or speed > 300):
                raise ValidationError(f"Velocidad fuera de rango: {speed}")
            cleaned['speed'] = speed

        # Coolant temp: -40 a 150°C
        coolant_col = mappings.get('coolant_temp')
        if coolant_col and coolant_col in row:
            coolant = self._parse_float(row[coolant_col])
            if coolant is not None and (coolant < -40 or coolant > 150):
                raise ValidationError(f"Temperatura fuera de rango: {coolant}")
            cleaned['coolant_temp'] = coolant

        # Intake temp: -40 a 100°C
        intake_col = mappings.get('intake_temp')
        if intake_col and intake_col in row:
            intake = self._parse_float(row[intake_col])
            if intake is not None and (intake < -40 or intake > 100):
                raise ValidationError(f"Temp. admisión fuera de rango: {intake}")
            cleaned['intake_temp'] = intake

        # MAF: 0-200 g/s
        maf_col = mappings.get('maf')
        if maf_col and maf_col in row:
            maf = self._parse_float(row[maf_col])
            if maf is not None and (maf < 0 or maf > 200):
                raise ValidationError(f"MAF fuera de rango: {maf}")
            cleaned['maf'] = maf

        # Engine load: 0-100%
        load_col = mappings.get('engine_load')
        if load_col and load_col in row:
            load = self._parse_float(row[load_col])
            if load is not None and (load < 0 or load > 100):
                raise ValidationError(f"Carga motor fuera de rango: {load}")
            cleaned['engine_load'] = load

        # Throttle position: 0-100%
        throttle_col = mappings.get('throttle_pos')
        if throttle_col and throttle_col in row:
            throttle = self._parse_float(row[throttle_col])
            if throttle is not None and (throttle < 0 or throttle > 100):
                raise ValidationError(f"Posición acelerador fuera de rango: {throttle}")
            cleaned['throttle_pos'] = throttle

        # Fuel pressure
        fuel_col = mappings.get('fuel_pressure')
        if fuel_col and fuel_col in row:
            fuel = self._parse_float(row[fuel_col])
            cleaned['fuel_pressure'] = fuel

        # GPS coordinates
        lat_col = mappings.get('latitude')
        lon_col = mappings.get('longitude')

        if lat_col and lat_col in row:
            lat = self._parse_float(row[lat_col])
            if lat is not None and (lat < -90 or lat > 90):
                raise ValidationError(f"Latitud inválida: {lat}")
            cleaned['latitude'] = lat

        if lon_col and lon_col in row:
            lon = self._parse_float(row[lon_col])
            if lon is not None and (lon < -180 or lon > 180):
                raise ValidationError(f"Longitud inválida: {lon}")
            cleaned['longitude'] = lon

        return cleaned

    def _split_into_trips(self, data_rows: List[Dict], gap_minutes: int = 30) -> List[List[Dict]]:
        """
        Divide datos en viajes separados según gaps de tiempo

        Args:
            data_rows: Lista de filas de datos
            gap_minutes: Minutos de inactividad para considerar nuevo viaje

        Returns:
            Lista de listas (cada sublista es un viaje)
        """
        if not data_rows:
            return []

        # Ordenar por timestamp
        sorted_data = sorted(data_rows, key=lambda x: x['timestamp'])

        trips = []
        current_trip = []
        last_timestamp = None

        for row in sorted_data:
            timestamp = datetime.fromisoformat(row['timestamp'])

            if last_timestamp:
                gap = (timestamp - last_timestamp).total_seconds() / 60

                if gap > gap_minutes:
                    # Nuevo viaje
                    if current_trip:
                        trips.append(current_trip)
                    current_trip = [row]
                else:
                    current_trip.append(row)
            else:
                current_trip.append(row)

            last_timestamp = timestamp

        # Agregar último viaje
        if current_trip:
            trips.append(current_trip)

        print(f"[CSV-IMPORTER] {len(sorted_data)} filas divididas en {len(trips)} viajes")
        return trips

    def _calculate_trip_stats(self, trip_data: List[Dict]) -> Dict:
        """
        Calcula estadísticas de un viaje

        Args:
            trip_data: Datos del viaje

        Returns:
            Dict con estadísticas
        """
        if not trip_data:
            return {}

        # Calcular distancia total (si hay coordenadas GPS)
        distance_km = 0.0
        speeds = []

        for i in range(len(trip_data)):
            if trip_data[i].get('speed'):
                speeds.append(trip_data[i]['speed'])

            if i > 0:
                lat1 = trip_data[i-1].get('latitude')
                lon1 = trip_data[i-1].get('longitude')
                lat2 = trip_data[i].get('latitude')
                lon2 = trip_data[i].get('longitude')

                if all([lat1, lon1, lat2, lon2]):
                    distance_km += self._haversine_distance(lat1, lon1, lat2, lon2)

        # Calcular duración
        start_time = datetime.fromisoformat(trip_data[0]['timestamp'])
        end_time = datetime.fromisoformat(trip_data[-1]['timestamp'])
        duration_seconds = (end_time - start_time).total_seconds()

        return {
            'distance_km': round(distance_km, 2),
            'duration_seconds': int(duration_seconds),
            'avg_speed': round(sum(speeds) / len(speeds), 1) if speeds else 0,
            'max_speed': round(max(speeds), 1) if speeds else 0
        }

    # === FUNCIONES AUXILIARES ===

    def _parse_datetime(self, value: str, format_str: Optional[str] = None) -> Optional[datetime]:
        """Parsea fecha con formato específico o intentando múltiples formatos"""
        if not value or value.strip() == '':
            return None

        formats_to_try = [
            format_str,
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%d/%m/%Y %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%H:%M:%S.%f',
            '%H:%M:%S'
        ]

        for fmt in formats_to_try:
            if not fmt:
                continue
            try:
                return datetime.strptime(value.strip(), fmt)
            except:
                continue

        return None

    def _parse_float(self, value: str) -> Optional[float]:
        """Parsea valor float con manejo de errores"""
        if not value or value.strip() == '':
            return None

        try:
            # Limpiar valor (remover espacios, comas, etc.)
            cleaned = value.strip().replace(',', '.')
            return float(cleaned)
        except:
            return None

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia entre dos puntos GPS usando fórmula Haversine"""
        from math import radians, sin, cos, sqrt, atan2

        R = 6371  # Radio de la Tierra en km

        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calcula hash MD5 del archivo"""
        hash_md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _detect_date_range(self, rows: List[Dict], config: Dict) -> Dict:
        """Detecta rango de fechas en el CSV"""
        if not rows:
            return {'start': None, 'end': None}

        timestamp_col = config['mappings'].get('timestamp')
        if not timestamp_col:
            return {'start': None, 'end': None}

        dates = []
        for row in rows:
            if timestamp_col in row:
                dt = self._parse_datetime(row[timestamp_col], config.get('timestamp_format'))
                if dt:
                    dates.append(dt)

        if dates:
            return {
                'start': min(dates).strftime('%Y-%m-%d'),
                'end': max(dates).strftime('%Y-%m-%d')
            }

        return {'start': None, 'end': None}

    def _detect_vehicles(self, rows: List[Dict], config: Dict) -> List[Dict]:
        """Detecta vehículos en el CSV (si tiene identificadores)"""
        # Por ahora retorna vacío, se puede expandir en el futuro
        return []

    def _generate_warnings(self, headers: List[str], config: Dict) -> List[str]:
        """Genera warnings sobre columnas faltantes"""
        warnings = []

        critical_fields = ['timestamp', 'rpm', 'speed']
        mappings = config.get('mappings', {})

        for field in critical_fields:
            col_name = mappings.get(field)
            if col_name and col_name not in headers:
                warnings.append(f"Columna crítica '{col_name}' no encontrada")

        return warnings

    def _register_import(self, vehicle_id: int, source_type: str, filename: str,
                         file_hash: str, total_rows: int, rows_imported: int,
                         rows_skipped: int, trips_created: int) -> Optional[int]:
        """Registra la importación en la base de datos"""
        if not self.db:
            return None

        try:
            cursor = self.db._get_connection().cursor()
            cursor.execute('''
                INSERT INTO imports (
                    vehicle_id, source_type, filename, file_hash,
                    rows_total, rows_imported, rows_skipped, trips_created,
                    import_date, can_rollback
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                vehicle_id, source_type, filename, file_hash,
                total_rows, rows_imported, rows_skipped, trips_created,
                datetime.now().isoformat(), 1
            ))

            import_id = cursor.lastrowid
            self.db._get_connection().commit()

            print(f"[CSV-IMPORTER] ✓ Importación registrada (ID: {import_id})")
            return import_id

        except Exception as e:
            print(f"[CSV-IMPORTER] Error registrando importación: {e}")
            return None


class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    pass
