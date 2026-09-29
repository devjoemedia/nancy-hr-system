"""Reports: staff numbers and licence expiry (web version)."""

from datetime import date, datetime, timedelta

from hr.constants import (
    EMPLOYMENT_TYPES,
    EXPIRY_PERIODS,
    LICENSE_STAGES,
    LOCATIONS,
)
from hr.database import get_connection


def staff_summary():
    """Count active staff by location and staff status.

    Returns ``(rows, totals)``. Each row is ``(location, count for each
    of EMPLOYMENT_TYPES..., total)`` and ``totals`` maps each staff status
    (and "Total") to its overall count.
    """
    conn = get_connection()
    counts = conn.execute("""
        SELECT
            COALESCE(NULLIF(location, ''), 'Not set') AS location,
            COALESCE(NULLIF(employment_type, ''), 'Permanent') AS employment_type,
            COUNT(*) AS n
        FROM employees
        WHERE active = 1
        GROUP BY 1, 2
    """).fetchall()
    conn.close()

    table = {}
    for row in counts:
        table.setdefault(row["location"], {})[row["employment_type"]] = row["n"]

    # Known locations first (always shown), then anything else in the data.
    locations = LOCATIONS + sorted(loc for loc in table if loc not in LOCATIONS)

    rows = []
    totals = {kind: 0 for kind in EMPLOYMENT_TYPES}
    for location in locations:
        by_type = table.get(location, {})
        counts_here = [by_type.get(kind, 0) for kind in EMPLOYMENT_TYPES]
        rows.append((location, *counts_here, sum(counts_here)))
        for kind, n in zip(EMPLOYMENT_TYPES, counts_here):
            totals[kind] += n
    totals["Total"] = sum(totals[kind] for kind in EMPLOYMENT_TYPES)
    return rows, totals


def license_expiry(stage, period):
    """Employees whose licence ``stage`` date falls within ``period``.

    ``stage`` is a key of LICENSE_STAGES and ``period`` a key of
    EXPIRY_PERIODS. Returns a list of dicts sorted by date, each with the
    employee details, the date and the number of days left (negative when
    already passed).
    """
    column = LICENSE_STAGES[stage]
    days = EXPIRY_PERIODS[period]
    today = date.today()

    conn = get_connection()
    rows = conn.execute(f"""
        SELECT * FROM employees
        WHERE active = 1 AND {column} IS NOT NULL AND {column} != ''
    """).fetchall()
    conn.close()

    results = []
    for row in rows:
        try:
            due = datetime.strptime(row[column], "%Y-%m-%d").date()
        except ValueError:
            continue

        if days is None:
            matches = due < today
        else:
            matches = today <= due <= today + timedelta(days=days)

        if matches:
            results.append({
                "employee_id": row["employee_id"],
                "name": f"{row['first_name']} {row['last_name']}",
                "designation": row["position"] or "",
                "location": row["location"] or "",
                "license_no": row["license_no"] or "",
                "license_type": row["license_type"] or "",
                "date": row[column],
                "days_left": (due - today).days,
            })

    results.sort(key=lambda r: r["date"])
    return results


def licenses_due_count(days=30):
    """How many active staff have any licence date due in the next ``days``."""
    today = date.today()
    limit = today + timedelta(days=days)
    conn = get_connection()
    rows = conn.execute("SELECT * FROM employees WHERE active = 1").fetchall()
    conn.close()

    count = 0
    for row in rows:
        for column in LICENSE_STAGES.values():
            try:
                due = datetime.strptime(row[column] or "", "%Y-%m-%d").date()
            except ValueError:
                continue
            if today <= due <= limit:
                count += 1
                break
    return count
