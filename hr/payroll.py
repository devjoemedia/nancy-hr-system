"""Payroll feature."""

from hr.database import get_connection
from hr.utils import get_employee, pause


def generate_payroll():
    print("\n========== GENERATE PAYROLL ==========")

    employee_id = input("Employee ID: ").strip()

    employee = get_employee(employee_id)

    if not employee:
        print("Employee not found.")
        return

    month = input(
        "Payroll month (YYYY-MM): "
    ).strip()

    try:
        allowances = float(
            input("Allowances: ")
        )

        overtime = float(
            input("Overtime: ")
        )

        deductions = float(
            input("Deductions: ")
        )

    except ValueError:
        print("Invalid amount.")
        return

    basic_salary = employee["basic_salary"]

    net_salary = (
        basic_salary
        + allowances
        + overtime
        - deductions
    )

    conn = get_connection()

    conn.execute("""
        INSERT INTO payroll (
            employee_id,
            month,
            basic_salary,
            allowances,
            overtime,
            deductions,
            net_salary
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        employee_id,
        month,
        basic_salary,
        allowances,
        overtime,
        deductions,
        net_salary
    ))

    conn.commit()
    conn.close()

    print("\nPayroll generated successfully.")
    print("--------------------------------")
    print("Employee       :", employee["first_name"], employee["last_name"])
    print("Month          :", month)
    print("Basic Salary   :", f"{basic_salary:.2f}")
    print("Allowances     :", f"{allowances:.2f}")
    print("Overtime       :", f"{overtime:.2f}")
    print("Deductions     :", f"{deductions:.2f}")
    print("--------------------------------")
    print("NET SALARY     :", f"{net_salary:.2f}")


def view_payroll():
    print("\n========== PAYROLL HISTORY ==========")

    employee_id = input(
        "Employee ID (leave empty for all): "
    ).strip()

    conn = get_connection()

    if employee_id:
        records = conn.execute("""
            SELECT
                p.*,
                e.first_name,
                e.last_name
            FROM payroll p
            JOIN employees e
                ON p.employee_id = e.employee_id
            WHERE p.employee_id = ?
            ORDER BY p.id DESC
        """, (employee_id,)).fetchall()

    else:
        records = conn.execute("""
            SELECT
                p.*,
                e.first_name,
                e.last_name
            FROM payroll p
            JOIN employees e
                ON p.employee_id = e.employee_id
            ORDER BY p.id DESC
        """).fetchall()

    conn.close()

    if not records:
        print("No payroll records found.")
        return

    print("-" * 110)

    for record in records:
        name = record["first_name"] + " " + record["last_name"]

        print(
            f"Employee: {record['employee_id']} - {name}\n"
            f"Month: {record['month']}\n"
            f"Basic: {record['basic_salary']:.2f}\n"
            f"Allowances: {record['allowances']:.2f}\n"
            f"Overtime: {record['overtime']:.2f}\n"
            f"Deductions: {record['deductions']:.2f}\n"
            f"NET: {record['net_salary']:.2f}"
        )

        print("-" * 110)


def payroll_menu():

    while True:

        print("\n")
        print("========== PAYROLL ==========")
        print("1. Generate Payroll")
        print("2. View Payroll")
        print("0. Back")

        choice = input("Select option: ").strip()

        if choice == "1":
            generate_payroll()
            pause()

        elif choice == "2":
            view_payroll()
            pause()

        elif choice == "0":
            break

        else:
            print("Invalid option.")
