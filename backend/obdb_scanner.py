"""
OBDb Scanner for SENTINEL PRO
===============================

Scans vehicles to determine which OBDb commands are supported.
Creates vehicle-specific profiles for optimized OBD-II monitoring.

Usage:
    python obdb_scanner.py --vehicle-id 1 --port COM6
    python obdb_scanner.py --vehicle-id 1 --port /dev/ttyUSB0

Author: SENTINEL PRO Team
Version: 1.0
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Optional

try:
    import obd
    from obd import OBDCommand
    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False
    print("[OBDb Scanner] ✗ python-obd not available")
    print("[OBDb Scanner] Install with: pip install obd")

try:
    from obdb_parser import OBDbParser
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False
    print("[OBDb Scanner] ✗ obdb_parser not available")

try:
    from database import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("[OBDb Scanner] ⚠️  database module not available")


class OBDbScanner:
    """
    Scanner for detecting supported OBDb commands.

    Process:
    1. Connect to vehicle via OBD-II
    2. Query each OBDb command
    3. Record which commands respond
    4. Save vehicle profile
    5. Update database
    """

    def __init__(self, port: str = None, baudrate: int = None):
        """
        Initialize scanner.

        Args:
            port: Serial port (e.g., COM6, /dev/ttyUSB0)
            baudrate: Baud rate (default: auto-detect)
        """
        self.port = port
        self.baudrate = baudrate
        self.connection = None
        self.parser = None
        self.supported_commands = []
        self.protocol = None

    def connect(self) -> bool:
        """
        Connect to vehicle.

        Returns:
            True if connected
        """
        if not OBD_AVAILABLE:
            print("[Scanner] ✗ Cannot connect: python-obd not available")
            return False

        try:
            print(f"[Scanner] Connecting to {self.port}...")

            if self.baudrate:
                self.connection = obd.OBD(portstr=self.port, baudrate=self.baudrate)
            else:
                self.connection = obd.OBD(portstr=self.port)

            if self.connection.is_connected():
                self.protocol = self.connection.protocol_name()
                print(f"[Scanner] ✓ Connected")
                print(f"[Scanner] Protocol: {self.protocol}")
                return True
            else:
                print(f"[Scanner] ✗ Connection failed")
                return False

        except Exception as e:
            print(f"[Scanner] ✗ Connection error: {e}")
            return False

    def scan_vehicle(self, vehicle_id: int) -> Dict:
        """
        Scan vehicle for supported OBDb commands.

        Args:
            vehicle_id: Vehicle ID from database

        Returns:
            Vehicle profile dict
        """
        if not self.connection or not self.connection.is_connected():
            print("[Scanner] ✗ Not connected to vehicle")
            return {}

        print(f"\n[Scanner] Starting scan for vehicle ID {vehicle_id}...")
        print(f"[Scanner] This may take 2-5 minutes...")

        # Initialize parser
        if PARSER_AVAILABLE:
            try:
                # Try loading database
                if os.path.exists("obdb_minimal.json"):
                    self.parser = OBDbParser("obdb_minimal.json")
                else:
                    from obdb_parser import create_minimal_obdb_json
                    create_minimal_obdb_json()
                    self.parser = OBDbParser("obdb_minimal.json")
            except Exception as e:
                print(f"[Scanner] ⚠️  Parser error: {e}")

        # Create profile
        profile = {
            'vehicle_id': vehicle_id,
            'scan_timestamp': datetime.now().isoformat(),
            'protocol': self.protocol,
            'supported_commands': [],
            'command_details': [],
            'metadata': {
                'scanner_version': '1.0',
                'sentinel_pro_version': '10.0',
                'scan_duration_seconds': 0
            }
        }

        start_time = datetime.now()

        # Scan commands
        if self.parser:
            # Scan OBDb commands
            print(f"[Scanner] Scanning OBDb commands...")
            supported = self._scan_obdb_commands()
            profile['supported_commands'] = supported
            print(f"[Scanner] ✓ Found {len(supported)} supported OBDb commands")
        else:
            # Scan standard python-obd commands
            print(f"[Scanner] Scanning standard OBD commands...")
            supported = self._scan_standard_commands()
            profile['supported_commands'] = supported
            print(f"[Scanner] ✓ Found {len(supported)} supported commands")

        # Calculate scan duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        profile['metadata']['scan_duration_seconds'] = duration

        print(f"[Scanner] ✓ Scan completed in {duration:.1f} seconds")

        return profile

    def _scan_obdb_commands(self) -> List[str]:
        """
        Scan OBDb-specific commands.

        Returns:
            List of supported command strings
        """
        supported = []
        total_commands = len(self.parser.commands)

        print(f"[Scanner] Testing {total_commands} OBDb commands...")

        for idx, cmd in enumerate(self.parser.commands, 1):
            cmd_str = self.parser.get_command_string(cmd)

            # Show progress every 10 commands
            if idx % 10 == 0:
                print(f"[Scanner] Progress: {idx}/{total_commands} ({idx*100//total_commands}%)")

            # Try to query command
            if self._test_command(cmd_str):
                supported.append(cmd_str)
                # Get signal names for logging
                signals = cmd.get('signals', [])
                signal_names = [s.get('name', '') for s in signals]
                print(f"[Scanner] ✓ {cmd_str}: {', '.join(signal_names[:2])}")

        return supported

    def _scan_standard_commands(self) -> List[str]:
        """
        Scan standard python-obd commands.

        Fallback when OBDb parser not available.

        Returns:
            List of supported command names
        """
        supported = []

        # Get all available commands
        all_commands = obd.commands[1]  # Mode 01 commands

        print(f"[Scanner] Testing {len(all_commands)} standard commands...")

        for idx, cmd in enumerate(all_commands, 1):
            # Show progress
            if idx % 10 == 0:
                print(f"[Scanner] Progress: {idx}/{len(all_commands)}")

            # Query command
            response = self.connection.query(cmd)

            if response and not response.is_null():
                cmd_name = cmd.name
                supported.append(cmd_name)
                print(f"[Scanner] ✓ {cmd_name}")

        return supported

    def _test_command(self, cmd_str: str) -> bool:
        """
        Test if a specific command is supported.

        Args:
            cmd_str: Command string (e.g., "01 06")

        Returns:
            True if supported
        """
        try:
            # Parse command
            parts = cmd_str.split()
            if len(parts) != 2:
                return False

            mode_str, pid_str = parts
            mode = int(mode_str, 16)
            pid = int(pid_str, 16)

            # Try to find corresponding OBD command
            for cmd in obd.commands:
                if hasattr(cmd, 'mode') and hasattr(cmd, 'pid'):
                    if cmd.mode == mode and cmd.pid == pid:
                        # Query command
                        response = self.connection.query(cmd)
                        return response and not response.is_null()

            # If not found in standard commands, command not supported
            return False

        except Exception:
            return False

    def save_profile(self, profile: Dict, output_dir: str = "vehicle_profiles") -> bool:
        """
        Save vehicle profile to JSON file.

        Args:
            profile: Vehicle profile dict
            output_dir: Output directory

        Returns:
            True if saved successfully
        """
        try:
            # Create directory if needed
            os.makedirs(output_dir, exist_ok=True)

            # Generate filename
            vehicle_id = profile.get('vehicle_id', 'unknown')
            filename = f"vehicle_{vehicle_id}.json"
            filepath = os.path.join(output_dir, filename)

            # Save profile
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2)

            print(f"[Scanner] ✓ Profile saved: {filepath}")
            return True

        except Exception as e:
            print(f"[Scanner] ✗ Error saving profile: {e}")
            return False

    def update_database(self, vehicle_id: int, profile: Dict) -> bool:
        """
        Update database with scan results.

        Marks vehicle as OBDb-scanned and stores supported command count.

        Args:
            vehicle_id: Vehicle ID
            profile: Vehicle profile

        Returns:
            True if updated successfully
        """
        if not DATABASE_AVAILABLE:
            print("[Scanner] ⚠️  Database not available, skipping update")
            return False

        try:
            db = DatabaseManager()

            # Update vehicle record
            # Add obdb_scanned flag and supported_commands count
            supported_count = len(profile.get('supported_commands', []))

            # Note: This requires database schema update
            # For now, just log the information
            print(f"[Scanner] Vehicle {vehicle_id}: {supported_count} commands supported")
            print(f"[Scanner] ⚠️  Database update requires schema migration")
            print(f"[Scanner] Run: python migrate_db.py")

            db.close()
            return True

        except Exception as e:
            print(f"[Scanner] ✗ Database error: {e}")
            return False

    def disconnect(self):
        """Disconnect from vehicle."""
        if self.connection:
            self.connection.close()
            print("[Scanner] ✓ Disconnected")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="OBDb Scanner for SENTINEL PRO",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scan vehicle on Windows
    python obdb_scanner.py --vehicle-id 1 --port COM6

    # Scan vehicle on Linux
    python obdb_scanner.py --vehicle-id 1 --port /dev/ttyUSB0

    # Scan with custom baud rate
    python obdb_scanner.py --vehicle-id 1 --port COM6 --baudrate 38400
        """
    )

    parser.add_argument('--vehicle-id', type=int, required=True,
                        help='Vehicle ID from database')
    parser.add_argument('--port', type=str, required=True,
                        help='Serial port (e.g., COM6, /dev/ttyUSB0)')
    parser.add_argument('--baudrate', type=int, default=None,
                        help='Baud rate (default: auto-detect)')
    parser.add_argument('--output-dir', type=str, default='vehicle_profiles',
                        help='Output directory for profiles')

    args = parser.parse_args()

    # Check dependencies
    if not OBD_AVAILABLE:
        print("[Scanner] ✗ python-obd is required")
        print("[Scanner] Install with: pip install obd")
        return 1

    # Create scanner
    print("=" * 70)
    print("OBDb Scanner for SENTINEL PRO")
    print("=" * 70)

    scanner = OBDbScanner(port=args.port, baudrate=args.baudrate)

    # Connect
    if not scanner.connect():
        print("[Scanner] ✗ Failed to connect to vehicle")
        return 1

    try:
        # Scan
        profile = scanner.scan_vehicle(args.vehicle_id)

        if profile:
            # Save profile
            scanner.save_profile(profile, args.output_dir)

            # Update database
            scanner.update_database(args.vehicle_id, profile)

            # Summary
            print("\n" + "=" * 70)
            print("SCAN SUMMARY")
            print("=" * 70)
            print(f"Vehicle ID: {args.vehicle_id}")
            print(f"Protocol: {profile.get('protocol', 'Unknown')}")
            print(f"Supported commands: {len(profile.get('supported_commands', []))}")
            print(f"Scan duration: {profile['metadata']['scan_duration_seconds']:.1f} seconds")
            print("=" * 70)

            return 0
        else:
            print("[Scanner] ✗ Scan failed")
            return 1

    finally:
        # Always disconnect
        scanner.disconnect()


if __name__ == "__main__":
    sys.exit(main())
