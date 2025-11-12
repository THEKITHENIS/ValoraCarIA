"""
Database Migration Script for OBDb Integration
===============================================

Migrates existing SENTINEL PRO database to support OBDb extended signals.

IMPORTANT: This script ONLY adds new tables - it does NOT modify existing data.

What this script does:
- Creates backup of current database
- Adds obd_extended table
- Adds indices for performance
- Verifies migration success
- Leaves all existing data intact

Usage:
    python migrate_db.py
    python migrate_db.py --db-path ../db/sentinel.db
    python migrate_db.py --skip-backup (not recommended)

Author: SENTINEL PRO Team
Version: 1.0
"""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime


def backup_database(db_path: str) -> str:
    """
    Create backup of database before migration.

    Args:
        db_path: Path to database file

    Returns:
        Path to backup file
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"

    print(f"[Migrate] Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)

    # Verify backup
    backup_size = os.path.getsize(backup_path)
    original_size = os.path.getsize(db_path)

    if backup_size != original_size:
        raise Exception("Backup verification failed: size mismatch")

    print(f"[Migrate] ✓ Backup created successfully ({backup_size} bytes)")
    return backup_path


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """
    Check if table exists in database.

    Args:
        conn: Database connection
        table_name: Name of table

    Returns:
        True if table exists
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    ''', (table_name,))

    return cursor.fetchone() is not None


def migrate_database(db_path: str, skip_backup: bool = False) -> bool:
    """
    Perform database migration.

    Args:
        db_path: Path to database file
        skip_backup: Skip backup creation (not recommended)

    Returns:
        True if migration successful
    """
    print("=" * 70)
    print("SENTINEL PRO - Database Migration")
    print("OBDb Extended Signals Support")
    print("=" * 70)

    # Create backup unless skipped
    backup_path = None
    if not skip_backup:
        try:
            backup_path = backup_database(db_path)
        except Exception as e:
            print(f"[Migrate] ✗ Backup failed: {e}")
            print(f"[Migrate] Migration aborted for safety")
            return False

    # Connect to database
    try:
        print(f"\n[Migrate] Connecting to database: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

    except Exception as e:
        print(f"[Migrate] ✗ Connection failed: {e}")
        return False

    try:
        # Check if migration already applied
        if table_exists(conn, 'obd_extended'):
            print(f"\n[Migrate] ⚠️  Table 'obd_extended' already exists")
            print(f"[Migrate] Database appears to be already migrated")

            # Ask user if they want to continue
            response = input("\n[Migrate] Continue anyway? (y/N): ").strip().lower()
            if response != 'y':
                print(f"[Migrate] Migration cancelled")
                conn.close()
                return False

        print(f"\n[Migrate] Creating table 'obd_extended'...")

        # Create obd_extended table
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

        print(f"[Migrate] ✓ Table created")

        # Create indices
        print(f"\n[Migrate] Creating indices...")

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_obd_extended_trip
            ON obd_extended(trip_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_obd_extended_timestamp
            ON obd_extended(timestamp)
        ''')

        print(f"[Migrate] ✓ Indices created")

        # Commit changes
        conn.commit()
        print(f"\n[Migrate] ✓ Migration completed successfully")

        # Verify migration
        print(f"\n[Migrate] Verifying migration...")

        # Check table exists
        if not table_exists(conn, 'obd_extended'):
            raise Exception("Verification failed: table not found")

        # Check indices exist
        cursor.execute('''
            SELECT name FROM sqlite_master
            WHERE type='index' AND name LIKE 'idx_obd_extended%'
        ''')

        indices = cursor.fetchall()
        if len(indices) < 2:
            raise Exception(f"Verification failed: expected 2 indices, found {len(indices)}")

        print(f"[Migrate] ✓ Verification passed")

        # Display summary
        print("\n" + "=" * 70)
        print("MIGRATION SUMMARY")
        print("=" * 70)
        print(f"Database: {db_path}")
        print(f"Backup: {backup_path if backup_path else 'None (skipped)'}")
        print(f"New table: obd_extended")
        print(f"New indices: {len(indices)}")
        print(f"Status: SUCCESS")
        print("=" * 70)

        print(f"\n[Migrate] ℹ️  Existing data preserved:")
        print(f"  - vehicles table: UNCHANGED")
        print(f"  - trips table: UNCHANGED")
        print(f"  - obd_data table: UNCHANGED")
        print(f"  - maintenance table: UNCHANGED")
        print(f"  - alerts table: UNCHANGED")

        print(f"\n[Migrate] ℹ️  Next steps:")
        print(f"  1. Restart obd_server.py")
        print(f"  2. Run obdb_scanner.py to scan vehicle")
        print(f"  3. Extended signals will be saved automatically")

        return True

    except Exception as e:
        print(f"\n[Migrate] ✗ Migration failed: {e}")
        print(f"[Migrate] Rolling back changes...")

        conn.rollback()

        if backup_path:
            print(f"\n[Migrate] ⚠️  To restore from backup:")
            print(f"  cp '{backup_path}' '{db_path}'")

        return False

    finally:
        conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration script for OBDb support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Migrate with backup (recommended)
    python migrate_db.py

    # Migrate specific database
    python migrate_db.py --db-path /path/to/sentinel.db

    # Skip backup (not recommended)
    python migrate_db.py --skip-backup

Notes:
    - This script ONLY adds new tables
    - Existing data is NEVER modified
    - Backup is STRONGLY recommended
    - Migration is idempotent (safe to run multiple times)
        """
    )

    parser.add_argument('--db-path', type=str, default='../db/sentinel.db',
                        help='Path to database file')
    parser.add_argument('--skip-backup', action='store_true',
                        help='Skip backup creation (not recommended)')

    args = parser.parse_args()

    # Expand path
    db_path = os.path.abspath(args.db_path)

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"[Migrate] ✗ Database not found: {db_path}")
        print(f"[Migrate] Please check the path and try again")
        return 1

    # Warn if skipping backup
    if args.skip_backup:
        print(f"\n⚠️  WARNING: Backup will be skipped!")
        print(f"⚠️  This is NOT recommended for production databases")
        response = input(f"\nContinue without backup? (y/N): ").strip().lower()
        if response != 'y':
            print(f"[Migrate] Migration cancelled")
            return 0

    # Perform migration
    success = migrate_database(db_path, args.skip_backup)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
