"""Tkinter graphical interface for the HR Management System.

This gives the application a desktop GUI styled after a classic
"Employee Data Form": an orange header banner, left-aligned field
labels with entry boxes, radio buttons for the location, and a Submit
button. The same look is carried across every module (Employees,
Attendance, Leave, Payroll), a Dashboard summary and a Reports tab
(staff numbers by location and licence expiry).

All data still lives in the same SQLite database used by the terminal
version, so the two front-ends stay fully compatible.

Run with:  python hr_system.py
"""

import os
import sqlite3
import subprocess
import sys
from datetime import date
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    StringVar,
    Tk,
    X,
    Y,
    filedialog,
    messagebox,
    ttk,
)
import tkinter as tk

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
from hr.database import get_connection, setup_database
from hr.export import (
    OPENPYXL_MISSING,
    default_filename,
    excel_available,
    export_to_excel,
)
from hr.photos import (
    PILLOW_AVAILABLE,
    PILLOW_MISSING,
    PhotoError,
    delete_photo,
    initials,
    load_logo,
    load_thumbnail,
    make_avatar,
    photo_path,
    save_photo,
)
from hr.reports import license_expiry, licenses_due_count, staff_summary
from hr.utils import calculate_days, get_employee, is_valid_date

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

ORANGE = "#C0501E"          # header banner (matches the reference form)
ORANGE_DARK = "#9E3F16"
PAGE_BG = "#EFE9E6"         # soft neutral page background
CARD_BG = "#FDFDFD"         # form card background
FIELD_BG = "#E9E9E9"        # entry field fill, like the reference form
BORDER = "#C98B76"
TEXT = "#2A2A2A"
MUTED = "#7A7A7A"

FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_HEADER = ("Segoe UI", 13, "bold")


def _style():
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure("TFrame", background=PAGE_BG)
    style.configure("Card.TFrame", background=CARD_BG)
    style.configure("TLabel", background=CARD_BG, foreground=TEXT, font=FONT)
    style.configure("Page.TLabel", background=PAGE_BG, foreground=TEXT, font=FONT)
    style.configure("Field.TLabel", background=CARD_BG, foreground=TEXT, font=FONT_BOLD)
    style.configure("Muted.TLabel", background=PAGE_BG, foreground=MUTED, font=FONT)

    style.configure(
        "TEntry",
        fieldbackground=FIELD_BG,
        background=FIELD_BG,
        bordercolor=BORDER,
        relief="solid",
        padding=5,
    )
    style.configure("TCombobox", fieldbackground=FIELD_BG, padding=4)
    style.configure("Card.TRadiobutton", background=CARD_BG, font=FONT)

    style.configure(
        "Submit.TButton",
        background=ORANGE,
        foreground="white",
        font=FONT_BOLD,
        padding=(18, 8),
        borderwidth=0,
    )
    style.map(
        "Submit.TButton",
        background=[("active", ORANGE_DARK)],
        foreground=[("active", "white")],
    )

    style.configure(
        "Ghost.TButton",
        background=CARD_BG,
        foreground=ORANGE,
        font=FONT_BOLD,
        padding=(14, 6),
    )
    style.map("Ghost.TButton", background=[("active", PAGE_BG)])

    style.configure(
        "Treeview",
        background="white",
        fieldbackground="white",
        rowheight=26,
        font=FONT,
    )
    style.configure(
        "Treeview.Heading",
        background=ORANGE,
        foreground="white",
        font=FONT_BOLD,
    )
    style.map("Treeview.Heading", background=[("active", ORANGE_DARK)])
    # Taller rows for the employee list so the photos fit.
    style.configure("Employees.Treeview", rowheight=44)

    return style


# ---------------------------------------------------------------------------
# Reusable widgets
# ---------------------------------------------------------------------------


class FormCard(ttk.Frame):
    """A titled card with an orange header, styled like the reference form."""

    def __init__(self, master, title):
        super().__init__(master, style="Card.TFrame")
        self.configure(padding=0)

        outer = tk.Frame(self, background=BORDER, padx=2, pady=2)
        outer.pack(fill=BOTH, expand=True)

        inner = tk.Frame(outer, background=CARD_BG)
        inner.pack(fill=BOTH, expand=True)

        header = tk.Frame(inner, background=ORANGE)
        header.pack(fill=X)
        tk.Label(
            header,
            text=title,
            background=ORANGE,
            foreground="white",
            font=FONT_HEADER,
            anchor="w",
            padx=16,
            pady=10,
        ).pack(fill=X)

        self.body = tk.Frame(inner, background=CARD_BG, padx=18, pady=18)
        self.body.pack(fill=BOTH, expand=True)
        self.body.columnconfigure(1, weight=1)
        self._row = 0

    def add_field(self, label, width=32):
        """Add a labelled entry row and return the Entry widget."""
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(
            row=self._row, column=0, sticky="e", padx=(0, 12), pady=8
        )
        entry = ttk.Entry(self.body, width=width, font=FONT)
        entry.grid(row=self._row, column=1, sticky="we", pady=8)
        self._row += 1
        return entry

    def add_section(self, title):
        """Add a small heading that groups the rows below it."""
        tk.Label(
            self.body, text=title, background=CARD_BG, foreground=ORANGE,
            font=FONT_BOLD, anchor="w",
        ).grid(row=self._row, column=0, columnspan=2, sticky="we", pady=(12, 2))
        self._row += 1

    def add_row(self, label):
        """Add a labelled row and return an empty frame to fill."""
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(
            row=self._row, column=0, sticky="ne", padx=(0, 12), pady=8
        )
        holder = tk.Frame(self.body, background=CARD_BG)
        holder.grid(row=self._row, column=1, sticky="w", pady=8)
        self._row += 1
        return holder

    def add_combo(self, label, values, width=30):
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(
            row=self._row, column=0, sticky="e", padx=(0, 12), pady=8
        )
        var = StringVar()
        combo = ttk.Combobox(
            self.body, textvariable=var, values=values, width=width, font=FONT,
            state="readonly",
        )
        combo.grid(row=self._row, column=1, sticky="we", pady=8)
        self._row += 1
        return var

    def add_radio(self, label, options, default=None):
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(
            row=self._row, column=0, sticky="e", padx=(0, 12), pady=8
        )
        holder = tk.Frame(self.body, background=CARD_BG)
        holder.grid(row=self._row, column=1, sticky="w", pady=8)
        var = StringVar(value=default or options[0])
        for opt in options:
            ttk.Radiobutton(
                holder, text=opt, value=opt, variable=var,
                style="Card.TRadiobutton",
            ).pack(side=LEFT, padx=(0, 18))
        self._row += 1
        return var

    def add_submit(self, text, command):
        btn = ttk.Button(self.body, text=text, style="Submit.TButton", command=command)
        btn.grid(row=self._row, column=1, sticky="e", pady=(14, 0))
        self._row += 1
        return btn


def scrollable_area(master):
    """Return ``(outer, inner)`` where ``inner`` scrolls vertically.

    Build the tab's content inside ``inner`` and add ``outer`` to the
    notebook. When the content is taller than the window, a scrollbar
    appears and the mouse wheel scrolls it.
    """
    outer = ttk.Frame(master)
    canvas = tk.Canvas(outer, background=PAGE_BG, highlightthickness=0)
    vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    vsb.pack(side=RIGHT, fill=Y)

    inner = ttk.Frame(canvas)
    window = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _on_inner_configure(_event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_canvas_configure(event):
        # Keep the inner frame as wide as the visible canvas.
        canvas.itemconfigure(window, width=event.width)

    inner.bind("<Configure>", _on_inner_configure)
    canvas.bind("<Configure>", _on_canvas_configure)

    def _wheel(event):
        if event.num == 4:                       # Linux wheel up
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:                     # Linux wheel down
            canvas.yview_scroll(1, "units")
        else:                                    # Windows / macOS
            canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _bind_wheel(_event):
        canvas.bind_all("<MouseWheel>", _wheel)
        canvas.bind_all("<Button-4>", _wheel)
        canvas.bind_all("<Button-5>", _wheel)

    def _unbind_wheel(_event):
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    canvas.bind("<Enter>", _bind_wheel)
    canvas.bind("<Leave>", _unbind_wheel)

    return outer, inner


def make_tree(master, columns, widths=None, hscroll=False):
    """Create a Treeview with scrollbars inside ``master``.

    With ``hscroll`` the columns keep their widths and a horizontal
    scrollbar appears when they don't all fit.
    """
    frame = ttk.Frame(master)
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=12)
    widths = widths or {}
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=widths.get(col, 120), anchor="w",
                    stretch=not hscroll)
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    if hscroll:
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=hsb.set)
        hsb.grid(row=1, column=0, sticky="we")
    return frame, tree


def open_file(path):
    """Open a file with the computer's usual program (e.g. Excel)."""
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def export_to_excel_dialog(parent):
    """Ask where to save, write the Excel workbook, then offer to open it."""
    if not excel_available():
        messagebox.showwarning("Export to Excel", OPENPYXL_MISSING, parent=parent)
        return
    path = filedialog.asksaveasfilename(
        parent=parent, title="Export to Excel", defaultextension=".xlsx",
        initialfile=default_filename(), filetypes=[("Excel workbook", "*.xlsx")])
    if not path:
        return
    try:
        export_to_excel(path)
    except PermissionError:
        messagebox.showerror(
            "Export to Excel",
            "Could not save the file. If it is open in Excel, close it and try again.",
            parent=parent)
        return
    except OSError as error:
        messagebox.showerror("Export to Excel", f"Could not save the file:\n{error}",
                             parent=parent)
        return
    if messagebox.askyesno("Exported", f"Saved to:\n{path}\n\nOpen it now?",
                           parent=parent):
        try:
            open_file(path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------


class DashboardTab(ttk.Frame):
    def __init__(self, master):
        super().__init__(master, padding=24)
        self.cards = {}

        header = ttk.Frame(self)
        header.pack(fill=X, pady=(0, 16))
        ttk.Label(header, text="Dashboard", style="Page.TLabel",
                  font=FONT_TITLE).pack(side=LEFT)
        ttk.Button(header, text="Refresh", style="Ghost.TButton",
                   command=self.refresh).pack(side=RIGHT)
        ttk.Button(header, text="Export to Excel", style="Submit.TButton",
                   command=lambda: export_to_excel_dialog(self)).pack(side=RIGHT, padx=(0, 8))

        row = ttk.Frame(self)
        row.pack(fill=X)
        specs = [
            ("Active Employees", "#C0501E"),
            ("Attendance Today", "#2E7D5B"),
            ("Pending Leave", "#B4881C"),
            ("Payroll Records", "#3A5A8C"),
            ("Licenses Due (30 days)", "#7A3E8C"),
        ]
        for i, (title, color) in enumerate(specs):
            row.columnconfigure(i, weight=1)
            card = tk.Frame(row, background=color)
            card.grid(row=0, column=i, sticky="we", padx=6, ipady=14)
            value = tk.Label(card, text="0", background=color, foreground="white",
                             font=("Segoe UI", 26, "bold"))
            value.pack()
            tk.Label(card, text=title, background=color, foreground="white",
                     font=FONT).pack(pady=(2, 0))
            self.cards[title] = value

        # Company logo, centred under the stats. If it can't be shown, say
        # why on screen instead of leaving an unexplained gap.
        self._logo, problem = load_logo((320, 320), PAGE_BG)
        if self._logo:
            tk.Label(self, image=self._logo, background=PAGE_BG).pack(pady=(32, 0))
        else:
            print(problem)
            ttk.Label(self, text=problem, style="Muted.TLabel",
                      justify="center").pack(pady=(32, 0))

    def refresh(self):
        conn = get_connection()
        today = date.today().isoformat()
        stats = {
            "Active Employees": conn.execute(
                "SELECT COUNT(*) FROM employees WHERE active = 1").fetchone()[0],
            "Attendance Today": conn.execute(
                "SELECT COUNT(*) FROM attendance WHERE attendance_date = ?",
                (today,)).fetchone()[0],
            "Pending Leave": conn.execute(
                "SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'"
            ).fetchone()[0],
            "Payroll Records": conn.execute(
                "SELECT COUNT(*) FROM payroll").fetchone()[0],
            "Licenses Due (30 days)": licenses_due_count(30),
        }
        conn.close()
        for key, value in stats.items():
            self.cards[key].configure(text=str(value))


class EmployeesTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self.editing_id = None

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---- Employee Data Form (left) -------------------------------
        form = FormCard(self, "Employee Data Form")
        form.grid(row=0, column=0, sticky="n", padx=(0, 20))
        self.form = form

        self.f_code = form.add_field("Employee Code")

        # ---- Profile picture ----
        # The picked file is only copied into the photos folder on Submit.
        self.photo_source = None      # new picture chosen on the form
        self.photo_removed = False    # "Remove" pressed while editing
        self.photo_current = None     # file name already saved for this employee
        self._photo_image = None      # keep a reference so Tk shows it

        holder = form.add_row("Photo")
        self.photo_label = tk.Label(
            holder, text="No photo", background=FIELD_BG, foreground=MUTED,
            font=FONT, width=14, height=7, relief="solid", borderwidth=1)
        self.photo_label.pack(side=LEFT)
        photo_btns = tk.Frame(holder, background=CARD_BG)
        photo_btns.pack(side=LEFT, padx=(12, 0), anchor="n")
        ttk.Button(photo_btns, text="Choose Photo…", style="Ghost.TButton",
                   command=self.choose_photo).pack(fill=X)
        ttk.Button(photo_btns, text="Remove", style="Ghost.TButton",
                   command=self.remove_photo).pack(fill=X, pady=(6, 0))
        tk.Label(photo_btns, text="JPG, JPEG or PNG", background=CARD_BG,
                 foreground=MUTED, font=("Segoe UI", 9)).pack(pady=(6, 0))

        # column -> (kind, widget or StringVar, options)
        self.fields = {}
        for column, label, kind, options in EMPLOYEE_FORM:
            if kind == "section":
                form.add_section(label)
            elif kind == "combo":
                self.fields[column] = (kind, form.add_combo(label, options), options)
            elif kind == "radio":
                self.fields[column] = (kind, form.add_radio(label, options), options)
            elif kind == "date":
                self.fields[column] = (
                    kind, form.add_field(f"{label} (YYYY-MM-DD)"), None)
            else:
                self.fields[column] = (kind, form.add_field(label), None)

        btns = tk.Frame(form.body, background=CARD_BG)
        btns.grid(row=99, column=1, sticky="e", pady=(16, 0))
        ttk.Button(btns, text="Clear", style="Ghost.TButton",
                   command=self.clear_form).pack(side=LEFT, padx=(0, 8))
        self.submit_btn = ttk.Button(btns, text="Submit", style="Submit.TButton",
                                     command=self.submit)
        self.submit_btn.pack(side=LEFT)

        # ---- Employee list (right) -----------------------------------
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Employees", style="Page.TLabel",
                  font=FONT_HEADER).grid(row=0, column=0, sticky="w")

        search_row = ttk.Frame(right)
        search_row.grid(row=1, column=0, sticky="we", pady=8)
        self.search = ttk.Entry(search_row, font=FONT, width=28)
        self.search.pack(side=LEFT)
        self.search.bind("<Return>", lambda e: self.load())
        ttk.Button(search_row, text="Search", style="Ghost.TButton",
                   command=self.load).pack(side=LEFT, padx=6)
        ttk.Button(search_row, text="Show All", style="Ghost.TButton",
                   command=self.show_all).pack(side=LEFT)

        cols = ("Code", "Name", "Date of Birth", "Designation", "Category",
                "Staff Status", "Company", "Service Status", "Location",
                "Contact", "License Expiry")
        tree_frame, self.tree = make_tree(
            right, cols,
            {"Code": 70, "Name": 150, "Date of Birth": 100, "Designation": 230,
             "Category": 80, "Staff Status": 95, "Company": 90,
             "Service Status": 105, "Location": 80, "Contact": 100,
             "License Expiry": 105},
            hscroll=True,
        )
        # Show the tree column (#0) too: it holds each employee's photo.
        self.tree.configure(style="Employees.Treeview", show=("tree", "headings"))
        self.tree.heading("#0", text="Photo")
        self.tree.column("#0", width=64, minwidth=64, stretch=False, anchor="center")
        self._row_images = {}   # employee code -> image (Tk needs a reference)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        action_row = ttk.Frame(right)
        action_row.grid(row=3, column=0, sticky="we", pady=8)
        ttk.Button(action_row, text="Load for Edit", style="Ghost.TButton",
                   command=self.load_for_edit).pack(side=LEFT, padx=(0, 8))
        ttk.Button(action_row, text="Deactivate", style="Ghost.TButton",
                   command=self.deactivate).pack(side=LEFT)

        preview = ttk.Frame(right)
        preview.grid(row=4, column=0, sticky="w", pady=(4, 0))
        self._preview_image = None
        self.preview_photo = tk.Label(preview, background=PAGE_BG)
        self.preview_photo.pack(side=LEFT)
        self.preview_text = ttk.Label(preview, text="", style="Page.TLabel",
                                      justify=LEFT)
        self.preview_text.pack(side=LEFT, padx=12)

        self.clear_form()
        self.load()

    # -- helpers -------------------------------------------------------
    def _get(self, column):
        kind, widget, _options = self.fields[column]
        return widget.get().strip()

    def _set(self, column, value):
        kind, widget, options = self.fields[column]
        if kind in ("combo", "radio"):
            widget.set(value or (options[0] if kind == "radio" else ""))
        else:
            widget.delete(0, END)
            widget.insert(0, value or "")

    def clear_form(self):
        self.editing_id = None
        self.f_code.configure(state="normal")
        self.f_code.delete(0, END)
        for column in self.fields:
            self._set(column, EMPLOYEE_FORM_DEFAULTS.get(column, ""))
        self.photo_source = None
        self.photo_removed = False
        self.photo_current = None
        self._show_form_photo(None)
        self.submit_btn.configure(text="Submit")

    # -- profile picture -------------------------------------------------
    def _show_form_photo(self, path):
        self._photo_image = load_thumbnail(path, (120, 120))
        if self._photo_image:
            self.photo_label.configure(image=self._photo_image, text="",
                                       width=120, height=120)
        else:
            self.photo_label.configure(image="", text="No photo",
                                       width=14, height=7)

    def choose_photo(self):
        path = filedialog.askopenfilename(
            title="Choose a profile picture",
            filetypes=[("Pictures", "*.jpg *.jpeg *.png *.JPG *.JPEG *.PNG"),
                       ("JPEG", "*.jpg *.jpeg *.JPG *.JPEG"),
                       ("PNG", "*.png *.PNG")])
        if not path:
            return
        if not path.lower().endswith((".jpg", ".jpeg", ".png")):
            messagebox.showwarning("Photo", "Please choose a .jpg, .jpeg or .png picture.")
            return
        if not PILLOW_AVAILABLE:
            messagebox.showwarning("Photo", PILLOW_MISSING)
            return
        if load_thumbnail(path, (120, 120)) is None:
            messagebox.showwarning("Photo", "That file is not a picture that can be opened.")
            return
        self.photo_source = path
        self.photo_removed = False
        self._show_form_photo(path)

    def remove_photo(self):
        self.photo_source = None
        self.photo_removed = bool(self.photo_current)
        self._show_form_photo(None)

    def _save_photo_changes(self, code):
        """Apply a chosen or removed picture after the employee is saved."""
        if self.photo_source:
            filename = save_photo(self.photo_source, code)
        elif self.photo_removed:
            delete_photo(self.photo_current)
            filename = None
        else:
            return
        conn = get_connection()
        conn.execute("UPDATE employees SET photo = ? WHERE employee_id = ?",
                     (filename, code))
        conn.commit()
        conn.close()

    def submit(self):
        code = self.f_code.get().strip()
        values = {column: self._get(column) for column in self.fields}
        if not code or not values["first_name"] or not values["last_name"]:
            messagebox.showwarning(
                "Missing data", "Employee Code, First Name and Last Name are required.")
            return

        try:
            values["basic_salary"] = float(values["basic_salary"] or 0)
        except ValueError:
            messagebox.showwarning("Invalid salary", "Basic Salary must be a number.")
            return

        for column, label, kind, _options in EMPLOYEE_FORM:
            if kind == "date" and not is_valid_date(values[column]):
                messagebox.showwarning(
                    "Invalid date", f"{label} must be in YYYY-MM-DD format.")
                return

        columns = list(values)
        conn = get_connection()
        try:
            if self.editing_id:
                conn.execute(f"""
                    UPDATE employees
                    SET {", ".join(f"{c} = ?" for c in columns)}
                    WHERE employee_id = ?
                """, list(values.values()) + [self.editing_id])
                conn.commit()
                messagebox.showinfo("Saved", "Employee updated successfully.")
            else:
                conn.execute(f"""
                    INSERT INTO employees (employee_id, {", ".join(columns)})
                    VALUES ({", ".join("?" for _ in range(len(columns) + 1))})
                """, [code] + list(values.values()))
                conn.commit()
                messagebox.showinfo("Saved", "Employee added successfully.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", "That Employee Code already exists.")
            return
        finally:
            conn.close()

        try:
            self._save_photo_changes(self.editing_id or code)
        except PhotoError as error:
            messagebox.showwarning(
                "Photo", f"The employee was saved, but the photo was not.\n\n{error}")

        self.clear_form()
        self.load()
        self.app.dashboard.refresh()

    def load(self):
        term = self.search.get().strip()
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

        self.tree.delete(*self.tree.get_children())
        self._row_images = {}
        for r in rows:
            avatar = make_avatar(r["photo"], r["first_name"], r["last_name"],
                                 size=36, key=r["employee_id"])
            self._row_images[r["employee_id"]] = avatar
            # Without Pillow there is no image, so fall back to plain initials.
            picture = {"image": avatar} if avatar else {
                "text": initials(r["first_name"], r["last_name"])}
            self.tree.insert("", END, iid=r["employee_id"], **picture, values=(
                r["employee_id"],
                f"{r['first_name']} {r['last_name']}",
                r["date_of_birth"] or "",
                r["position"] or "",
                r["category"] or "",
                r["employment_type"] or "",
                r["company"] or "",
                r["service_status"] or "",
                r["location"] or "",
                r["phone"] or "",
                r["license_expiry"] or "",
            ))

    def show_all(self):
        self.search.delete(0, END)
        self.load()

    def on_select(self, _event):
        sel = self.tree.selection()
        emp = get_employee(sel[0]) if sel else None
        if not emp:
            self._preview_image = None
            self.preview_photo.configure(image="")
            self.preview_text.configure(text="")
            return
        self._preview_image = make_avatar(
            emp["photo"], emp["first_name"], emp["last_name"],
            size=72, key=emp["employee_id"])
        self.preview_photo.configure(image=self._preview_image or "")
        self.preview_text.configure(text=(
            f"{emp['first_name']} {emp['last_name']}  ({emp['employee_id']})\n"
            f"{emp['position'] or ''}  •  {emp['category'] or ''}  •  "
            f"{emp['location'] or ''}\n"
            f"{emp['employment_type'] or ''}  •  {emp['company'] or ''}  •  "
            f"{emp['service_status'] or ''}\n"
            f"Date of Birth: {emp['date_of_birth'] or '-'}"))

    def _selected_code(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select an employee from the list.")
            return None
        return sel[0]

    def load_for_edit(self):
        code = self._selected_code()
        if not code:
            return
        emp = get_employee(code)
        if not emp:
            return
        self.clear_form()
        self.editing_id = code
        self.f_code.insert(0, emp["employee_id"])
        self.f_code.configure(state="disabled")
        for column in self.fields:
            value = emp[column]
            if column == "basic_salary":
                value = str(value or 0)
            self._set(column, value)
        self.photo_current = emp["photo"]
        self._show_form_photo(photo_path(emp["photo"]))
        self.submit_btn.configure(text="Update")

    def deactivate(self):
        code = self._selected_code()
        if not code:
            return
        emp = get_employee(code)
        if not emp:
            return
        if not messagebox.askyesno(
                "Confirm",
                f"Deactivate {emp['first_name']} {emp['last_name']} ({code})?"):
            return
        conn = get_connection()
        conn.execute("UPDATE employees SET active = 0 WHERE employee_id = ?", (code,))
        conn.commit()
        conn.close()
        self.load()
        self.app.dashboard.refresh()


class AttendanceTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        form = FormCard(self, "Record Attendance")
        form.grid(row=0, column=0, sticky="n", padx=(0, 20))
        self.f_emp = form.add_field("Employee Code")
        self.f_date = form.add_field("Date (YYYY-MM-DD)")
        self.f_date.insert(0, date.today().isoformat())
        self.f_shift = form.add_combo("Shift", SHIFTS)
        self.f_shift.set(SHIFTS[0])
        self.f_in = form.add_field("Check-in (HH:MM)")
        self.f_out = form.add_field("Check-out (HH:MM)")
        self.f_status = form.add_combo("Status", ATTENDANCE_STATUSES)
        self.f_status.set(ATTENDANCE_STATUSES[0])
        form.add_submit("Submit", self.submit)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Attendance Records", style="Page.TLabel",
                  font=FONT_HEADER).grid(row=0, column=0, sticky="w", pady=(0, 8))
        cols = ("Date", "Code", "Name", "Shift", "In", "Out", "Status")
        tree_frame, self.tree = make_tree(
            right, cols,
            {"Date": 100, "Code": 80, "Name": 160, "Shift": 90, "In": 70,
             "Out": 70, "Status": 90})
        tree_frame.grid(row=1, column=0, sticky="nsew")
        self.load()

    def submit(self):
        code = self.f_emp.get().strip()
        if not get_employee(code):
            messagebox.showwarning("Not found", "Employee not found.")
            return
        status = self.f_status.get()
        if not status:
            messagebox.showwarning("Status", "Please choose a status.")
            return
        attendance_date = self.f_date.get().strip() or date.today().isoformat()
        if not is_valid_date(attendance_date):
            messagebox.showwarning("Date", "Date must be in YYYY-MM-DD format.")
            return
        conn = get_connection()
        conn.execute("""
            INSERT INTO attendance
                (employee_id, attendance_date, shift, check_in, check_out, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, attendance_date, self.f_shift.get(),
              self.f_in.get().strip(), self.f_out.get().strip(), status))
        conn.commit()
        conn.close()
        messagebox.showinfo("Saved", "Attendance recorded.")
        self.load()
        self.app.dashboard.refresh()

    def load(self):
        conn = get_connection()
        rows = conn.execute("""
            SELECT a.*, e.first_name, e.last_name FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            ORDER BY a.attendance_date DESC, a.id DESC
        """).fetchall()
        conn.close()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", END, values=(
                r["attendance_date"], r["employee_id"],
                f"{r['first_name']} {r['last_name']}", r["shift"] or "",
                r["check_in"] or "", r["check_out"] or "", r["status"]))


class LeaveTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        form = FormCard(self, "Leave Request")
        form.grid(row=0, column=0, sticky="n", padx=(0, 20))
        self.f_emp = form.add_field("Employee Code")
        self.f_type = form.add_combo("Leave Type", LEAVE_TYPES)
        self.f_type.set(LEAVE_TYPES[0])
        self.f_start = form.add_field("Start Date (YYYY-MM-DD)")
        self.f_end = form.add_field("End Date (YYYY-MM-DD)")
        self.f_reason = form.add_field("Reason")
        form.add_submit("Submit", self.submit)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Leave Requests", style="Page.TLabel",
                  font=FONT_HEADER).grid(row=0, column=0, sticky="w", pady=(0, 8))
        cols = ("ID", "Code", "Name", "Type", "Start", "End", "Days", "Status")
        tree_frame, self.tree = make_tree(
            right, cols,
            {"ID": 40, "Code": 70, "Name": 140, "Type": 110, "Start": 90,
             "End": 90, "Days": 50, "Status": 80})
        tree_frame.grid(row=1, column=0, sticky="nsew")

        action = ttk.Frame(right)
        action.grid(row=2, column=0, sticky="we", pady=8)
        ttk.Button(action, text="Approve", style="Ghost.TButton",
                   command=lambda: self.decide("Approved")).pack(side=LEFT, padx=(0, 8))
        ttk.Button(action, text="Reject", style="Ghost.TButton",
                   command=lambda: self.decide("Rejected")).pack(side=LEFT)
        self.load()

    def submit(self):
        code = self.f_emp.get().strip()
        if not get_employee(code):
            messagebox.showwarning("Not found", "Employee not found.")
            return
        days = calculate_days(self.f_start.get().strip(), self.f_end.get().strip())
        if days <= 0:
            messagebox.showwarning("Dates", "Please enter a valid date range.")
            return
        conn = get_connection()
        conn.execute("""
            INSERT INTO leave_requests
                (employee_id, leave_type, start_date, end_date, days, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (code, self.f_type.get(), self.f_start.get().strip(),
              self.f_end.get().strip(), days, self.f_reason.get().strip()))
        conn.commit()
        conn.close()
        messagebox.showinfo("Submitted", f"Leave request submitted for {days} day(s).")
        self.load()
        self.app.dashboard.refresh()

    def load(self):
        conn = get_connection()
        rows = conn.execute("""
            SELECT l.*, e.first_name, e.last_name FROM leave_requests l
            JOIN employees e ON l.employee_id = e.employee_id
            ORDER BY l.id DESC
        """).fetchall()
        conn.close()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", END, iid=str(r["id"]), values=(
                r["id"], r["employee_id"],
                f"{r['first_name']} {r['last_name']}", r["leave_type"],
                r["start_date"], r["end_date"], r["days"], r["status"]))

    def decide(self, status):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Select a leave request first.")
            return
        request_id = int(sel[0])
        conn = get_connection()
        req = conn.execute(
            "SELECT * FROM leave_requests WHERE id = ?", (request_id,)).fetchone()
        if req["status"] != "Pending":
            messagebox.showinfo("Processed", "This request was already processed.")
            conn.close()
            return

        if status == "Approved" and req["leave_type"] in ("Annual", "Sick"):
            column = "annual_leave" if req["leave_type"] == "Annual" else "sick_leave"
            emp = conn.execute(
                f"SELECT {column} FROM employees WHERE employee_id = ?",
                (req["employee_id"],)).fetchone()
            if emp[column] < req["days"]:
                messagebox.showwarning(
                    "Balance", f"Not enough {req['leave_type'].lower()} leave.")
                conn.close()
                return
            conn.execute(
                f"UPDATE employees SET {column} = {column} - ? WHERE employee_id = ?",
                (req["days"], req["employee_id"]))

        conn.execute("UPDATE leave_requests SET status = ? WHERE id = ?",
                     (status, request_id))
        conn.commit()
        conn.close()
        self.load()
        self.app.dashboard.refresh()


class PayrollTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        form = FormCard(self, "Generate Payroll")
        form.grid(row=0, column=0, sticky="n", padx=(0, 20))
        self.f_emp = form.add_field("Employee Code")
        self.f_month = form.add_field("Month (YYYY-MM)")
        self.f_allow = form.add_field("Allowances")
        self.f_over = form.add_field("Overtime")
        self.f_ded = form.add_field("Deductions")
        form.add_submit("Submit", self.submit)

        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Payroll History", style="Page.TLabel",
                  font=FONT_HEADER).grid(row=0, column=0, sticky="w", pady=(0, 8))
        cols = ("Code", "Name", "Month", "Basic", "Allow", "OT", "Deduct", "Net")
        tree_frame, self.tree = make_tree(
            right, cols,
            {"Code": 70, "Name": 150, "Month": 80, "Basic": 90, "Allow": 80,
             "OT": 70, "Deduct": 80, "Net": 90})
        tree_frame.grid(row=1, column=0, sticky="nsew")
        self.load()

    def submit(self):
        code = self.f_emp.get().strip()
        emp = get_employee(code)
        if not emp:
            messagebox.showwarning("Not found", "Employee not found.")
            return
        try:
            allow = float(self.f_allow.get().strip() or 0)
            over = float(self.f_over.get().strip() or 0)
            ded = float(self.f_ded.get().strip() or 0)
        except ValueError:
            messagebox.showwarning("Invalid", "Amounts must be numbers.")
            return
        basic = emp["basic_salary"]
        net = basic + allow + over - ded
        conn = get_connection()
        conn.execute("""
            INSERT INTO payroll
                (employee_id, month, basic_salary, allowances, overtime,
                 deductions, net_salary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (code, self.f_month.get().strip(), basic, allow, over, ded, net))
        conn.commit()
        conn.close()
        messagebox.showinfo("Done", f"Payroll generated. Net salary: {net:.2f}")
        self.load()
        self.app.dashboard.refresh()

    def load(self):
        conn = get_connection()
        rows = conn.execute("""
            SELECT p.*, e.first_name, e.last_name FROM payroll p
            JOIN employees e ON p.employee_id = e.employee_id
            ORDER BY p.id DESC
        """).fetchall()
        conn.close()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", END, values=(
                r["employee_id"], f"{r['first_name']} {r['last_name']}",
                r["month"], f"{r['basic_salary']:.2f}", f"{r['allowances']:.2f}",
                f"{r['overtime']:.2f}", f"{r['deductions']:.2f}",
                f"{r['net_salary']:.2f}"))


class ReportsTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=20)
        self.app = app
        self.columnconfigure(1, weight=1)

        # ---- Staff report (top) --------------------------------------
        staff = FormCard(self, "Staff Report")
        staff.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 20))
        body = staff.body

        cards = tk.Frame(body, background=CARD_BG)
        cards.grid(row=0, column=0, columnspan=2, sticky="we")
        self.totals = {}
        colors = ["#C0501E", "#B4881C", "#3A5A8C"]
        specs = [(kind, f"Total {kind} Staff", colors[i % len(colors)])
                 for i, kind in enumerate(EMPLOYMENT_TYPES)]
        specs.append(("Total", "Total Staff", "#2E7D5B"))
        for i, (key, title, color) in enumerate(specs):
            cards.columnconfigure(i, weight=1)
            card = tk.Frame(cards, background=color)
            card.grid(row=0, column=i, sticky="we", padx=6, ipady=10)
            value = tk.Label(card, text="0", background=color, foreground="white",
                             font=("Segoe UI", 22, "bold"))
            value.pack()
            tk.Label(card, text=title, background=color, foreground="white",
                     font=FONT).pack()
            self.totals[key] = value

        tree_frame, self.staff_tree = make_tree(
            body, ("Location", *EMPLOYMENT_TYPES, "Total"),
            {"Location": 160, **{kind: 110 for kind in EMPLOYMENT_TYPES},
             "Total": 110})
        self.staff_tree.configure(height=6)
        tree_frame.grid(row=1, column=0, columnspan=2, sticky="we", pady=(14, 0))

        report_btns = tk.Frame(body, background=CARD_BG)
        report_btns.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(report_btns, text="Refresh", style="Ghost.TButton",
                   command=self.refresh).pack(side=LEFT, padx=(0, 8))
        ttk.Button(report_btns, text="Export to Excel", style="Submit.TButton",
                   command=lambda: export_to_excel_dialog(self)).pack(side=LEFT)

        # ---- Licence expiry (bottom) ---------------------------------
        lic = FormCard(self, "License Expiry")
        lic.grid(row=1, column=0, sticky="n", padx=(0, 20))
        self.f_stage = lic.add_radio("Expiring", list(LICENSE_STAGES))
        self.f_period = lic.add_combo("Expiring Period", list(EXPIRY_PERIODS),
                                      width=18)
        self.f_period.set("Next 30 days")
        lic.add_submit("Generate", self.run_license_report)

        right = ttk.Frame(self)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        self.license_title = ttk.Label(right, text="Licenses", style="Page.TLabel",
                                       font=FONT_HEADER)
        self.license_title.grid(row=0, column=0, sticky="w", pady=(0, 8))
        cols = ("Code", "Name", "Designation", "Location", "License No",
                "Type", "Date", "Days Left")
        tree_frame, self.license_tree = make_tree(
            right, cols,
            {"Code": 70, "Name": 140, "Designation": 130, "Location": 80,
             "License No": 100, "Type": 50, "Date": 90, "Days Left": 70})
        tree_frame.grid(row=1, column=0, sticky="nsew")

        self.refresh()

    def refresh(self):
        rows, totals = staff_summary()
        for key, label in self.totals.items():
            label.configure(text=str(totals[key]))
        self.staff_tree.delete(*self.staff_tree.get_children())
        for row in rows:
            self.staff_tree.insert("", END, values=row)
        self.staff_tree.insert("", END, values=(
            "TOTAL", *(totals[kind] for kind in EMPLOYMENT_TYPES), totals["Total"]))
        self.run_license_report()

    def run_license_report(self):
        stage, period = self.f_stage.get(), self.f_period.get()
        results = license_expiry(stage, period)
        self.license_title.configure(
            text=f"{stage} - {period}  ({len(results)} found)")
        self.license_tree.delete(*self.license_tree.get_children())
        for r in results:
            self.license_tree.insert("", END, values=(
                r["employee_id"], r["name"], r["designation"], r["location"],
                r["license_no"], r["license_type"], r["date"], r["days_left"]))


# ---------------------------------------------------------------------------
# Application shell
# ---------------------------------------------------------------------------


class HRApp(Tk):
    def __init__(self):
        super().__init__()
        self.title("HR Management System")
        self.geometry("1180x720")
        self.minsize(980, 640)
        self.configure(background=PAGE_BG)
        _style()

        banner = tk.Frame(self, background=ORANGE)
        banner.pack(fill=X)
        tk.Label(banner, text="HR Management System", background=ORANGE,
                 foreground="white", font=FONT_TITLE, padx=22, pady=14,
                 anchor="w").pack(side=LEFT)
        tk.Label(banner, text="Nancy  •  Human Resources", background=ORANGE,
                 foreground="#F5D9CC", font=FONT, padx=22).pack(side=RIGHT)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=BOTH, expand=True, padx=12, pady=12)

        # Each tab lives inside a vertically-scrollable area so long forms
        # can be scrolled when the window is short.
        self.dashboard = self._add_tab(notebook, "  Dashboard  ", DashboardTab)
        self.employees = self._add_tab(notebook, "  Employees  ", EmployeesTab, self)
        self.attendance = self._add_tab(notebook, "  Attendance  ", AttendanceTab, self)
        self.leave = self._add_tab(notebook, "  Leave  ", LeaveTab, self)
        self.payroll = self._add_tab(notebook, "  Payroll  ", PayrollTab, self)
        self.reports = self._add_tab(notebook, "  Reports  ", ReportsTab, self)

        # Keep the summaries current whenever the user switches tabs.
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.dashboard.refresh()

    def _on_tab_changed(self, _event):
        self.dashboard.refresh()
        self.reports.refresh()

    def _add_tab(self, notebook, label, tab_class, *extra):
        outer, inner = scrollable_area(notebook)
        tab = tab_class(inner, *extra)
        tab.pack(fill=BOTH, expand=True)
        notebook.add(outer, text=label)
        return tab


def run():
    """Set up the database and launch the GUI."""
    setup_database()
    app = HRApp()
    app.mainloop()


if __name__ == "__main__":
    run()
