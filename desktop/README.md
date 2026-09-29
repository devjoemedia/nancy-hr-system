# Human Resource Management System

A simple local Human Resource Management System developed in Python.

The system is designed to run locally from PyCharm without Django,
Flask, or any other web framework.

## Main Modules

The system contains four main modules:

1. Employee Database
2. Attendance Management
3. Leave Management
4. Payroll Management

---

## 1. Employee Database

The Employee Database stores information about employees.

### Employee information

- Employee ID
- First name
- Last name
- Gender
- Date of birth
- Contact (phone number)
- Emergency contact
- Email
- Address
- Ghana Card number
- SSNIT number
- Qualification
- Department: ERP, Allocation, Data, PC, Washing Bay, Fuel
- Designation: Equipment Trackers, Truck Management, Truck Driver,
  Shift Supervisor / Field Supervisor, Logistics Officer
- Category: Cat 7–3 (1st), Level 1–8 (2nd), Group 4–11 and 15 (3rd)
- Location: Main Port, GJT, KUT, FH
- Staff status: Permanent, Contract or Casual
- Company: GPHA, GDLC, BNAB, Get Labour, MAFEM, Private
- Service status: Active, Sick, Suspension, Transferred, Retired, Death,
  Leave, Sacked, Resigned
- Date hired
- Basic salary
- License number and type (E, F, BE, A/E)
- License 1st renewal date, 2nd renewal date and expiry date
- Profile picture (JPG, JPEG or PNG)

### Profile pictures

Use "Choose Photo…" on the Employee Data Form (or give a file path when
adding/updating in the terminal). The picture is resized, turned upright if
it came from a phone, and saved as `photos/<Employee Code>.png` when you
press Submit. Selecting an employee in the list shows their photo.

Keep the `photos` folder with `hr_management.db` when moving the system to
another computer.

### Employee functions

- Add employee
- View employees
- Search employee
- Update employee
- Delete employee
- View employee details

---

## 2. Attendance Management

The Attendance module records employee attendance.

### Attendance information

- Employee ID
- Employee name
- Date
- Shift (A, B, C, D or Straight Day)
- Check-in time
- Check-out time
- Attendance status

### Attendance statuses

- Present
- Absent
- Late
- Permission

### Attendance functions

- Record attendance
- View attendance
- Search attendance
- Calculate working hours
- View employee attendance history

---

## 3. Leave Management

The Leave Management module handles employee leave requests.

### Leave types

- Annual Leave (deducted from the annual leave balance)
- Sick Leave (deducted from the sick leave balance)
- Compassionate Leave
- Proportionate Leave
- Study Leave

### Leave status

- Pending
- Approved
- Rejected

### Leave functions

- Submit leave request
- View leave requests
- Approve leave
- Reject leave
- View leave history
- Calculate leave duration

---

## 4. Payroll Management

The Payroll module calculates employee salaries.

### Payroll information

- Employee
- Basic salary
- Allowances
- Overtime
- Deductions
- Gross salary
- Net salary
- Pay date

### Salary calculation

Gross salary:

Basic Salary + Allowances + Overtime

Net salary:

Gross Salary - Deductions

Example:

Basic Salary = 5,000

Allowances = 500

Overtime = 200

Deductions = 300

Gross Salary:

5,000 + 500 + 200 = 5,700

Net Salary:

5,700 - 300 = 5,400

---

## Export to Excel

Click **Export to Excel** on the Dashboard or the Reports tab (or choose
option 6 in the terminal menu) to save all records as an Excel workbook with
one sheet each for the Staff Report, Employees, Attendance, Leave, Payroll
and Licences. The terminal menu saves it in an `exports` folder next to the
app.

The file is a copy of the records at that moment; changes made in Excel do
not go back into the system. It contains personal details, so store it
carefully. Needs `openpyxl` (included in `requirements.txt`).

## Reports

The Reports tab (and menu option 5 in the terminal) shows:

- Total number of Permanent, Contract and Casual staff
- Permanent, Contract and Casual staff counted per location
  (Main Port, GJT, KUT, FH)
- License expiry: choose 1st Renewal, 2nd Renewal or Complete Expiry and
  an expiring period (already expired, next 30/60/90 days, 6 or 12 months)
  to list the staff whose license date falls in that period

The Dashboard also shows how many licenses are due in the next 30 days.

---

# 5. Technology

The project uses:

- Python 3
- SQLite3
- Tkinter (if GUI is enabled)
- PyCharm

SQLite is included with Python, so no separate database server is required.

---

# 6. Requirements

Install:

- Python 3
- PyCharm

Check Python:

python --version

or:

py --version

Install Pillow (needed for profile pictures):

pip install pillow

Everything else works without it.

No Django installation is required.

No Flask installation is required.

---

# 7. Project Setup

Open the project in PyCharm.

Open the PyCharm Terminal.

Create a virtual environment:

python -m venv venv

Windows:

venv\Scripts\activate

PowerShell:

.\venv\Scripts\Activate.ps1

Linux/macOS:

source venv/bin/activate

---

# 8. Database

The application uses SQLite.

The database file is:

hr_system.db

The database is created automatically when the application starts.

The application should create the required tables automatically.

Expected tables:

- employees
- attendance
- leave_requests
- payroll

---

# 9. Running the Application

Run:

python main.py

The application should open the main HR Management System.

---

# 10. Main Menu

The application should provide options similar to:

1. Employee Management
2. Attendance Management
3. Leave Management
4. Payroll Management
5. Reports
6. Exit

---

# 11. Testing Employee Management

Add a sample employee:

Employee ID:
EMP001

First Name:
John

Last Name:
Mensah

Gender:
Male

Date of Birth:
1995-05-10

Phone:
0240000000

Email:
john@example.com

Address:
Accra, Ghana

Department:
Information Technology

Position:
Software Developer

Date Hired:
2025-01-15

Basic Salary:
5000

Status:
Active

Save the employee.

Then test:

- View employees
- Search EMP001
- Update EMP001
- View employee details
- Delete/deactivate EMP001

---

# 12. Sample Employees

Use these employees for testing:

| ID | Name | Department | Position | Salary |
|---|---|---|---|---:|
| EMP001 | John Mensah | IT | Software Developer | 5000 |
| EMP002 | Mary Owusu | HR | HR Officer | 4500 |
| EMP003 | David Asante | Finance | Accountant | 5500 |
| EMP004 | Linda Addo | Marketing | Marketing Officer | 4000 |
| EMP005 | Michael Boateng | IT | System Administrator | 4800 |

---

# 13. Testing Attendance

Record attendance for EMP001.

Example:

Employee:
EMP001

Date:
2026-09-20

Check-in:
08:00

Check-out:
17:00

Status:
Present

Test the following statuses:

- Present
- Absent
- Late
- Permission

Test:

- Add attendance
- View attendance
- Search by employee
- Search by date
- View attendance history

---

# 14. Testing Leave Management

Create a leave request.

Example:

Employee:
EMP001

Leave Type:
Annual Leave

Start Date:
2026-10-01

End Date:
2026-10-05

Reason:
Annual vacation

Status:
Pending

Test:

- Submit leave
- View pending leave
- Approve leave
- Reject leave
- View leave history

---

# 15. Testing Payroll

Create payroll for EMP001.

Example:

Employee:
EMP001

Basic Salary:
5000

Allowances:
500

Overtime:
200

Deductions:
300

Expected calculation:

Gross Salary = 5000 + 500 + 200

Gross Salary = 5700

Net Salary = 5700 - 300

Net Salary = 5400

Expected result:

Gross Salary: 5700

Net Salary: 5400

---

# 16. Testing the Database

You can inspect the SQLite database using Python.

Run:

python

Then:

import sqlite3

connection = sqlite3.connect("hr_system.db")

cursor = connection.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")

print(cursor.fetchall())

connection.close()

Expected result should contain tables similar to:

employees
attendance
leave_requests
payroll

---

# 17. Testing Employee Records

Open Python:

python

Run:

import sqlite3

connection = sqlite3.connect("hr_system.db")

cursor = connection.cursor()

cursor.execute("SELECT * FROM employees")

employees = cursor.fetchall()

for employee in employees:
    print(employee)

connection.close()

---

# 18. Testing Attendance Records

Run:

import sqlite3

connection = sqlite3.connect("hr_system.db")

cursor = connection.cursor()

cursor.execute("SELECT * FROM attendance")

records = cursor.fetchall()

for record in records:
    print(record)

connection.close()

---

# 19. Testing Leave Records

Run:

import sqlite3

connection = sqlite3.connect("hr_system.db")

cursor = connection.cursor()

cursor.execute("SELECT * FROM leave_requests")

records = cursor.fetchall()

for record in records:
    print(record)

connection.close()

---

# 20. Testing Payroll Records

Run:

import sqlite3

connection = sqlite3.connect("hr_system.db")

cursor = connection.cursor()

cursor.execute("SELECT * FROM payroll")

records = cursor.fetchall()

for record in records:
    print(record)

connection.close()

---

# 21. Basic Testing Checklist

## Employee Management

[ ] Add employee

[ ] View employee

[ ] Search employee

[ ] Update employee

[ ] Delete/deactivate employee

## Attendance

[ ] Record attendance

[ ] View attendance

[ ] Search attendance

[ ] Record absent employee

[ ] Record late employee

[ ] Calculate working hours

## Leave

[ ] Submit leave

[ ] View leave

[ ] Approve leave

[ ] Reject leave

[ ] Calculate leave duration

## Payroll

[ ] Create payroll

[ ] Calculate gross salary

[ ] Calculate deductions

[ ] Calculate net salary

[ ] View payroll

[ ] View payroll history

## Database

[ ] Database created

[ ] Employee table created

[ ] Attendance table created

[ ] Leave table created

[ ] Payroll table created

---

# 22. Troubleshooting

## Python is not recognized

Try:

py --version

If Python is installed, use:

py main.py

instead of:

python main.py

---

## Virtual environment is not activated

Windows:

venv\Scripts\activate

PowerShell:

.\venv\Scripts\Activate.ps1

---

## Database does not exist

Run:

python main.py

The application should create the SQLite database automatically.

---

## Database is corrupted

Stop the application.

Delete:

hr_system.db

Run:

python main.py

The application should create a new database.

WARNING:

Deleting the database removes all stored employee,
attendance, leave, and payroll records.

Only do this during testing.

---

# 23. Running the Project

The normal workflow is:

1. Open PyCharm.
2. Open the HR Management System project.
3. Open the terminal.
4. Activate the virtual environment.
5. Run main.py.

Command:

python main.py

---

# 24. Important Files

main.py

The main entry point of the application.

database.py

Handles the SQLite database and database connections.

employees.py

Handles employee records.

attendance.py

Handles attendance records.

leave_management.py

Handles leave requests and approvals.

payroll.py

Handles salary and payroll calculations.

reports.py

Generates HR reports.

utils.py

Contains reusable helper functions.

hr_system.db

The local SQLite database.

---

# 25. Future Improvements

Possible improvements include:

- Login system
- Admin and HR user roles
- Employee dashboard
- Attendance dashboard
- Leave calendar
- Payroll reports
- PDF payslips
- Excel export
- Employee profile pictures
- Department management
- Automatic payroll calculations
- Backup and restore
- Search and filtering
- Monthly HR reports

---

# 26. Author

Human Resource Management System

Developed using Python and SQLite.

Designed to run locally using PyCharm.
