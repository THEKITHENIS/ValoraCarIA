"""
OBDb Integration for SENTINEL PRO
==================================

Integrates Open Board Diagnostics Database (OBDb) with SENTINEL PRO
to expand from 21 basic PIDs to 113 extended OBD-II commands.

Key Features:
- Non-breaking: Maintains full compatibility with existing 21 PIDs
- Optional: System works in degraded mode if OBDb fails
- Vehicle-specific: Uses per-vehicle profiles
- AI-enhanced: Enriches Gemini prompts with extended signals

Author: SENTINEL PRO Team
Version: 1.0
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from obdb_parser import OBDbParser
    OBDB_PARSER_AVAILABLE = True
except ImportError:
    OBDB_PARSER_AVAILABLE = False
    print("[OBDb Integration] ⚠️  obdb_parser not available")

try:
    import obd
    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False
    print("[OBDb Integration] ⚠️  python-obd not available")


class OBDbIntegration:
    """
    Main integration class for OBDb with SENTINEL PRO.

    Responsibilities:
    - Load vehicle-specific OBDb profiles
    - Query extended OBD-II signals
    - Categorize signals for UI display
    - Enhance AI prompts with extended data
    - Maintain backward compatibility
    """

    def __init__(self, connection=None, vehicle_profile_path: Optional[str] = None):
        """
        Initialize OBDb integration.

        Args:
            connection: python-obd connection object
            vehicle_profile_path: Path to vehicle profile JSON
        """
        self.obd_connection = connection
        self.parser = None
        self.vehicle_profile = {}
        self.extended_signals = {}
        self.last_update = None
        self.enabled = False

        # Try to initialize parser
        if OBDB_PARSER_AVAILABLE:
            try:
                # Try loading full database first
                if os.path.exists("obdb_full.json"):
                    self.parser = OBDbParser("obdb_full.json")
                elif os.path.exists("obdb_minimal.json"):
                    self.parser = OBDbParser("obdb_minimal.json")
                else:
                    # Create minimal database
                    from obdb_parser import create_minimal_obdb_json
                    create_minimal_obdb_json()
                    self.parser = OBDbParser("obdb_minimal.json")

                print(f"[OBDb Integration] ✓ Parser initialized")
            except Exception as e:
                print(f"[OBDb Integration] ✗ Parser initialization failed: {e}")

        # Load vehicle profile if provided
        if vehicle_profile_path:
            self.load_vehicle_profile(vehicle_profile_path)

        # Mark as enabled if we have both parser and connection
        if self.parser and self.obd_connection:
            self.enabled = True
            print(f"[OBDb Integration] ✓ Integration enabled")
        else:
            print(f"[OBDb Integration] ℹ️  Integration disabled (degraded mode)")

    def load_vehicle_profile(self, profile_path: str) -> bool:
        """
        Load vehicle-specific OBDb profile.

        Profile contains:
        - Supported OBDb commands
        - Vehicle metadata (VIN, make, model, year)
        - Scan timestamp
        - Protocol information

        Args:
            profile_path: Path to profile JSON

        Returns:
            True if loaded successfully
        """
        try:
            if not os.path.exists(profile_path):
                print(f"[OBDb Integration] ⚠️  Profile not found: {profile_path}")
                return False

            with open(profile_path, 'r', encoding='utf-8') as f:
                self.vehicle_profile = json.load(f)

            supported_count = len(self.vehicle_profile.get('supported_commands', []))
            print(f"[OBDb Integration] ✓ Profile loaded: {supported_count} commands supported")
            return True

        except Exception as e:
            print(f"[OBDb Integration] ✗ Error loading profile: {e}")
            return False

    def get_extended_signals(self) -> Dict[str, Dict]:
        """
        Query extended OBD-II signals beyond the 21 basic PIDs.

        Signals are categorized into:
        - fuel_system: Fuel trim, pressure, system status
        - o2_sensors: Oxygen sensors (lambda)
        - emissions: EGR, evaporative, catalyst
        - exhaust: Exhaust temperatures
        - dpf: Diesel Particulate Filter (diesel only)
        - battery: Hybrid/EV battery
        - diagnostics: DTCs, MIL, monitor status

        Returns:
            Dict with categorized signals
        """
        if not self.enabled:
            return self._get_empty_signals()

        signals = {
            'fuel_system': {},
            'o2_sensors': {},
            'emissions': {},
            'exhaust': {},
            'dpf': {},
            'battery': {},
            'diagnostics': {}
        }

        try:
            # Get fast commands for real-time monitoring
            fast_commands = self.parser.get_fast_commands(max_freq=1.0)

            for cmd in fast_commands:
                cmd_str = self.parser.get_command_string(cmd)

                # Only query if vehicle supports this command
                if cmd_str not in self.vehicle_profile.get('supported_commands', []):
                    continue

                # Query command
                signal_data = self._query_command(cmd_str)

                if signal_data:
                    # Decode and categorize signals
                    for signal in cmd.get('signals', []):
                        signal_id = signal.get('id', '')
                        path = signal.get('path', '')

                        # Extract category from path
                        category_key = self._get_category_from_path(path)

                        if category_key and signal_id in signal_data:
                            signals[category_key][signal_id] = {
                                'value': signal_data[signal_id],
                                'unit': signal.get('unit', ''),
                                'name': signal.get('name', signal_id),
                                'command': cmd_str
                            }

            self.extended_signals = signals
            self.last_update = datetime.now()

        except Exception as e:
            print(f"[OBDb Integration] Error querying signals: {e}")

        return signals

    def _get_empty_signals(self) -> Dict[str, Dict]:
        """Return empty signal structure."""
        return {
            'fuel_system': {},
            'o2_sensors': {},
            'emissions': {},
            'exhaust': {},
            'dpf': {},
            'battery': {},
            'diagnostics': {}
        }

    def _query_command(self, cmd_str: str) -> Optional[Dict]:
        """
        Query a specific OBD-II command.

        Args:
            cmd_str: Command string (e.g., "01 06")

        Returns:
            Dict of signal values or None
        """
        if not self.obd_connection or not OBD_AVAILABLE:
            return None

        try:
            # Parse command string
            parts = cmd_str.split()
            if len(parts) != 2:
                return None

            mode_str, pid_str = parts

            # Try to find corresponding obd command
            # python-obd uses different naming convention
            obd_cmd = self._find_obd_command(mode_str, pid_str)

            if obd_cmd:
                response = self.obd_connection.query(obd_cmd)
                if response and not response.is_null():
                    return {'value': response.value}

        except Exception as e:
            print(f"[OBDb Integration] Error querying {cmd_str}: {e}")

        return None

    def _find_obd_command(self, mode: str, pid: str):
        """
        Find python-obd command object from mode and PID.

        Args:
            mode: Mode string (e.g., "01")
            pid: PID string (e.g., "06")

        Returns:
            obd.OBDCommand or None
        """
        if not OBD_AVAILABLE:
            return None

        try:
            # python-obd command lookup
            # This is a simplified version - actual implementation
            # would need complete mapping
            mode_int = int(mode, 16)
            pid_int = int(pid, 16)

            # Check if command exists
            for cmd in obd.commands:
                if hasattr(cmd, 'mode') and hasattr(cmd, 'pid'):
                    if cmd.mode == mode_int and cmd.pid == pid_int:
                        return cmd

        except Exception:
            pass

        return None

    def _get_category_from_path(self, path: str) -> Optional[str]:
        """
        Extract category key from OBDb signal path.

        Args:
            path: Signal path (e.g., "Fuel.ShortTrim.Bank1")

        Returns:
            Category key or None
        """
        if not path:
            return None

        path_lower = path.lower()

        # Mapping from path prefixes to category keys
        if 'fuel' in path_lower:
            return 'fuel_system'
        elif 'o2' in path_lower or 'oxygen' in path_lower or 'lambda' in path_lower:
            return 'o2_sensors'
        elif 'egr' in path_lower or 'evap' in path_lower or 'catalyst' in path_lower:
            return 'emissions'
        elif 'exhaust' in path_lower:
            return 'exhaust'
        elif 'dpf' in path_lower or 'particulate' in path_lower:
            return 'dpf'
        elif 'battery' in path_lower or 'hybrid' in path_lower:
            return 'battery'
        elif 'dtc' in path_lower or 'mil' in path_lower or 'monitor' in path_lower:
            return 'diagnostics'

        return None

    def enhance_gemini_prompt(self, base_data: Dict, trip_data: List[Dict] = None) -> str:
        """
        Enhance Gemini AI prompt with extended OBDb signals.

        Takes basic 21-PID data and enriches it with:
        - Fuel trim data (mixture adjustments)
        - O2 sensor readings (air-fuel ratio)
        - Emissions system status
        - Exhaust temperatures
        - DPF status (diesel)
        - Diagnostic codes

        Args:
            base_data: Basic OBD data (21 PIDs)
            trip_data: Optional trip history

        Returns:
            Enhanced prompt string
        """
        if not self.enabled or not self.extended_signals:
            # Return basic prompt if OBDb unavailable
            return self._generate_basic_prompt(base_data, trip_data)

        prompt_parts = []

        # Base information
        prompt_parts.append("=== ANÁLISIS DEL VEHÍCULO ===\n")
        prompt_parts.append(f"Timestamp: {datetime.now().isoformat()}\n")

        # Basic 21 PIDs
        prompt_parts.append("\n--- DATOS BÁSICOS OBD-II ---")
        if base_data:
            for key, value in base_data.items():
                if value is not None:
                    prompt_parts.append(f"{key}: {value}")

        # Extended signals - Fuel System
        if self.extended_signals.get('fuel_system'):
            prompt_parts.append("\n--- SISTEMA DE COMBUSTIBLE ---")
            for signal_id, signal_info in self.extended_signals['fuel_system'].items():
                value = signal_info['value']
                unit = signal_info['unit']
                name = signal_info['name']
                prompt_parts.append(f"{name}: {value} {unit}")

        # Extended signals - O2 Sensors
        if self.extended_signals.get('o2_sensors'):
            prompt_parts.append("\n--- SENSORES DE OXÍGENO (LAMBDA) ---")
            for signal_id, signal_info in self.extended_signals['o2_sensors'].items():
                value = signal_info['value']
                unit = signal_info['unit']
                name = signal_info['name']
                prompt_parts.append(f"{name}: {value} {unit}")

        # Extended signals - Emissions
        if self.extended_signals.get('emissions'):
            prompt_parts.append("\n--- SISTEMA DE EMISIONES ---")
            for signal_id, signal_info in self.extended_signals['emissions'].items():
                value = signal_info['value']
                unit = signal_info['unit']
                name = signal_info['name']
                prompt_parts.append(f"{name}: {value} {unit}")

        # Extended signals - Exhaust
        if self.extended_signals.get('exhaust'):
            prompt_parts.append("\n--- SISTEMA DE ESCAPE ---")
            for signal_id, signal_info in self.extended_signals['exhaust'].items():
                value = signal_info['value']
                unit = signal_info['unit']
                name = signal_info['name']
                prompt_parts.append(f"{name}: {value} {unit}")

        # Extended signals - DPF (diesel only)
        if self.extended_signals.get('dpf'):
            prompt_parts.append("\n--- FILTRO DE PARTÍCULAS DIÉSEL (DPF) ---")
            for signal_id, signal_info in self.extended_signals['dpf'].items():
                value = signal_info['value']
                unit = signal_info['unit']
                name = signal_info['name']
                prompt_parts.append(f"{name}: {value} {unit}")

        # Extended signals - Diagnostics
        if self.extended_signals.get('diagnostics'):
            prompt_parts.append("\n--- DIAGNÓSTICO ---")
            for signal_id, signal_info in self.extended_signals['diagnostics'].items():
                value = signal_info['value']
                unit = signal_info['unit']
                name = signal_info['name']
                prompt_parts.append(f"{name}: {value} {unit}")

        # Trip data if available
        if trip_data:
            prompt_parts.append(f"\n--- HISTORIAL DE VIAJE ---")
            prompt_parts.append(f"Puntos de datos: {len(trip_data)}")

        # Analysis request
        prompt_parts.append("\n=== SOLICITUD DE ANÁLISIS ===")
        prompt_parts.append("Por favor analiza estos datos y proporciona:")
        prompt_parts.append("1. Estado general del vehículo (0-100)")
        prompt_parts.append("2. Componentes en riesgo o con anomalías")
        prompt_parts.append("3. Recomendaciones de mantenimiento prioritarias")
        prompt_parts.append("4. Predicciones de fallos en 6-12 meses")
        prompt_parts.append("5. Diagnóstico específico considerando:")
        prompt_parts.append("   - Fuel trim (ajustes de mezcla)")
        prompt_parts.append("   - Sensores O2 (ratio aire-combustible)")
        prompt_parts.append("   - Sistema de emisiones")
        prompt_parts.append("   - Temperaturas de escape")

        return "\n".join(prompt_parts)

    def _generate_basic_prompt(self, base_data: Dict, trip_data: List[Dict] = None) -> str:
        """
        Generate basic prompt without extended signals.

        Fallback for when OBDb is unavailable.
        """
        prompt_parts = []

        prompt_parts.append("=== ANÁLISIS DEL VEHÍCULO ===")
        prompt_parts.append(f"Timestamp: {datetime.now().isoformat()}\n")
        prompt_parts.append("--- DATOS BÁSICOS OBD-II ---")

        if base_data:
            for key, value in base_data.items():
                if value is not None:
                    prompt_parts.append(f"{key}: {value}")

        if trip_data:
            prompt_parts.append(f"\nPuntos de datos: {len(trip_data)}")

        return "\n".join(prompt_parts)

    def get_status(self) -> Dict:
        """
        Get integration status.

        Returns:
            Status dict with diagnostics
        """
        return {
            'enabled': self.enabled,
            'parser_available': self.parser is not None,
            'connection_available': self.obd_connection is not None,
            'profile_loaded': bool(self.vehicle_profile),
            'supported_commands': len(self.vehicle_profile.get('supported_commands', [])),
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'signal_categories': {
                cat: len(signals)
                for cat, signals in self.extended_signals.items()
            } if self.extended_signals else {}
        }

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<OBDbIntegration: {status}>"


# === UTILITY FUNCTIONS ===

def create_vehicle_profile_template(vehicle_id: int, vin: str = None) -> Dict:
    """
    Create template for vehicle profile.

    Args:
        vehicle_id: Vehicle ID from database
        vin: Vehicle Identification Number

    Returns:
        Profile template dict
    """
    return {
        'vehicle_id': vehicle_id,
        'vin': vin,
        'scan_timestamp': datetime.now().isoformat(),
        'protocol': None,
        'supported_commands': [],
        'metadata': {
            'scanner_version': '1.0',
            'sentinel_pro_version': '10.0'
        }
    }


def save_vehicle_profile(profile: Dict, output_path: str) -> bool:
    """
    Save vehicle profile to JSON file.

    Args:
        profile: Profile dict
        output_path: Output file path

    Returns:
        True if saved successfully
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(profile, f, indent=2)

        print(f"[OBDb Integration] ✓ Profile saved: {output_path}")
        return True

    except Exception as e:
        print(f"[OBDb Integration] ✗ Error saving profile: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("OBDb Integration Test")
    print("=" * 70)

    # Test without connection (degraded mode)
    integration = OBDbIntegration()

    status = integration.get_status()
    print(f"\nIntegration Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    # Test profile template
    print(f"\nCreating profile template...")
    template = create_vehicle_profile_template(vehicle_id=1, vin="WVW1234567890")
    print(f"Template: {template}")

    print("\n" + "=" * 70)
