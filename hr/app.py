"""Main menu wiring for the HR Management System."""

from hr.attendance import attendance_menu
from hr.dashboard import dashboard
from hr.database import setup_database
from hr.employees import employee_menu
from hr.leave import leave_menu
from hr.payroll import payroll_menu
from hr.reports import reports_menu


def main():

    setup_database()

    while True:

        dashboard()

        print("\nMAIN MENU")
        print("1. Employee Database")
        print("2. Attendance")
        print("3. Leave Management")
        print("4. Payroll")
        print("5. Reports")
        print("0. Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            employee_menu()

        elif choice == "2":
            attendance_menu()

        elif choice == "3":
            leave_menu()

        elif choice == "4":
            payroll_menu()

        elif choice == "5":
            reports_menu()

        elif choice == "0":
            print("\nThank you for using the HR Management System.")
            break

        else:
            print("Invalid option.")
