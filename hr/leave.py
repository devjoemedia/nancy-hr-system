"""Leave management feature."""

from hr.constants import LEAVE_TYPES
from hr.database import get_connection
from hr.utils import calculate_days, choose, get_employee, pause


def request_leave():
    print("\n========== LEAVE REQUEST ==========")

    employee_id = input("Employee ID: ").strip()

    employee = get_employee(employee_id)

    if not employee:
        print("Employee not found.")
        return

    leave_type = choose("Leave Types", LEAVE_TYPES)

    if not leave_type:
        print("Invalid leave type.")
        return

    start_date = input("Start date (YYYY-MM-DD): ").strip()
    end_date = input("End date (YYYY-MM-DD): ").strip()

    days = calculate_days(start_date, end_date)

    if days <= 0:
        print("Invalid dates.")
        return

    reason = input("Reason: ").strip()

    conn = get_connection()

    conn.execute("""
        INSERT INTO leave_requests (
            employee_id,
            leave_type,
            start_date,
            end_date,
            days,
            reason
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        employee_id,
        leave_type,
        start_date,
        end_date,
        days,
        reason
    ))

    conn.commit()
    conn.close()

    print(f"Leave request submitted for {days} day(s).")


def view_leave_requests():
    print("\n========== LEAVE REQUESTS ==========")

    conn = get_connection()

    requests = conn.execute("""
        SELECT
            l.*,
            e.first_name,
            e.last_name
        FROM leave_requests l
        JOIN employees e
            ON l.employee_id = e.employee_id
        ORDER BY l.id DESC
    """).fetchall()

    conn.close()

    if not requests:
        print("No leave requests found.")
        return

    for request in requests:
        name = request["first_name"] + " " + request["last_name"]

        print("\n-----------------------------------")
        print("Request ID :", request["id"])
        print("Employee   :", request["employee_id"])
        print("Name       :", name)
        print("Leave Type :", request["leave_type"])
        print("Start Date :", request["start_date"])
        print("End Date   :", request["end_date"])
        print("Days       :", request["days"])
        print("Reason     :", request["reason"])
        print("Status     :", request["status"])


def approve_leave():
    print("\n========== APPROVE/REJECT LEAVE ==========")

    view_leave_requests()

    try:
        request_id = int(input("\nEnter Request ID: "))
    except ValueError:
        print("Invalid ID.")
        return

    print("\n1. Approve")
    print("2. Reject")

    choice = input("Select: ").strip()

    if choice == "1":
        status = "Approved"
    elif choice == "2":
        status = "Rejected"
    else:
        print("Invalid option.")
        return

    conn = get_connection()

    request = conn.execute("""
        SELECT *
        FROM leave_requests
        WHERE id = ?
    """, (request_id,)).fetchone()

    if not request:
        print("Leave request not found.")
        conn.close()
        return

    if request["status"] != "Pending":
        print("This request has already been processed.")
        conn.close()
        return

    # If approving annual leave, reduce annual leave balance.
    if status == "Approved" and request["leave_type"] == "Annual":

        employee = conn.execute("""
            SELECT annual_leave
            FROM employees
            WHERE employee_id = ?
        """, (request["employee_id"],)).fetchone()

        if employee["annual_leave"] < request["days"]:
            print("Employee does not have enough annual leave.")
            conn.close()
            return

        conn.execute("""
            UPDATE employees
            SET annual_leave = annual_leave - ?
            WHERE employee_id = ?
        """, (
            request["days"],
            request["employee_id"]
        ))

    # If approving sick leave, reduce sick leave balance.
    if status == "Approved" and request["leave_type"] == "Sick":

        employee = conn.execute("""
            SELECT sick_leave
            FROM employees
            WHERE employee_id = ?
        """, (request["employee_id"],)).fetchone()

        if employee["sick_leave"] < request["days"]:
            print("Employee does not have enough sick leave.")
            conn.close()
            return

        conn.execute("""
            UPDATE employees
            SET sick_leave = sick_leave - ?
            WHERE employee_id = ?
        """, (
            request["days"],
            request["employee_id"]
        ))

    conn.execute("""
        UPDATE leave_requests
        SET status = ?
        WHERE id = ?
    """, (status, request_id))

    conn.commit()
    conn.close()

    print(f"Leave request {status.lower()}.")


def view_leave_balance():
    print("\n========== LEAVE BALANCES ==========")

    employee_id = input("Employee ID: ").strip()

    employee = get_employee(employee_id)

    if not employee:
        print("Employee not found.")
        return

    print("\nEmployee:", employee["first_name"], employee["last_name"])
    print("Annual Leave Remaining:", employee["annual_leave"])
    print("Sick Leave Remaining  :", employee["sick_leave"])


def leave_menu():

    while True:

        print("\n")
        print("========== LEAVE MANAGEMENT ==========")
        print("1. Request Leave")
        print("2. View Leave Requests")
        print("3. Approve/Reject Leave")
        print("4. View Leave Balance")
        print("0. Back")

        choice = input("Select option: ").strip()

        if choice == "1":
            request_leave()
            pause()

        elif choice == "2":
            view_leave_requests()
            pause()

        elif choice == "3":
            approve_leave()
            pause()

        elif choice == "4":
            view_leave_balance()
            pause()

        elif choice == "0":
            break

        else:
            print("Invalid option.")
