"""Attendance tracking feature."""

import sqlite3
from datetime import date

from hr.constants import ATTENDANCE_STATUSES, SHIFTS
from hr.database import get_connection
from hr.utils import choose, get_employee, pause


def record_attendance():
    print("\n========== RECORD ATTENDANCE ==========")

    employee_id = input("Employee ID: ").strip()

    employee = get_employee(employee_id)

    if not employee:
        print("Employee not found.")
        return

    attendance_date = input(
        "Date (YYYY-MM-DD) [today]: "
    ).strip()

    if not attendance_date:
        attendance_date = date.today().isoformat()

    shift = choose("Shift", SHIFTS)

    if not shift:
        print("Invalid shift.")
        return

    check_in = input("Check-in time (HH:MM): ").strip()
    check_out = input("Check-out time (HH:MM): ").strip()

    status = choose("Status", ATTENDANCE_STATUSES)

    if not status:
        print("Invalid status.")
        return

    conn = get_connection()

    try:
        conn.execute("""
            INSERT INTO attendance (
                employee_id,
                attendance_date,
                shift,
                check_in,
                check_out,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            employee_id,
            attendance_date,
            shift,
            check_in,
            check_out,
            status
        ))

        conn.commit()
        print("Attendance recorded successfully.")

    except sqlite3.Error as error:
        print("Error:", error)

    finally:
        conn.close()


def view_attendance():
    print("\n========== ATTENDANCE RECORDS ==========")

    employee_id = input(
        "Employee ID (leave empty for all): "
    ).strip()

    conn = get_connection()

    if employee_id:
        records = conn.execute("""
            SELECT
                a.*,
                e.first_name,
                e.last_name
            FROM attendance a
            JOIN employees e
                ON a.employee_id = e.employee_id
            WHERE a.employee_id = ?
            ORDER BY a.attendance_date DESC
        """, (employee_id,)).fetchall()
    else:
        records = conn.execute("""
            SELECT
                a.*,
                e.first_name,
                e.last_name
            FROM attendance a
            JOIN employees e
                ON a.employee_id = e.employee_id
            ORDER BY a.attendance_date DESC
        """).fetchall()

    conn.close()

    if not records:
        print("No attendance records found.")
        return

    print("-" * 100)

    for record in records:
        name = record["first_name"] + " " + record["last_name"]

        print(
            f"{record['attendance_date']} | "
            f"{record['employee_id']} | "
            f"{name} | "
            f"Shift: {record['shift'] or '-'} | "
            f"IN: {record['check_in']} | "
            f"OUT: {record['check_out']} | "
            f"{record['status']}"
        )

    print("-" * 100)


def attendance_menu():

    while True:

        print("\n")
        print("========== ATTENDANCE ==========")
        print("1. Record Attendance")
        print("2. View Attendance")
        print("0. Back")

        choice = input("Select option: ").strip()

        if choice == "1":
            record_attendance()
            pause()

        elif choice == "2":
            view_attendance()
            pause()

        elif choice == "0":
            break

        else:
            print("Invalid option.")
