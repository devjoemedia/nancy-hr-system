"""Shared utility helpers used across feature modules."""

from datetime import datetime

from hr.database import get_connection


def get_employee(employee_id):
    conn = get_connection()
    employee = conn.execute(
        "SELECT * FROM employees WHERE employee_id = ? AND active = 1",
        (employee_id,)
    ).fetchone()
    conn.close()
    return employee


def calculate_days(start_date, end_date):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if end < start:
            return 0

        return (end - start).days + 1

    except ValueError:
        return 0


def is_valid_date(value):
    """True if ``value`` is empty or a YYYY-MM-DD date."""
    if not value:
        return True
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False
