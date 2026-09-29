"""Web version of the HR Management System (Flask).

A standalone project: everything it needs is in this folder, including
its own copy of the shared ``hr`` code. Records are kept in
``hr_management.db`` next to this file.

Run locally, from this folder:

    pip install -r requirements.txt
    flask --app app create-user
    flask --app app run --debug

Then open http://127.0.0.1:5000. See DEPLOY.md for free hosting.
"""

import io
import os
import re
import secrets
import sqlite3
from datetime import date, timedelta

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)

from hr.constants import (
    ATTENDANCE_STATUSES,
    EMPLOYEE_FORM,
    EMPLOYEE_FORM_DEFAULTS,
    EMPLOYMENT_TYPES,
    EXPIRY_PERIODS,
    LEAVE_TYPES,
    LICENSE_STAGES,
    SHIFTS,
)
from hr.database import APP_DIR, get_connection, setup_database
from hr.export import (
    OPENPYXL_MISSING,
    default_filename,
    excel_available,
    workbook_bytes,
)
from hr.leave import decide_leave
from hr.photos import (
    PHOTO_DIR,
    PhotoError,
    avatar_color,
    delete_photo,
    find_logo,
    initials,
    logo_png,
    save_photo,
)
from hr.reports import license_expiry, licenses_due_count, staff_summary
from hr.utils import calculate_days, get_employee, is_valid_date
from auth import (
    check_csrf,
    check_login,
    create_user,
    csrf_token,
    load_current_user,
    login_required,
    register_commands,
    set_password,
    setup_users_table,
)

# Employee codes end up in web addresses and photo file names.
EMPLOYEE_CODE = re.compile(r"^[A-Za-z0-9_-]{1,30}$")


def _secret_key():
    """Signing key for sessions: from HR_SECRET_KEY, or a file kept on disk."""
    if os.environ.get("HR_SECRET_KEY"):
        return os.environ["HR_SECRET_KEY"]
    path = os.path.join(APP_DIR, "instance", "secret_key")
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


def create_app():
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=_secret_key(),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,         # photo uploads up to 8 MB
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Cookies only travel over HTTPS, except when testing with --debug.
        SESSION_COOKIE_SECURE=not app.debug,
    )

    setup_database()
    setup_users_table()
    register_commands(app)

    app.before_request(load_current_user)
    app.before_request(check_csrf)

    # Globals, so the shared macros in macros.html can use them too.
    app.jinja_env.globals.update(
        csrf_token=csrf_token, initials=initials, avatar_color=avatar_color)

    @app.context_processor
    def template_helpers():
        return {"has_logo": find_logo() is not None}

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        # Staff records are private: don't let browsers or proxies keep copies.
        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store"
        return response

    register_routes(app)
    return app


def active_employees():
    conn = get_connection()
    rows = conn.execute("""
        SELECT employee_id, first_name, last_name FROM employees
        WHERE active = 1 ORDER BY first_name, last_name
    """).fetchall()
    conn.close()
    return rows


def to_float(value, label, errors):
    try:
        return float(value or 0)
    except ValueError:
        errors.append(f"{label} must be a number.")
        return 0.0


def register_routes(app):

    # ---- Sign in / out ---------------------------------------------------

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            try:
                user = check_login(request.form.get("username"),
                                   request.form.get("password"))
            except PermissionError:
                flash("Too many wrong passwords. Try again in 15 minutes.", "error")
                return render_template("login.html"), 429
            if user:
                session.clear()
                session.permanent = True
                session["user_id"] = user["id"]
                target = request.args.get("next", "")
                # Only follow local links, never another website.
                if not target.startswith("/") or target.startswith("//"):
                    target = url_for("dashboard")
                return redirect(target)
            flash("Wrong username or password.", "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You have signed out.", "info")
        return redirect(url_for("login"))

    # ---- Dashboard --------------------------------------------------------

    @app.route("/")
    @login_required
    def dashboard():
        conn = get_connection()
        today = date.today().isoformat()
        stats = [
            ("Active Employees", conn.execute(
                "SELECT COUNT(*) FROM employees WHERE active = 1").fetchone()[0],
             "#C0501E"),
            ("Attendance Today", conn.execute(
                "SELECT COUNT(*) FROM attendance WHERE attendance_date = ?",
                (today,)).fetchone()[0], "#2E7D5B"),
            ("Pending Leave", conn.execute(
                "SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'"
            ).fetchone()[0], "#B4881C"),
            ("Payroll Records", conn.execute(
                "SELECT COUNT(*) FROM payroll").fetchone()[0], "#3A5A8C"),
            ("Licenses Due (30 days)", licenses_due_count(30), "#7A3E8C"),
        ]
        conn.close()
        return render_template("dashboard.html", stats=stats)

    logo_cache = {}

    @app.route("/logo")
    def logo():
        path = find_logo()
        if not path:
            abort(404)
        # Serve a copy with the plain background removed (made once, then
        # reused until the logo file changes); fall back to the file as is.
        stamp = (path, os.path.getmtime(path))
        if logo_cache.get("stamp") != stamp:
            logo_cache.update(stamp=stamp, png=logo_png(path))
        if logo_cache["png"] is None:
            return send_file(path, max_age=3600)
        return send_file(io.BytesIO(logo_cache["png"]), mimetype="image/png",
                         max_age=3600)

    # ---- Employees --------------------------------------------------------

    @app.route("/employees")
    @login_required
    def employees():
        term = request.args.get("q", "").strip()
        conn = get_connection()
        if term:
            like = f"%{term}%"
            rows = conn.execute("""
                SELECT * FROM employees
                WHERE active = 1 AND (
                    employee_id LIKE ? OR first_name LIKE ? OR last_name LIKE ?
                    OR position LIKE ? OR location LIKE ? OR ghana_card_no LIKE ?
                    OR ssnit_no LIKE ? OR license_no LIKE ? OR company LIKE ?
                    OR category LIKE ? OR department LIKE ? OR service_status LIKE ?)
                ORDER BY id DESC
            """, (like,) * 12).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM employees WHERE active = 1 ORDER BY id DESC"
            ).fetchall()
        conn.close()
        return render_template("employees.html", employees=rows, q=term)

    @app.route("/employees/new", methods=["GET", "POST"])
    @login_required
    def employee_new():
        return employee_form(None)

    @app.route("/employees/<code>/edit", methods=["GET", "POST"])
    @login_required
    def employee_edit(code):
        emp = get_employee(code)
        if not emp:
            abort(404)
        return employee_form(emp)

    def employee_form(emp):
        editing = emp is not None
        if editing:
            values = {column: emp[column] or "" for column, _, kind, _ in EMPLOYEE_FORM
                      if kind != "section"}
            values["basic_salary"] = emp["basic_salary"] or 0
            code = emp["employee_id"]
        else:
            values = {column: EMPLOYEE_FORM_DEFAULTS.get(column, "")
                      for column, _, kind, options in EMPLOYEE_FORM if kind != "section"}
            for column, _, kind, options in EMPLOYEE_FORM:
                if kind == "radio":
                    values[column] = options[0]
            code = ""

        if request.method == "POST":
            errors = []
            if not editing:
                code = request.form.get("employee_id", "").strip()
                if not EMPLOYEE_CODE.match(code):
                    errors.append("Employee Code is required and may only use "
                                  "letters, numbers, - and _ (up to 30).")
            for column, label, kind, options in EMPLOYEE_FORM:
                if kind == "section":
                    continue
                value = request.form.get(column, "").strip()
                if kind in ("combo", "radio") and value and value not in options:
                    errors.append(f"Please choose a valid {label}.")
                if kind == "date" and not is_valid_date(value):
                    errors.append(f"{label} must be a valid date.")
                values[column] = value
            if not values["first_name"] or not values["last_name"]:
                errors.append("First Name and Last Name are required.")
            values["basic_salary"] = to_float(values["basic_salary"], "Basic Salary", errors)

            upload = request.files.get("photo")
            if upload and upload.filename and not upload.filename.lower().endswith(
                    (".jpg", ".jpeg", ".png")):
                errors.append("The photo must be a .jpg, .jpeg or .png picture.")

            if not errors:
                columns = list(values)
                conn = get_connection()
                try:
                    if editing:
                        conn.execute(f"""
                            UPDATE employees
                            SET {", ".join(f"{c} = ?" for c in columns)}
                            WHERE employee_id = ?
                        """, list(values.values()) + [code])
                    else:
                        conn.execute(f"""
                            INSERT INTO employees (employee_id, {", ".join(columns)})
                            VALUES ({", ".join("?" for _ in range(len(columns) + 1))})
                        """, [code] + list(values.values()))
                    conn.commit()
                except sqlite3.IntegrityError:
                    conn.close()
                    errors.append("That Employee Code already exists.")
                else:
                    conn.close()
                    save_photo_changes(code, emp, upload)
                    flash("Employee updated." if editing else "Employee added.", "success")
                    return redirect(url_for("employees"))

            for error in errors:
                flash(error, "error")

        return render_template("employee_form.html", emp=emp, code=code,
                               values=values, form=EMPLOYEE_FORM)

    def save_photo_changes(code, emp, upload):
        filename = None
        if upload and upload.filename:
            try:
                filename = save_photo(upload.stream, code, name=upload.filename)
            except PhotoError as error:
                flash(f"The employee was saved, but the photo was not: {error}", "warning")
                return
        elif emp and emp["photo"] and request.form.get("remove_photo"):
            delete_photo(emp["photo"])
        else:
            return
        conn = get_connection()
        conn.execute("UPDATE employees SET photo = ? WHERE employee_id = ?",
                     (filename, code))
        conn.commit()
        conn.close()

    @app.post("/employees/<code>/deactivate")
    @login_required
    def employee_deactivate(code):
        emp = get_employee(code)
        if not emp:
            abort(404)
        conn = get_connection()
        conn.execute("UPDATE employees SET active = 0 WHERE employee_id = ?", (code,))
        conn.commit()
        conn.close()
        flash(f"{emp['first_name']} {emp['last_name']} was deactivated.", "success")
        return redirect(url_for("employees"))

    @app.route("/employees/<code>/photo")
    @login_required
    def employee_photo(code):
        conn = get_connection()
        row = conn.execute("SELECT photo FROM employees WHERE employee_id = ?",
                           (code,)).fetchone()
        conn.close()
        if not row or not row["photo"]:
            abort(404)
        return send_from_directory(PHOTO_DIR, row["photo"], max_age=0)

    # ---- Attendance -------------------------------------------------------

    @app.route("/attendance", methods=["GET", "POST"])
    @login_required
    def attendance():
        if request.method == "POST":
            f = request.form
            code = f.get("employee_id", "")
            day = f.get("attendance_date") or date.today().isoformat()
            if not get_employee(code):
                flash("Please choose an employee.", "error")
            elif f.get("shift") not in SHIFTS or f.get("status") not in ATTENDANCE_STATUSES:
                flash("Please choose a shift and a status.", "error")
            elif not is_valid_date(day):
                flash("Please enter a valid date.", "error")
            else:
                conn = get_connection()
                conn.execute("""
                    INSERT INTO attendance
                        (employee_id, attendance_date, shift, check_in, check_out, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (code, day, f["shift"], f.get("check_in", ""),
                      f.get("check_out", ""), f["status"]))
                conn.commit()
                conn.close()
                flash("Attendance recorded.", "success")
                return redirect(url_for("attendance"))

        filter_code = request.args.get("employee", "")
        filter_date = request.args.get("date", "")
        where, params = [], []
        if filter_code:
            where.append("a.employee_id = ?")
            params.append(filter_code)
        if filter_date:
            where.append("a.attendance_date = ?")
            params.append(filter_date)
        conn = get_connection()
        rows = conn.execute(f"""
            SELECT a.*, e.first_name, e.last_name FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            {"WHERE " + " AND ".join(where) if where else ""}
            ORDER BY a.attendance_date DESC, a.id DESC LIMIT 300
        """, params).fetchall()
        conn.close()
        return render_template(
            "attendance.html", records=rows, employees=active_employees(),
            shifts=SHIFTS, statuses=ATTENDANCE_STATUSES, today=date.today().isoformat(),
            filter_code=filter_code, filter_date=filter_date)

    # ---- Leave ------------------------------------------------------------

    @app.route("/leave", methods=["GET", "POST"])
    @login_required
    def leave():
        if request.method == "POST":
            f = request.form
            code = f.get("employee_id", "")
            start, end = f.get("start_date", ""), f.get("end_date", "")
            days = calculate_days(start, end)
            if not get_employee(code):
                flash("Please choose an employee.", "error")
            elif f.get("leave_type") not in LEAVE_TYPES:
                flash("Please choose a leave type.", "error")
            elif days <= 0:
                flash("Please enter a valid date range.", "error")
            else:
                conn = get_connection()
                conn.execute("""
                    INSERT INTO leave_requests
                        (employee_id, leave_type, start_date, end_date, days, reason)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (code, f["leave_type"], start, end, days, f.get("reason", "").strip()))
                conn.commit()
                conn.close()
                flash(f"Leave request submitted for {days} day(s).", "success")
                return redirect(url_for("leave"))

        conn = get_connection()
        rows = conn.execute("""
            SELECT l.*, e.first_name, e.last_name FROM leave_requests l
            JOIN employees e ON l.employee_id = e.employee_id
            ORDER BY l.id DESC LIMIT 300
        """).fetchall()
        conn.close()
        return render_template("leave.html", requests=rows,
                               employees=active_employees(), leave_types=LEAVE_TYPES)

    @app.post("/leave/<int:request_id>/decide")
    @login_required
    def leave_decide(request_id):
        status = request.form.get("status")
        if status not in ("Approved", "Rejected"):
            abort(400)
        ok, message = decide_leave(request_id, status)
        flash(message, "success" if ok else "error")
        return redirect(url_for("leave"))

    # ---- Payroll ----------------------------------------------------------

    @app.route("/payroll", methods=["GET", "POST"])
    @login_required
    def payroll():
        if request.method == "POST":
            f = request.form
            emp = get_employee(f.get("employee_id", ""))
            errors = []
            allow = to_float(f.get("allowances"), "Allowances", errors)
            over = to_float(f.get("overtime"), "Overtime", errors)
            ded = to_float(f.get("deductions"), "Deductions", errors)
            month = f.get("month", "")
            if not emp:
                errors.append("Please choose an employee.")
            if not re.match(r"^\d{4}-\d{2}$", month):
                errors.append("Please choose the payroll month.")
            if not errors:
                basic = emp["basic_salary"] or 0
                net = basic + allow + over - ded
                conn = get_connection()
                conn.execute("""
                    INSERT INTO payroll (employee_id, month, basic_salary, allowances,
                                         overtime, deductions, net_salary)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (emp["employee_id"], month, basic, allow, over, ded, net))
                conn.commit()
                conn.close()
                flash(f"Payroll generated. Net salary: {net:,.2f}", "success")
                return redirect(url_for("payroll"))
            for error in errors:
                flash(error, "error")

        conn = get_connection()
        rows = conn.execute("""
            SELECT p.*, e.first_name, e.last_name FROM payroll p
            JOIN employees e ON p.employee_id = e.employee_id
            ORDER BY p.id DESC LIMIT 300
        """).fetchall()
        conn.close()
        return render_template("payroll.html", records=rows, employees=active_employees())

    # ---- Reports ----------------------------------------------------------

    @app.route("/reports")
    @login_required
    def reports():
        rows, totals = staff_summary()
        stage = request.args.get("stage", "1st Renewal")
        period = request.args.get("period", "Next 30 days")
        if stage not in LICENSE_STAGES:
            stage = "1st Renewal"
        if period not in EXPIRY_PERIODS:
            period = "Next 30 days"
        return render_template(
            "reports.html", rows=rows, totals=totals, kinds=EMPLOYMENT_TYPES,
            stage=stage, period=period, stages=list(LICENSE_STAGES),
            periods=list(EXPIRY_PERIODS), licenses=license_expiry(stage, period))

    # ---- Export to Excel --------------------------------------------------

    @app.route("/export")
    @login_required
    def export_excel():
        if not excel_available():
            flash(OPENPYXL_MISSING, "error")
            return redirect(url_for("dashboard"))
        response = send_file(
            io.BytesIO(workbook_bytes()),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True, download_name=default_filename(), max_age=0)
        # Staff records: never keep a copy in a browser or proxy cache.
        response.headers["Cache-Control"] = "no-store"
        return response

    # ---- Users ------------------------------------------------------------

    @app.route("/users", methods=["GET", "POST"])
    @login_required
    def users():
        if request.method == "POST":
            error = create_user(request.form.get("username"), request.form.get("password"))
            if error:
                flash(error, "error")
            else:
                flash("User added.", "success")
                return redirect(url_for("users"))
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, username, created_at FROM users ORDER BY username").fetchall()
        conn.close()
        return render_template("users.html", users=rows)

    @app.post("/users/<int:user_id>/delete")
    @login_required
    def user_delete(user_id):
        if user_id == g.user["id"]:
            flash("You can't remove your own account.", "error")
        else:
            conn = get_connection()
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            conn.close()
            flash("User removed.", "success")
        return redirect(url_for("users"))

    @app.route("/account", methods=["GET", "POST"])
    @login_required
    def account():
        if request.method == "POST":
            if request.form.get("password") != request.form.get("confirm"):
                flash("The two passwords don't match.", "error")
            else:
                error = set_password(g.user["id"], request.form.get("password"))
                flash(error or "Password changed.", "error" if error else "success")
                if not error:
                    return redirect(url_for("dashboard"))
        return render_template("account.html")

    @app.errorhandler(413)
    def too_large(_error):
        flash("That file is too big (8 MB maximum).", "error")
        return redirect(request.path)


app = create_app()
