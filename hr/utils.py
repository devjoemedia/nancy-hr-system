"""Shared utility helpers used across feature modules."""

from datetime import datetime

from hr.database import get_connection


def pause():
    input("\nPress Enter to continue...")


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


def choose(title, options, allow_blank=False, current=None):
    """Print a numbered list and return the chosen option.

    Returns ``current`` when the user presses Enter and ``allow_blank`` is
    set (useful when updating a record), or ``None`` for an invalid choice.
    """
    print(f"\n{title}:")
    for number, option in enumerate(options, start=1):
        print(f"{number}. {option}")

    prompt = "Select"
    if allow_blank:
        prompt += f" [{current or ''}]"
    choice = input(prompt + ": ").strip()

    if not choice and allow_blank:
        return current
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    return None
