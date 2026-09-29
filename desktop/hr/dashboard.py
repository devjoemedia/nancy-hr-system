"""Dashboard summary feature."""

from datetime import date

from hr.database import get_connection
from hr.reports import licenses_due_count, staff_summary


def dashboard():
    conn = get_connection()

    employee_count = conn.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE active = 1
    """).fetchone()[0]

    today = date.today().isoformat()

    attendance_today = conn.execute("""
        SELECT COUNT(*)
        FROM attendance
        WHERE attendance_date = ?
    """, (today,)).fetchone()[0]

    pending_leave = conn.execute("""
        SELECT COUNT(*)
        FROM leave_requests
        WHERE status = 'Pending'
    """).fetchone()[0]

    payroll_count = conn.execute("""
        SELECT COUNT(*)
        FROM payroll
    """).fetchone()[0]

    conn.close()

    _rows, staff = staff_summary()
    licenses_due = licenses_due_count(30)

    print("\n")
    print("=" * 60)
    print("              HR MANAGEMENT SYSTEM")
    print("=" * 60)

    print()
    print(f"Active Employees     : {employee_count}")
    print(f"  Perm / Contr / Cas : "
          f"{staff['Permanent']} / {staff['Contract']} / {staff['Casual']}")
    print(f"Attendance Today     : {attendance_today}")
    print(f"Pending Leave        : {pending_leave}")
    print(f"Payroll Records      : {payroll_count}")
    print(f"Licenses Due (30d)   : {licenses_due}")

    print("=" * 60)
