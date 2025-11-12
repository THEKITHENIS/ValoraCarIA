"""
OBDb Parser for SENTINEL PRO
=============================

Parser for Open Board Diagnostics Database (OBDb) JSON files.
Provides access to extended OBD-II commands beyond the basic 21 PIDs.

Author: SENTINEL PRO Team
Version: 1.0
"""

import json
import os
from typing import Dict, List, Optional, Any


class OBDbParser:
    """
    Parser for OBDb JSON database files.

    Provides methods to:
    - Load OBDb command definitions
    - Filter commands by frequency/priority
    - Extract signal definitions
    - Map OBDb commands to python-obd format
    """

    def __init__(self, json_file_path: str = "default.json"):
        """
        Initialize the OBDb parser.

        Args:
            json_file_path: Path to OBDb JSON file
        """
        self.json_file_path = json_file_path
        self.commands = []
        self.command_map = {}

        if os.path.exists(json_file_path):
            self.load_database(json_file_path)
        else:
            print(f"[OBDb Parser] ⚠️  Database file not found: {json_file_path}")
            print(f"[OBDb Parser] ℹ️  Parser initialized without commands")

    def load_database(self, json_file_path: str) -> bool:
        """
        Load OBDb JSON database.

        Args:
            json_file_path: Path to JSON file

        Returns:
            True if loaded successfully
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract commands from JSON
            if isinstance(data, dict) and 'commands' in data:
                self.commands = data['commands']
            elif isinstance(data, list):
                self.commands = data
            else:
                print(f"[OBDb Parser] ⚠️  Unexpected JSON format")
                return False

            # Build command map for fast lookup
            for cmd in self.commands:
                cmd_str = self.get_command_string(cmd)
                if cmd_str:
                    self.command_map[cmd_str] = cmd

            print(f"[OBDb Parser] ✓ Loaded {len(self.commands)} commands from {json_file_path}")
            return True

        except Exception as e:
            print(f"[OBDb Parser] ✗ Error loading database: {e}")
            return False

    def get_command_string(self, command: Dict) -> str:
        """
        Extract command string from OBDb command definition.

        Args:
            command: OBDb command dict

        Returns:
            Command string (e.g., "01 0C" for RPM)
        """
        try:
            # OBDb format: mode + PID
            mode = command.get('mode', '')
            pid = command.get('pid', '')

            if mode and pid:
                return f"{mode} {pid}".upper()

            # Alternative: full command string
            if 'command' in command:
                return command['command'].upper()

            return ""

        except Exception:
            return ""

    def get_fast_commands(self, max_freq: float = 5.0) -> List[Dict]:
        """
        Get commands suitable for high-frequency polling.

        Args:
            max_freq: Maximum frequency in Hz (default 5 Hz = every 200ms)

        Returns:
            List of fast commands
        """
        fast_commands = []

        for cmd in self.commands:
            # Check if command has frequency info
            freq = cmd.get('frequency', 0)
            priority = cmd.get('priority', 'low')

            # Include if:
            # - Frequency is high enough
            # - Priority is high
            # - Command is marked as "fast"
            if (freq >= max_freq or
                priority in ['high', 'critical'] or
                cmd.get('fast', False)):
                fast_commands.append(cmd)

        return fast_commands

    def get_commands_by_category(self, category: str) -> List[Dict]:
        """
        Get commands by category.

        Categories:
        - fuel: Fuel system
        - o2: Oxygen sensors
        - emissions: Emissions system
        - exhaust: Exhaust system
        - temperature: Temperature sensors
        - pressure: Pressure sensors
        - diagnostics: Diagnostic codes

        Args:
            category: Category name

        Returns:
            List of commands in category
        """
        category_commands = []
        category_lower = category.lower()

        for cmd in self.commands:
            # Check command path/category
            path = cmd.get('path', '').lower()
            cmd_category = cmd.get('category', '').lower()

            if category_lower in path or category_lower in cmd_category:
                category_commands.append(cmd)

        return category_commands

    def get_signal_info(self, command: Dict, signal_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific signal.

        Args:
            command: OBDb command dict
            signal_id: Signal identifier

        Returns:
            Signal info dict or None
        """
        signals = command.get('signals', [])

        for signal in signals:
            if signal.get('id') == signal_id or signal.get('name') == signal_id:
                return signal

        return None

    def get_all_signals(self) -> List[Dict]:
        """
        Extract all signals from all commands.

        Returns:
            List of all signals with metadata
        """
        all_signals = []

        for cmd in self.commands:
            cmd_str = self.get_command_string(cmd)
            signals = cmd.get('signals', [])

            for signal in signals:
                signal_info = {
                    'command': cmd_str,
                    'signal_id': signal.get('id', ''),
                    'signal_name': signal.get('name', ''),
                    'path': signal.get('path', ''),
                    'unit': signal.get('unit', ''),
                    'min': signal.get('min', None),
                    'max': signal.get('max', None),
                    'description': signal.get('description', '')
                }
                all_signals.append(signal_info)

        return all_signals

    def get_command_by_string(self, cmd_string: str) -> Optional[Dict]:
        """
        Get command definition by command string.

        Args:
            cmd_string: Command string (e.g., "01 0C")

        Returns:
            Command dict or None
        """
        return self.command_map.get(cmd_string.upper())

    def decode_value(self, signal: Dict, raw_bytes: bytes) -> Optional[float]:
        """
        Decode raw bytes to physical value using signal definition.

        Args:
            signal: Signal definition from OBDb
            raw_bytes: Raw bytes from ECU

        Returns:
            Decoded value or None
        """
        try:
            # Get decoding parameters
            offset = signal.get('offset', 0)
            scale = signal.get('scale', 1.0)
            byte_order = signal.get('byte_order', 'big')

            # Convert bytes to int
            if byte_order == 'big':
                raw_value = int.from_bytes(raw_bytes, byteorder='big')
            else:
                raw_value = int.from_bytes(raw_bytes, byteorder='little')

            # Apply formula: physical_value = (raw_value * scale) + offset
            physical_value = (raw_value * scale) + offset

            return physical_value

        except Exception as e:
            print(f"[OBDb Parser] Error decoding value: {e}")
            return None

    def get_supported_pids(self, profile_data: Dict) -> List[str]:
        """
        Extract list of supported PIDs from vehicle profile.

        Args:
            profile_data: Vehicle profile dict

        Returns:
            List of supported command strings
        """
        return profile_data.get('supported_commands', [])

    def get_statistics(self) -> Dict:
        """
        Get statistics about loaded commands.

        Returns:
            Dict with statistics
        """
        categories = {}
        total_signals = 0

        for cmd in self.commands:
            # Count by category
            category = cmd.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1

            # Count signals
            total_signals += len(cmd.get('signals', []))

        return {
            'total_commands': len(self.commands),
            'total_signals': total_signals,
            'categories': categories,
            'avg_signals_per_command': total_signals / len(self.commands) if self.commands else 0
        }

    def __repr__(self) -> str:
        return f"<OBDbParser: {len(self.commands)} commands loaded>"


# === UTILITY FUNCTIONS ===

def create_minimal_obdb_json():
    """
    Create a minimal OBDb JSON file for testing.

    This is used when default.json is not available.
    Contains only the most common extended PIDs.
    """
    minimal_db = {
        "version": "1.0",
        "description": "Minimal OBDb database for SENTINEL PRO",
        "commands": [
            {
                "mode": "01",
                "pid": "06",
                "command": "01 06",
                "category": "fuel",
                "frequency": 1.0,
                "signals": [
                    {
                        "id": "SHORT_FUEL_TRIM_1",
                        "name": "Short Term Fuel Trim - Bank 1",
                        "path": "Fuel.ShortTrim.Bank1",
                        "unit": "%",
                        "min": -100,
                        "max": 99.2,
                        "scale": 0.78125,
                        "offset": -100
                    }
                ]
            },
            {
                "mode": "01",
                "pid": "07",
                "command": "01 07",
                "category": "fuel",
                "frequency": 1.0,
                "signals": [
                    {
                        "id": "LONG_FUEL_TRIM_1",
                        "name": "Long Term Fuel Trim - Bank 1",
                        "path": "Fuel.LongTrim.Bank1",
                        "unit": "%",
                        "min": -100,
                        "max": 99.2,
                        "scale": 0.78125,
                        "offset": -100
                    }
                ]
            },
            {
                "mode": "01",
                "pid": "14",
                "command": "01 14",
                "category": "o2",
                "frequency": 2.0,
                "signals": [
                    {
                        "id": "O2_B1S1",
                        "name": "O2 Sensor Voltage - Bank 1 Sensor 1",
                        "path": "O2.Bank1.Sensor1",
                        "unit": "V",
                        "min": 0,
                        "max": 1.275,
                        "scale": 0.005,
                        "offset": 0
                    }
                ]
            },
            {
                "mode": "01",
                "pid": "2C",
                "command": "01 2C",
                "category": "emissions",
                "frequency": 0.5,
                "signals": [
                    {
                        "id": "COMMANDED_EGR",
                        "name": "Commanded EGR",
                        "path": "Emissions.EGR.Commanded",
                        "unit": "%",
                        "min": 0,
                        "max": 100,
                        "scale": 0.392157,
                        "offset": 0
                    }
                ]
            },
            {
                "mode": "01",
                "pid": "2D",
                "command": "01 2D",
                "category": "emissions",
                "frequency": 0.5,
                "signals": [
                    {
                        "id": "EGR_ERROR",
                        "name": "EGR Error",
                        "path": "Emissions.EGR.Error",
                        "unit": "%",
                        "min": -100,
                        "max": 99.2,
                        "scale": 0.78125,
                        "offset": -100
                    }
                ]
            }
        ]
    }

    with open('obdb_minimal.json', 'w', encoding='utf-8') as f:
        json.dump(minimal_db, f, indent=2)

    print("[OBDb Parser] ✓ Created obdb_minimal.json")


if __name__ == "__main__":
    print("=" * 70)
    print("OBDb Parser Test")
    print("=" * 70)

    # Test with minimal database
    create_minimal_obdb_json()

    parser = OBDbParser("obdb_minimal.json")

    if parser.commands:
        stats = parser.get_statistics()
        print(f"\nStatistics:")
        print(f"  Total commands: {stats['total_commands']}")
        print(f"  Total signals: {stats['total_signals']}")
        print(f"  Categories: {stats['categories']}")

        print(f"\nFast commands (>1 Hz):")
        fast_cmds = parser.get_fast_commands(max_freq=1.0)
        for cmd in fast_cmds:
            print(f"  - {parser.get_command_string(cmd)}: {cmd.get('signals', [{}])[0].get('name', 'N/A')}")

        print(f"\nFuel system commands:")
        fuel_cmds = parser.get_commands_by_category('fuel')
        for cmd in fuel_cmds:
            print(f"  - {parser.get_command_string(cmd)}: {len(cmd.get('signals', []))} signals")

    print("\n" + "=" * 70)
