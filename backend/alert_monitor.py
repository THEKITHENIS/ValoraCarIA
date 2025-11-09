# =============================================================================
# SENTINEL PRO - ALERT MONITORING ENGINE
# Motor de monitoreo y evaluación de reglas de alertas en tiempo real
# =============================================================================

import operator
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from database import DatabaseManager

class AlertMonitor:
    """Motor de monitoreo de alertas para SENTINEL PRO"""

    # Operadores de comparación soportados
    OPERATORS = {
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '==': operator.eq,
        '!=': operator.ne
    }

    # Parámetros monitorizables y sus nombres legibles
    PARAMETERS = {
        'rpm': 'RPM del Motor',
        'speed': 'Velocidad',
        'coolant_temp': 'Temperatura del Refrigerante',
        'intake_temp': 'Temperatura de Admisión',
        'maf': 'Flujo de Aire (MAF)',
        'engine_load': 'Carga del Motor',
        'throttle_pos': 'Posición del Acelerador',
        'fuel_pressure': 'Presión de Combustible'
    }

    # Umbrales recomendados por defecto
    DEFAULT_THRESHOLDS = {
        'rpm': {
            'max': 6500,
            'warning': 5500,
            'critical': 7000
        },
        'speed': {
            'max': 200,
            'warning': 180,
            'critical': 220
        },
        'coolant_temp': {
            'max': 105,
            'warning': 95,
            'critical': 110
        },
        'intake_temp': {
            'max': 60,
            'warning': 50,
            'critical': 70
        },
        'engine_load': {
            'max': 95,
            'warning': 85,
            'critical': 98
        },
        'throttle_pos': {
            'max': 100,
            'warning': 90
        },
        'fuel_pressure': {
            'min': 200,
            'max': 600,
            'warning_low': 250,
            'warning_high': 550
        }
    }

    def __init__(self, db: DatabaseManager):
        """
        Inicializa el monitor de alertas

        Args:
            db: Instancia del gestor de base de datos
        """
        self.db = db
        self._alert_cache = {}  # Cache para evitar alertas duplicadas
        self._cache_timeout = 300  # 5 minutos

    def evaluate_data_point(self, vehicle_id: int, data_point: Dict,
                           trip_id: int = None) -> List[Dict]:
        """
        Evalúa un punto de datos contra todas las reglas activas

        Args:
            vehicle_id: ID del vehículo
            data_point: Punto de datos OBD
            trip_id: ID del viaje (opcional)

        Returns:
            Lista de alertas generadas
        """
        # Obtener reglas activas para este vehículo
        rules = self.db.get_alert_rules(vehicle_id=vehicle_id, enabled_only=True)

        if not rules:
            return []

        alerts_generated = []

        for rule in rules:
            parameter = rule['parameter']

            # Verificar que el parámetro existe en el punto de datos
            if parameter not in data_point or data_point[parameter] is None:
                continue

            value = data_point[parameter]

            # Evaluar la condición
            if self._evaluate_condition(value, rule['condition'], rule['threshold']):
                # Verificar si ya generamos una alerta similar recientemente
                if not self._is_duplicate_alert(vehicle_id, rule['id'], value):
                    # Crear la alerta
                    alert = self._create_alert_from_rule(
                        vehicle_id, rule, value, trip_id
                    )
                    alerts_generated.append(alert)

                    # Actualizar cache
                    self._update_alert_cache(vehicle_id, rule['id'], value)

        return alerts_generated

    def _evaluate_condition(self, value: float, condition: str,
                          threshold: float) -> bool:
        """
        Evalúa una condición

        Args:
            value: Valor actual
            condition: Operador de comparación
            threshold: Valor umbral

        Returns:
            True si se cumple la condición
        """
        if condition not in self.OPERATORS:
            print(f"[ALERT] ⚠️  Operador desconocido: {condition}")
            return False

        try:
            return self.OPERATORS[condition](value, threshold)
        except Exception as e:
            print(f"[ALERT] ✗ Error evaluando condición: {e}")
            return False

    def _create_alert_from_rule(self, vehicle_id: int, rule: Dict,
                               value: float, trip_id: int = None) -> Dict:
        """
        Crea una alerta basada en una regla

        Args:
            vehicle_id: ID del vehículo
            rule: Regla que se disparó
            value: Valor que disparó la alerta
            trip_id: ID del viaje

        Returns:
            Diccionario con la alerta creada
        """
        # Generar mensaje
        if rule['message_template']:
            message = rule['message_template'].format(
                value=value,
                threshold=rule['threshold'],
                parameter=self.PARAMETERS.get(rule['parameter'], rule['parameter'])
            )
        else:
            message = (
                f"{self.PARAMETERS.get(rule['parameter'], rule['parameter'])} "
                f"alcanzó {value} (umbral: {rule['threshold']})"
            )

        # Crear alerta en la base de datos
        alert_id = self.db.create_alert(
            vehicle_id=vehicle_id,
            alert_type=rule['parameter'],
            severity=rule['severity'],
            message=message,
            value=value,
            threshold=rule['threshold'],
            trip_id=trip_id
        )

        return {
            'id': alert_id,
            'vehicle_id': vehicle_id,
            'trip_id': trip_id,
            'alert_type': rule['parameter'],
            'severity': rule['severity'],
            'message': message,
            'value': value,
            'threshold': rule['threshold'],
            'notify_sound': rule['notify_sound'],
            'notify_email': rule['notify_email'],
            'timestamp': datetime.now().isoformat()
        }

    def _is_duplicate_alert(self, vehicle_id: int, rule_id: int,
                           value: float) -> bool:
        """
        Verifica si una alerta es duplicada (generada recientemente)

        Args:
            vehicle_id: ID del vehículo
            rule_id: ID de la regla
            value: Valor actual

        Returns:
            True si es duplicada
        """
        cache_key = f"{vehicle_id}_{rule_id}"

        if cache_key not in self._alert_cache:
            return False

        cached_data = self._alert_cache[cache_key]
        time_diff = (datetime.now() - cached_data['timestamp']).total_seconds()

        # Si han pasado más de cache_timeout segundos, no es duplicada
        if time_diff > self._cache_timeout:
            return False

        # Si el valor cambió significativamente (>10%), no es duplicada
        value_diff_percent = abs(value - cached_data['value']) / cached_data['value'] * 100
        if value_diff_percent > 10:
            return False

        return True

    def _update_alert_cache(self, vehicle_id: int, rule_id: int, value: float):
        """
        Actualiza el cache de alertas

        Args:
            vehicle_id: ID del vehículo
            rule_id: ID de la regla
            value: Valor que disparó la alerta
        """
        cache_key = f"{vehicle_id}_{rule_id}"
        self._alert_cache[cache_key] = {
            'value': value,
            'timestamp': datetime.now()
        }

    def clean_cache(self):
        """Limpia entradas antiguas del cache"""
        current_time = datetime.now()
        keys_to_remove = []

        for key, data in self._alert_cache.items():
            time_diff = (current_time - data['timestamp']).total_seconds()
            if time_diff > self._cache_timeout:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._alert_cache[key]

    # =========================================================================
    # REGLAS PREDEFINIDAS
    # =========================================================================

    @classmethod
    def get_default_rules(cls, vehicle_id: int) -> List[Dict]:
        """
        Obtiene reglas predefinidas recomendadas

        Args:
            vehicle_id: ID del vehículo

        Returns:
            Lista de reglas predefinidas
        """
        return [
            {
                'vehicle_id': vehicle_id,
                'name': 'RPM Crítico',
                'parameter': 'rpm',
                'condition': '>',
                'threshold': cls.DEFAULT_THRESHOLDS['rpm']['critical'],
                'severity': 'critical',
                'message_template': '⚠️ RPM CRÍTICO: {value} RPM (máximo recomendado: {threshold})',
                'notify_email': False,
                'notify_sound': True
            },
            {
                'vehicle_id': vehicle_id,
                'name': 'RPM Alto',
                'parameter': 'rpm',
                'condition': '>',
                'threshold': cls.DEFAULT_THRESHOLDS['rpm']['warning'],
                'severity': 'high',
                'message_template': '⚠️ RPM elevado: {value} RPM',
                'notify_email': False,
                'notify_sound': True
            },
            {
                'vehicle_id': vehicle_id,
                'name': 'Temperatura del Refrigerante Crítica',
                'parameter': 'coolant_temp',
                'condition': '>',
                'threshold': cls.DEFAULT_THRESHOLDS['coolant_temp']['critical'],
                'severity': 'critical',
                'message_template': '🔥 TEMPERATURA CRÍTICA: {value}°C (máximo: {threshold}°C)',
                'notify_email': True,
                'notify_sound': True
            },
            {
                'vehicle_id': vehicle_id,
                'name': 'Temperatura del Refrigerante Alta',
                'parameter': 'coolant_temp',
                'condition': '>',
                'threshold': cls.DEFAULT_THRESHOLDS['coolant_temp']['warning'],
                'severity': 'high',
                'message_template': '⚠️ Temperatura elevada: {value}°C',
                'notify_email': False,
                'notify_sound': True
            },
            {
                'vehicle_id': vehicle_id,
                'name': 'Velocidad Excesiva',
                'parameter': 'speed',
                'condition': '>',
                'threshold': cls.DEFAULT_THRESHOLDS['speed']['warning'],
                'severity': 'medium',
                'message_template': '⚠️ Velocidad alta: {value} km/h',
                'notify_email': False,
                'notify_sound': False
            },
            {
                'vehicle_id': vehicle_id,
                'name': 'Carga del Motor Alta',
                'parameter': 'engine_load',
                'condition': '>',
                'threshold': cls.DEFAULT_THRESHOLDS['engine_load']['warning'],
                'severity': 'medium',
                'message_template': '⚠️ Carga del motor elevada: {value}%',
                'notify_email': False,
                'notify_sound': False
            },
            {
                'vehicle_id': vehicle_id,
                'name': 'Temperatura de Admisión Alta',
                'parameter': 'intake_temp',
                'condition': '>',
                'threshold': cls.DEFAULT_THRESHOLDS['intake_temp']['warning'],
                'severity': 'low',
                'message_template': '⚠️ Temperatura de admisión elevada: {value}°C',
                'notify_email': False,
                'notify_sound': False
            }
        ]

    def install_default_rules(self, vehicle_id: int) -> int:
        """
        Instala las reglas predefinidas para un vehículo

        Args:
            vehicle_id: ID del vehículo

        Returns:
            Número de reglas instaladas
        """
        default_rules = self.get_default_rules(vehicle_id)
        count = 0

        for rule_data in default_rules:
            try:
                self.db.create_alert_rule(**rule_data)
                count += 1
            except Exception as e:
                print(f"[ALERT] ✗ Error instalando regla: {e}")

        print(f"[ALERT] ✓ {count} reglas predefinidas instaladas para vehículo {vehicle_id}")
        return count

    # =========================================================================
    # ESTADÍSTICAS DE ALERTAS
    # =========================================================================

    def get_alert_stats(self, vehicle_id: int = None,
                       days: int = 7) -> Dict:
        """
        Obtiene estadísticas de alertas

        Args:
            vehicle_id: ID del vehículo (opcional)
            days: Número de días hacia atrás

        Returns:
            Diccionario con estadísticas
        """
        if vehicle_id:
            alerts = self.db.get_vehicle_alerts(vehicle_id, limit=1000)
        else:
            alerts = self.db.get_all_alerts(limit=1000)

        # Filtrar por fecha
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_alerts = [
            a for a in alerts
            if datetime.fromisoformat(a['timestamp']) > cutoff_date
        ]

        # Contar por severidad
        severity_counts = {
            'low': 0,
            'medium': 0,
            'high': 0,
            'critical': 0
        }

        for alert in recent_alerts:
            severity = alert['severity']
            if severity in severity_counts:
                severity_counts[severity] += 1

        # Contar por tipo
        type_counts = {}
        for alert in recent_alerts:
            alert_type = alert['alert_type']
            type_counts[alert_type] = type_counts.get(alert_type, 0) + 1

        # Calcular tasa de reconocimiento
        acknowledged_count = sum(1 for a in recent_alerts if a['acknowledged'])
        ack_rate = (acknowledged_count / len(recent_alerts) * 100) if recent_alerts else 0

        return {
            'total_alerts': len(recent_alerts),
            'unacknowledged': len(recent_alerts) - acknowledged_count,
            'by_severity': severity_counts,
            'by_type': type_counts,
            'acknowledgement_rate': round(ack_rate, 2),
            'period_days': days
        }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SENTINEL PRO - ALERT MONITOR TEST")
    print("=" * 70)

    from database import DatabaseManager

    # Inicializar
    db = DatabaseManager()
    monitor = AlertMonitor(db)

    print("\n[TEST] Monitor de alertas inicializado")

    # Test: Crear vehículo de prueba
    try:
        vehicle_id = db.create_vehicle(
            vin="ALERT_TEST_001",
            brand="Test",
            model="Alert Test",
            year=2020,
            fuel_type="gasolina",
            transmission="manual"
        )
        print(f"[TEST] ✓ Vehículo de prueba creado: ID {vehicle_id}")

        # Test: Instalar reglas predefinidas
        count = monitor.install_default_rules(vehicle_id)
        print(f"[TEST] ✓ {count} reglas predefinidas instaladas")

        # Test: Simular datos que disparan alertas
        test_data = {
            'rpm': 6000,  # Dispara alerta de RPM alto
            'coolant_temp': 96,  # Dispara alerta de temperatura
            'speed': 185,  # Dispara alerta de velocidad
            'engine_load': 88,
            'throttle_pos': 85
        }

        print("\n[TEST] Evaluando punto de datos de prueba:")
        print(f"  - RPM: {test_data['rpm']}")
        print(f"  - Temperatura: {test_data['coolant_temp']}°C")
        print(f"  - Velocidad: {test_data['speed']} km/h")

        alerts = monitor.evaluate_data_point(vehicle_id, test_data)
        print(f"\n[TEST] ✓ {len(alerts)} alertas generadas:")

        for alert in alerts:
            print(f"  - [{alert['severity'].upper()}] {alert['message']}")

        # Test: Estadísticas
        stats = monitor.get_alert_stats(vehicle_id)
        print(f"\n[TEST] ✓ Estadísticas:")
        print(f"  - Total alertas: {stats['total_alerts']}")
        print(f"  - No reconocidas: {stats['unacknowledged']}")
        print(f"  - Por severidad: {stats['by_severity']}")

    except Exception as e:
        print(f"[TEST] ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n✓ Tests completados")
