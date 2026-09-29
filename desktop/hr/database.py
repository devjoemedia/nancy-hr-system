"""Database connection and schema setup."""

import os
import sqlite3
import sys

# The project folder (the one holding hr_system.py). Files are looked up
# here rather than in whatever folder the app happens to be started from.
# When packaged as an .exe, use the folder the .exe is in instead: the code
# itself runs from a temporary folder that is deleted when the app closes.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE = os.path.join(APP_DIR, "hr_management.db")


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Employees
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            gender TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            department TEXT,
            position TEXT,
            date_hired TEXT,
            basic_salary REAL DEFAULT 0,
            annual_leave INTEGER DEFAULT 20,
            sick_leave INTEGER DEFAULT 10,
            active INTEGER DEFAULT 1
        )
    """)

    # Attendance
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            check_in TEXT,
            check_out TEXT,
            status TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Leave
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            days INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Payroll
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            month TEXT NOT NULL,
            basic_salary REAL NOT NULL,
            allowances REAL DEFAULT 0,
            overtime REAL DEFAULT 0,
            deductions REAL DEFAULT 0,
            net_salary REAL NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Lightweight migrations for columns added after the first release.
    # The GUI "Employee Data Form" needs Date of Birth and Location, which
    # were not part of the original schema.
    _ensure_column(cursor, "employees", "date_of_birth", "TEXT")
    _ensure_column(cursor, "employees", "location", "TEXT DEFAULT 'Office'")

    # Employee identity, staff type, licence and emergency contact details.
    _ensure_column(cursor, "employees", "employment_type", "TEXT DEFAULT 'Permanent'")
    _ensure_column(cursor, "employees", "ghana_card_no", "TEXT")
    _ensure_column(cursor, "employees", "ssnit_no", "TEXT")
    _ensure_column(cursor, "employees", "qualification", "TEXT")
    _ensure_column(cursor, "employees", "license_no", "TEXT")
    _ensure_column(cursor, "employees", "license_type", "TEXT")
    _ensure_column(cursor, "employees", "license_first_renewal", "TEXT")
    _ensure_column(cursor, "employees", "license_second_renewal", "TEXT")
    _ensure_column(cursor, "employees", "license_expiry", "TEXT")
    _ensure_column(cursor, "employees", "emergency_contact", "TEXT")
    _ensure_column(cursor, "employees", "photo", "TEXT")

    # Company, service status and category.
    _ensure_column(cursor, "employees", "company", "TEXT")
    _ensure_column(cursor, "employees", "service_status", "TEXT DEFAULT 'Active'")
    _ensure_column(cursor, "employees", "category", "TEXT")

    # "Shift Supervisor" became "Shift Supervisor / Field Supervisor".
    cursor.execute("""
        UPDATE employees SET position = 'Shift Supervisor / Field Supervisor'
        WHERE position = 'Shift Supervisor'
    """)

    # Attendance shift (A, B, C, D or Straight Day).
    _ensure_column(cursor, "attendance", "shift", "TEXT")

    conn.commit()
    conn.close()


def _ensure_column(cursor, table, column, definition):
    """Add ``column`` to ``table`` if it is not already present."""
    existing = [row["name"] for row in cursor.execute(f"PRAGMA table_info({table})")]
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
