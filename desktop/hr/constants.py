"""Fixed option lists shared by the terminal menu and the GUI."""

# Attendance
SHIFTS = ["A", "B", "C", "D", "Straight Day"]
ATTENDANCE_STATUSES = ["Present", "Absent", "Late", "Permission"]

# Leave
LEAVE_TYPES = ["Annual", "Sick", "Compassionate", "Proportionate", "Study Leave"]

# Employees
EMPLOYMENT_TYPES = ["Permanent", "Contract", "Casual"]      # "Staff Status"
COMPANIES = ["GPHA", "GDLC", "BNAB", "Get Labour", "MAFEM", "Private"]
SERVICE_STATUSES = [
    "Active",
    "Sick",
    "Suspension",
    "Transferred",
    "Retired",
    "Death",
    "Leave",
    "Sacked",
    "Resigned",
]
LOCATIONS = ["Main Port", "GJT", "KUT", "FH"]
DEPARTMENTS = ["ERP", "Allocation", "Data", "PC", "Washing Bay", "Fuel"]
DESIGNATIONS = [
    "Equipment Trackers",
    "Truck Management",
    "Truck Driver",
    "Shift Supervisor / Field Supervisor",
    "Logistics Officer",
]
# Category bands: 1st = Cat, 2nd = Level, 3rd = Group.
CATEGORY_BANDS = {
    "1st": [f"Cat {n}" for n in (7, 6, 5, 4, 3)],
    "2nd": [f"Level {n}" for n in range(1, 9)],
    "3rd": [f"Group {n}" for n in (4, 5, 6, 7, 8, 9, 10, 11, 15)],
}
CATEGORIES = [category for band in CATEGORY_BANDS.values() for category in band]

LICENSE_TYPES = ["E", "F", "BE", "A/E"]

# Licence report: which date to check, and how far ahead to look.
LICENSE_STAGES = {
    "1st Renewal": "license_first_renewal",
    "2nd Renewal": "license_second_renewal",
    "Complete Expiry": "license_expiry",
}
# ``None`` means "the date has already passed".
EXPIRY_PERIODS = {
    "Already expired": None,
    "Next 30 days": 30,
    "Next 60 days": 60,
    "Next 90 days": 90,
    "Next 6 months": 182,
    "Next 12 months": 365,
}


# Employee Data Form layout: (column, label, kind, options).
# ``kind`` is "section", "entry", "date", "combo" or "radio".
EMPLOYEE_FORM = [
    (None, "Personal Details", "section", None),
    ("first_name", "First Name", "entry", None),
    ("last_name", "Last Name", "entry", None),
    ("gender", "Gender", "combo", ["Male", "Female", "Other"]),
    ("date_of_birth", "Date of Birth", "date", None),
    ("phone", "Contact", "entry", None),
    ("emergency_contact", "Emergency Contact", "entry", None),
    ("email", "email ID", "entry", None),
    ("address", "Address", "entry", None),
    ("ghana_card_no", "Ghana Card No", "entry", None),
    ("ssnit_no", "SSNIT No", "entry", None),
    ("qualification", "Qualification", "entry", None),
    (None, "Employment", "section", None),
    ("employment_type", "Staff Status", "radio", EMPLOYMENT_TYPES),
    ("company", "Company", "combo", COMPANIES),
    ("service_status", "Service Status", "combo", SERVICE_STATUSES),
    ("department", "Department", "combo", DEPARTMENTS),
    ("position", "Designation", "combo", DESIGNATIONS),
    ("category", "Category", "combo", CATEGORIES),
    ("location", "Location", "radio", LOCATIONS),
    ("date_hired", "Date Hired", "date", None),
    ("basic_salary", "Basic Salary", "entry", None),
    (None, "Driving License", "section", None),
    ("license_no", "License No", "entry", None),
    ("license_type", "License Type", "combo", LICENSE_TYPES),
    ("license_first_renewal", "1st Renewal Date", "date", None),
    ("license_second_renewal", "2nd Renewal Date", "date", None),
    ("license_expiry", "Expiry Date", "date", None),
]

# Values a blank form starts with (radio buttons default to their first option).
EMPLOYEE_FORM_DEFAULTS = {"service_status": "Active"}
