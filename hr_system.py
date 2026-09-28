"""Entry point for the HR Management System.

The application logic lives in the ``hr`` package, with each feature in
its own module:

    hr/database.py    - connection and schema setup
    hr/utils.py       - shared helpers
    hr/employees.py   - employee management (CLI)
    hr/attendance.py  - attendance tracking (CLI)
    hr/leave.py       - leave management (CLI)
    hr/payroll.py     - payroll (CLI)
    hr/dashboard.py   - dashboard summary (CLI)
    hr/app.py         - text menu wiring
    hr/gui.py         - desktop graphical interface (Tkinter)

By default this launches the graphical interface:

    python hr_system.py

To use the original text menu in the terminal instead:

    python hr_system.py --cli
"""

import sys


def main():
    if "--cli" in sys.argv or "--terminal" in sys.argv:
        from hr.app import main as cli_main
        cli_main()
    else:
        from hr.gui import run
        run()


if __name__ == "__main__":
    main()
