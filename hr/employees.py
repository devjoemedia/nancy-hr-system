"""Employee management feature."""

import sqlite3

from hr.constants import (
    CATEGORIES,
    COMPANIES,
    DEPARTMENTS,
    DESIGNATIONS,
    EMPLOYMENT_TYPES,
    LICENSE_TYPES,
    LOCATIONS,
    SERVICE_STATUSES,
)
from hr.database import get_connection
from hr.photos import PhotoError, photo_path, save_photo
from hr.utils import choose, get_employee, is_valid_date, pause

# Pick-list details: (column, title, options, required for a new employee).
CHOICE_FIELDS = [
    ("employment_type", "Staff Status", EMPLOYMENT_TYPES, True),
    ("company", "Company", COMPANIES, False),
    ("service_status", "Service Status", SERVICE_STATUSES, True),
    ("department", "Department", DEPARTMENTS, False),
    ("position", "Designation", DESIGNATIONS, True),
    ("category", "Category", CATEGORIES, False),
    ("location", "Location", LOCATIONS, True),
]

# Extra details asked for after the basic fields: (column, prompt, is_date).
EXTRA_TEXT_FIELDS = [
    ("ghana_card_no", "Ghana Card No", False),
    ("ssnit_no", "SSNIT No", False),
    ("qualification", "Qualification", False),
    ("emergency_contact", "Emergency Contact", False),
    ("license_no", "License No", False),
    ("license_first_renewal", "1st Renewal Date (YYYY-MM-DD)", True),
    ("license_second_renewal", "2nd Renewal Date (YYYY-MM-DD)", True),
    ("license_expiry", "Expiry Date (YYYY-MM-DD)", True),
]


def ask_photo(employee_id, current=None):
    """Optionally copy a profile picture in for ``employee_id``."""
    prompt = "Photo file (.jpg/.jpeg/.png, Enter to skip)"
    if current:
        prompt = f"Photo file [{photo_path(current)}] (Enter to keep)"

    source = input(prompt + ": ").strip().strip('"').strip("'")

    if not source:
        return

    try:
        filename = save_photo(source, employee_id)
    except PhotoError as error:
        print("Photo not saved:", error)
        return

    conn = get_connection()
    conn.execute(
        "UPDATE employees SET photo = ? WHERE employee_id = ?",
        (filename, employee_id)
    )
    conn.commit()
    conn.close()

    print("Photo saved:", photo_path(filename))


def ask_extra_details(employee=None):
    """Ask for the employee details added after the first release.

    When ``employee`` is given, pressing Enter keeps the current value.
    Returns a dict of column -> value, or ``None`` if an entry is invalid.
    """
    current = dict(employee) if employee else {}
    details = {}

    for column, title, options, required in CHOICE_FIELDS:
        # Enter keeps the current value when editing, or skips an
        # optional field for a new employee.
        allow_blank = bool(employee) or not required
        if not required:
            title += " (Enter to skip)" if not employee else ""
        value = choose(title, options, allow_blank=allow_blank,
                       current=current.get(column))
        if value is None and not allow_blank:
            print("Invalid option.")
            return None
        details[column] = value or ""

    for column, label, is_date in EXTRA_TEXT_FIELDS:
        if employee:
            value = input(f"{label} [{current.get(column) or ''}]: ").strip()
            value = value or current.get(column) or ""
        else:
            value = input(f"{label}: ").strip()

        if is_date and not is_valid_date(value):
            print("Invalid date. Use YYYY-MM-DD.")
            return None
        details[column] = value

    details["license_type"] = choose(
        "License Type", LICENSE_TYPES,
        allow_blank=True, current=current.get("license_type")) or ""

    return details


def add_employee():
    print("\n========== ADD EMPLOYEE ==========")

    employee_id = input("Employee ID: ").strip()
    first_name = input("First Name: ").strip()
    last_name = input("Last Name: ").strip()
    gender = input("Gender: ").strip()
    phone = input("Phone: ").strip()
    email = input("Email: ").strip()
    address = input("Address: ").strip()
    date_hired = input("Date Hired (YYYY-MM-DD): ").strip()

    if not is_valid_date(date_hired):
        print("Invalid date. Use YYYY-MM-DD.")
        return

    try:
        basic_salary = float(input("Basic Salary: "))
    except ValueError:
        print("Invalid salary.")
        return

    details = ask_extra_details()

    if details is None:
        return

    columns = [
        "employee_id",
        "first_name",
        "last_name",
        "gender",
        "phone",
        "email",
        "address",
        "date_hired",
        "basic_salary",
    ] + list(details)

    values = [
        employee_id,
        first_name,
        last_name,
        gender,
        phone,
        email,
        address,
        date_hired,
        basic_salary,
    ] + list(details.values())

    conn = get_connection()

    try:
        conn.execute(f"""
            INSERT INTO employees ({", ".join(columns)})
            VALUES ({", ".join("?" for _ in columns)})
        """, values)

        conn.commit()
        print("\nEmployee added successfully.")

    except sqlite3.IntegrityError:
        print("\nEmployee ID already exists.")
        return

    finally:
        conn.close()

    ask_photo(employee_id)


def view_employees():
    print("\n========== EMPLOYEE LIST ==========")

    conn = get_connection()

    employees = conn.execute("""
        SELECT *
        FROM employees
        WHERE active = 1
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    if not employees:
        print("No employees found.")
        return

    print("-" * 160)
    print(
        f"{'ID':<10}"
        f"{'Name':<25}"
        f"{'Date of Birth':<15}"
        f"{'Designation':<37}"
        f"{'Category':<10}"
        f"{'Location':<12}"
        f"{'Status':<11}"
        f"{'Salary':<15}"
        f"{'Phone':<15}"
    )
    print("-" * 160)

    for employee in employees:
        name = employee["first_name"] + " " + employee["last_name"]

        print(
            f"{employee['employee_id']:<10}"
            f"{name:<25}"
            f"{employee['date_of_birth'] or '':<15}"
            f"{employee['position'] or '':<37}"
            f"{employee['category'] or '':<10}"
            f"{employee['location'] or '':<12}"
            f"{employee['employment_type'] or '':<11}"
            f"{employee['basic_salary']:<15.2f}"
            f"{employee['phone'] or '':<15}"
        )

    print("-" * 160)


def search_employee():
    print("\n========== SEARCH EMPLOYEE ==========")

    search = input("Enter employee ID or name: ").strip()

    conn = get_connection()

    employees = conn.execute("""
        SELECT *
        FROM employees
        WHERE active = 1
        AND (
            employee_id LIKE ?
            OR first_name LIKE ?
            OR last_name LIKE ?
        )
    """, (
        f"%{search}%",
        f"%{search}%",
        f"%{search}%"
    )).fetchall()

    conn.close()

    if not employees:
        print("No employees found.")
        return

    for employee in employees:
        print("\n-----------------------------------")
        print("Employee ID :", employee["employee_id"])
        print("Name        :", employee["first_name"], employee["last_name"])
        print("Gender      :", employee["gender"])
        print("Phone       :", employee["phone"])
        print("Email       :", employee["email"])
        print("Address     :", employee["address"])
        print("Emergency   :", employee["emergency_contact"])
        print("Ghana Card  :", employee["ghana_card_no"])
        print("SSNIT No    :", employee["ssnit_no"])
        print("Qualification:", employee["qualification"])
        print("Department  :", employee["department"])
        print("Designation :", employee["position"])
        print("Location    :", employee["location"])
        print("Category    :", employee["category"])
        print("Staff Status:", employee["employment_type"])
        print("Company     :", employee["company"])
        print("Service     :", employee["service_status"])
        print("Date Hired  :", employee["date_hired"])
        print("Salary      :", employee["basic_salary"])
        print("License No  :", employee["license_no"])
        print("License Type:", employee["license_type"])
        print("1st Renewal :", employee["license_first_renewal"])
        print("2nd Renewal :", employee["license_second_renewal"])
        print("Expiry Date :", employee["license_expiry"])
        print("Annual Leave:", employee["annual_leave"])
        print("Sick Leave  :", employee["sick_leave"])
        print("Photo       :", photo_path(employee["photo"]) or "None")


def update_employee():
    print("\n========== UPDATE EMPLOYEE ==========")

    employee_id = input("Employee ID: ").strip()

    employee = get_employee(employee_id)

    if not employee:
        print("Employee not found.")
        return

    print("Leave a field empty to keep the current value.")

    first_name = input(
        f"First Name [{employee['first_name']}]: "
    ).strip() or employee["first_name"]

    last_name = input(
        f"Last Name [{employee['last_name']}]: "
    ).strip() or employee["last_name"]

    phone = input(
        f"Phone [{employee['phone']}]: "
    ).strip() or employee["phone"]

    email = input(
        f"Email [{employee['email']}]: "
    ).strip() or employee["email"]

    salary_input = input(
        f"Basic Salary [{employee['basic_salary']}]: "
    ).strip()

    if salary_input:
        try:
            salary = float(salary_input)
        except ValueError:
            print("Invalid salary.")
            return
    else:
        salary = employee["basic_salary"]

    details = ask_extra_details(employee)

    if details is None:
        return

    details.update({
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
        "email": email,
        "basic_salary": salary,
    })

    conn = get_connection()

    conn.execute(f"""
        UPDATE employees
        SET {", ".join(f"{column} = ?" for column in details)}
        WHERE employee_id = ?
    """, list(details.values()) + [employee_id])

    conn.commit()
    conn.close()

    ask_photo(employee_id, employee["photo"])

    print("Employee updated successfully.")


def delete_employee():
    print("\n========== DELETE EMPLOYEE ==========")

    employee_id = input("Employee ID: ").strip()

    employee = get_employee(employee_id)

    if not employee:
        print("Employee not found.")
        return

    confirm = input(
        f"Deactivate {employee['first_name']} {employee['last_name']}? (y/n): "
    ).lower()

    if confirm != "y":
        print("Operation cancelled.")
        return

    conn = get_connection()

    conn.execute("""
        UPDATE employees
        SET active = 0
        WHERE employee_id = ?
    """, (employee_id,))

    conn.commit()
    conn.close()

    print("Employee deactivated successfully.")


def employee_menu():

    while True:

        print("\n")
        print("========== EMPLOYEE MANAGEMENT ==========")
        print("1. Add Employee")
        print("2. View Employees")
        print("3. Search Employee")
        print("4. Update Employee")
        print("5. Deactivate Employee")
        print("0. Back")

        choice = input("Select option: ").strip()

        if choice == "1":
            add_employee()
            pause()

        elif choice == "2":
            view_employees()
            pause()

        elif choice == "3":
            search_employee()
            pause()

        elif choice == "4":
            update_employee()
            pause()

        elif choice == "5":
            delete_employee()
            pause()

        elif choice == "0":
            break

        else:
            print("Invalid option.")
