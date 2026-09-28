"""HR Management System - single-file edition.

Everything the project does, bundled into one standalone file:

    * SQLite database setup + lightweight migrations
    * Shared helpers
    * Staff and licence-expiry reports
    * Employee profile pictures (JPG, JPEG, PNG - needs Pillow)
    * A desktop graphical interface (Tkinter) styled like an
      "Employee Data Form" (orange header, labelled fields, Submit)
    * The original text menu, kept for the terminal

It uses the same ``hr_management.db`` database as the package version,
so the two stay fully compatible.

Run the GUI (default):

    python hr_ms.py

Run the original terminal menu instead:

    python hr_ms.py --cli
"""

import math
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta

# ===========================================================================
# Database
# ===========================================================================

# The folder this file lives in. The database, the photos folder and the
# logo are looked up here rather than in whatever folder the app happens
# to be started from.
APP_DIR = os.path.dirname(os.path.abspath(__file__))

DATABASE = os.path.join(APP_DIR, "hr_management.db")

# ---- Option lists shared by the terminal menu and the GUI -----------------

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
    "Office Clerk",
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


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(cursor, table, column, definition):
    """Add ``column`` to ``table`` if it is not already present."""
    existing = [row["name"] for row in cursor.execute(f"PRAGMA table_info({table})")]
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def setup_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Employees
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            gender TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            department TEXT,
            position TEXT,
            date_hired TEXT,
            basic_salary REAL DEFAULT 0,
            annual_leave INTEGER DEFAULT 20,
            sick_leave INTEGER DEFAULT 10,
            active INTEGER DEFAULT 1
        )
    """)

    # Attendance
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            check_in TEXT,
            check_out TEXT,
            status TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Leave
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            days INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Payroll
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            month TEXT NOT NULL,
            basic_salary REAL NOT NULL,
            allowances REAL DEFAULT 0,
            overtime REAL DEFAULT 0,
            deductions REAL DEFAULT 0,
            net_salary REAL NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Lightweight migrations for columns added after the first release.
    # The GUI "Employee Data Form" needs Date of Birth and Location.
    _ensure_column(cursor, "employees", "date_of_birth", "TEXT")
    _ensure_column(cursor, "employees", "location", "TEXT DEFAULT 'Office'")

    # Employee identity, staff type, licence and emergency contact details.
    _ensure_column(cursor, "employees", "employment_type", "TEXT DEFAULT 'Permanent'")
    _ensure_column(cursor, "employees", "ghana_card_no", "TEXT")
    _ensure_column(cursor, "employees", "ssnit_no", "TEXT")
    _ensure_column(cursor, "employees", "qualification", "TEXT")
    _ensure_column(cursor, "employees", "license_no", "TEXT")
    _ensure_column(cursor, "employees", "license_type", "TEXT")
    _ensure_column(cursor, "employees", "license_first_renewal", "TEXT")
    _ensure_column(cursor, "employees", "license_second_renewal", "TEXT")
    _ensure_column(cursor, "employees", "license_expiry", "TEXT")
    _ensure_column(cursor, "employees", "emergency_contact", "TEXT")
    _ensure_column(cursor, "employees", "photo", "TEXT")

    # Company, service status and category.
    _ensure_column(cursor, "employees", "company", "TEXT")
    _ensure_column(cursor, "employees", "service_status", "TEXT DEFAULT 'Active'")
    _ensure_column(cursor, "employees", "category", "TEXT")

    # "Shift Supervisor" became "Shift Supervisor / Field Supervisor".
    cursor.execute("""
        UPDATE employees SET position = 'Shift Supervisor / Field Supervisor'
        WHERE position = 'Shift Supervisor'
    """)

    # Attendance shift (A, B, C, D or Straight Day).
    _ensure_column(cursor, "attendance", "shift", "TEXT")


    conn.commit()
    conn.close()


# ===========================================================================
# Shared helpers
# ===========================================================================


def pause():
    input("\nPress Enter to continue...")


def get_employee(employee_id):
    conn = get_connection()
    employee = conn.execute(
        "SELECT * FROM employees WHERE employee_id = ? AND active = 1",
        (employee_id,)
    ).fetchone()
    conn.close()
    return employee


def calculate_days(start_date, end_date):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        if end < start:
            return 0

        return (end - start).days + 1

    except ValueError:
        return 0


def is_valid_date(value):
    """True if ``value`` is empty or a YYYY-MM-DD date."""
    if not value:
        return True
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def choose(title, options, allow_blank=False, current=None):
    """Print a numbered list and return the chosen option.

    Returns ``current`` when the user presses Enter and ``allow_blank`` is
    set (useful when updating a record), or ``None`` for an invalid choice.
    """
    print(f"\n{title}:")
    for number, option in enumerate(options, start=1):
        print(f"{number}. {option}")

    prompt = "Select"
    if allow_blank:
        prompt += f" [{current or ''}]"
    choice = input(prompt + ": ").strip()

    if not choice and allow_blank:
        return current
    if choice.isdigit() and 1 <= int(choice) <= len(options):
        return options[int(choice) - 1]
    return None


# ===========================================================================
# Reports (staff numbers and licence expiry)
# ===========================================================================


def staff_summary():
    """Count active staff by location and staff status.

    Returns ``(rows, totals)``. Each row is ``(location, count for each
    of EMPLOYMENT_TYPES..., total)`` and ``totals`` maps each staff status
    (and "Total") to its overall count.
    """
    conn = get_connection()
    counts = conn.execute("""
        SELECT
            COALESCE(NULLIF(location, ''), 'Not set') AS location,
            COALESCE(NULLIF(employment_type, ''), 'Permanent') AS employment_type,
            COUNT(*) AS n
        FROM employees
        WHERE active = 1
        GROUP BY 1, 2
    """).fetchall()
    conn.close()

    table = {}
    for row in counts:
        table.setdefault(row["location"], {})[row["employment_type"]] = row["n"]

    # Known locations first (always shown), then anything else in the data.
    locations = LOCATIONS + sorted(loc for loc in table if loc not in LOCATIONS)

    rows = []
    totals = {kind: 0 for kind in EMPLOYMENT_TYPES}
    for location in locations:
        by_type = table.get(location, {})
        counts_here = [by_type.get(kind, 0) for kind in EMPLOYMENT_TYPES]
        rows.append((location, *counts_here, sum(counts_here)))
        for kind, n in zip(EMPLOYMENT_TYPES, counts_here):
            totals[kind] += n
    totals["Total"] = sum(totals[kind] for kind in EMPLOYMENT_TYPES)
    return rows, totals


def license_expiry(stage, period):
    """Employees whose licence ``stage`` date falls within ``period``.

    ``stage`` is a key of LICENSE_STAGES and ``period`` a key of
    EXPIRY_PERIODS. Returns a list of dicts sorted by date, each with the
    employee details, the date and the number of days left (negative when
    already passed).
    """
    column = LICENSE_STAGES[stage]
    days = EXPIRY_PERIODS[period]
    today = date.today()

    conn = get_connection()
    rows = conn.execute(f"""
        SELECT * FROM employees
        WHERE active = 1 AND {column} IS NOT NULL AND {column} != ''
    """).fetchall()
    conn.close()

    results = []
    for row in rows:
        try:
            due = datetime.strptime(row[column], "%Y-%m-%d").date()
        except ValueError:
            continue

        if days is None:
            matches = due < today
        else:
            matches = today <= due <= today + timedelta(days=days)

        if matches:
            results.append({
                "employee_id": row["employee_id"],
                "name": f"{row['first_name']} {row['last_name']}",
                "designation": row["position"] or "",
                "location": row["location"] or "",
                "license_no": row["license_no"] or "",
                "license_type": row["license_type"] or "",
                "date": row[column],
                "days_left": (due - today).days,
            })

    results.sort(key=lambda r: r["date"])
    return results


def licenses_due_count(days=30):
    """How many active staff have any licence date due in the next ``days``."""
    today = date.today()
    limit = today + timedelta(days=days)
    conn = get_connection()
    rows = conn.execute("SELECT * FROM employees WHERE active = 1").fetchall()
    conn.close()

    count = 0
    for row in rows:
        for column in LICENSE_STAGES.values():
            try:
                due = datetime.strptime(row[column] or "", "%Y-%m-%d").date()
            except ValueError:
                continue
            if today <= due <= limit:
                count += 1
                break
    return count


# ===========================================================================
# Profile pictures
# ===========================================================================
#
# Pictures are copied into the ``photos`` folder (next to the database),
# resized so they never exceed PHOTO_MAX_SIZE, and saved as
# ``<employee code>.png``. The employees table only stores the file name.
# JPEG pictures and JPEG logos need Pillow:  pip install pillow

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk
except ImportError:          # the rest of the app still works without it
    Image = ImageDraw = ImageFont = ImageOps = ImageTk = None

PHOTO_DIR = os.path.join(APP_DIR, "photos")
LOGO_NAMES = ("logo.jpeg", "logo.jpg", "logo.png")
PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png")
PHOTO_MAX_SIZE = (400, 400)
AVATAR_COLORS = ["#C0501E", "#2E7D5B", "#3A5A8C", "#B4881C", "#7A3E8C", "#1F7A8C"]
PILLOW_AVAILABLE = Image is not None
PILLOW_MISSING = "Profile pictures need Pillow. Install it with:  pip install pillow"


class PhotoError(Exception):
    """Raised when a picture cannot be used."""


def photo_path(filename):
    return os.path.join(PHOTO_DIR, filename) if filename else None


def save_photo(source, employee_id):
    """Copy ``source`` into the photos folder and return the new file name."""
    if Image is None:
        raise PhotoError(PILLOW_MISSING)
    if not source.lower().endswith(PHOTO_EXTENSIONS):
        raise PhotoError("Please choose a .jpg, .jpeg or .png picture.")

    try:
        with Image.open(source) as picture:
            # Phone photos store their rotation separately; apply it.
            picture = ImageOps.exif_transpose(picture).convert("RGBA")
    except (OSError, ValueError) as error:
        raise PhotoError(f"Could not open the picture:\n{error}")

    picture.thumbnail(PHOTO_MAX_SIZE)
    os.makedirs(PHOTO_DIR, exist_ok=True)
    filename = f"{employee_id}.png"
    picture.save(photo_path(filename), "PNG")
    return filename


def delete_photo(filename):
    path = photo_path(filename)
    if path and os.path.exists(path):
        os.remove(path)


def load_thumbnail(path, size):
    """Return a Tk image of the picture at ``path`` fitted inside ``size``.

    Returns ``None`` when there is no picture or it cannot be read.
    Keep a reference to the result, or Tk will discard the image.
    """
    if Image is None or not path or not os.path.exists(path):
        return None
    try:
        with Image.open(path) as picture:
            picture = picture.convert("RGBA")
    except (OSError, ValueError):
        return None
    picture.thumbnail(size)
    return ImageTk.PhotoImage(picture)


def initials(first_name, last_name):
    """"Kofi Ansah" -> "KA"."""
    return ((first_name or "")[:1] + (last_name or "")[:1]).upper() or "?"


def _avatar_font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:            # Pillow older than 10.1
        return ImageFont.load_default()


def make_avatar(filename, first_name, last_name, size=36, key=""):
    """Return a round Tk image: the employee's photo, or their initials.

    ``key`` (e.g. the employee code) picks a steady background colour for
    the initials. Returns ``None`` when Pillow is not installed.
    Keep a reference to the result, or Tk will discard the image.
    """
    if Image is None:
        return None

    big = size * 3               # draw large, then shrink for smooth edges
    picture = None
    path = photo_path(filename)
    if path and os.path.exists(path):
        try:
            with Image.open(path) as img:
                picture = ImageOps.fit(img.convert("RGBA"), (big, big))
            # Put see-through PNGs on white before cutting the circle.
            picture = Image.alpha_composite(
                Image.new("RGBA", (big, big), "white"), picture)
        except (OSError, ValueError):
            picture = None

    if picture is None:
        seed = sum(ord(ch) for ch in (key or first_name or "") + (last_name or ""))
        picture = Image.new("RGBA", (big, big), AVATAR_COLORS[seed % len(AVATAR_COLORS)])
        ImageDraw.Draw(picture).text(
            (big / 2, big / 2), initials(first_name, last_name),
            fill="white", font=_avatar_font(int(big * 0.42)), anchor="mm")

    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
    picture.putalpha(mask)
    return ImageTk.PhotoImage(picture.resize((size, size), Image.LANCZOS))


def find_logo(folder=APP_DIR):
    """Return the path of the logo in ``folder`` (any capitalisation), or None."""
    try:
        files = os.listdir(folder)
    except OSError:
        return None
    for wanted in LOGO_NAMES:
        for name in files:
            if name.lower() == wanted:
                return os.path.join(folder, name)
    return None


def load_logo(max_size, background):
    """Return ``(image, problem)`` for the company logo.

    ``image`` is a Tk image or ``None``; when it is ``None``, ``problem``
    says why, so it can be shown on screen. With Pillow, the plain area
    around the logo is filled with ``background`` so it blends into the page.
    """
    path = find_logo()
    if path is None:
        return None, ("Logo not shown: put logo.jpeg (or logo.jpg / logo.png) in\n"
                      + APP_DIR)
    name = os.path.basename(path)

    if Image is None:
        if not name.lower().endswith(".png"):
            return None, ("Logo not shown: JPEG logos need Pillow.\n"
                          "Install it with:  pip install pillow")
        import tkinter as tk
        try:
            picture = tk.PhotoImage(file=path)
        except tk.TclError:
            return None, f"Logo not shown: {name} could not be opened."
        shrink = math.ceil(max(picture.width() / max_size[0],
                               picture.height() / max_size[1], 1))
        return picture.subsample(shrink), None

    try:
        with Image.open(path) as picture:
            picture = picture.convert("RGB")
    except (OSError, ValueError):
        return None, f"Logo not shown: {name} could not be opened."

    fill = Image.new("RGB", (1, 1), background).getpixel((0, 0))
    width, height = picture.size
    for corner in ((0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)):
        ImageDraw.floodfill(picture, corner, fill, thresh=40)

    picture.thumbnail(max_size, Image.LANCZOS)
    return ImageTk.PhotoImage(picture), None


# ===========================================================================
# Graphical interface (Tkinter)
# ===========================================================================

from tkinter import (  # noqa: E402  (kept with the GUI section for clarity)
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
import tkinter as tk  # noqa: E402

# ---- Theme ----------------------------------------------------------------

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


# ---- Reusable widgets -----------------------------------------------------


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


# ---- Tabs -----------------------------------------------------------------


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

        ttk.Button(body, text="Refresh", style="Ghost.TButton",
                   command=self.refresh).grid(row=2, column=0, sticky="w",
                                              pady=(10, 0))

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


# ---- Application shell ----------------------------------------------------


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


def run_gui():
    """Set up the database and launch the GUI."""
    setup_database()
    app = HRApp()
    app.mainloop()


# ===========================================================================
# Terminal interface (the original text menu, kept for reference)
# ===========================================================================


# Extra details asked for after the basic fields: (column, prompt, is_date).
# Pick-list details: (column, title, options, required for a new employee).
_CLI_CHOICE_FIELDS = [
    ("employment_type", "Staff Status", EMPLOYMENT_TYPES, True),
    ("company", "Company", COMPANIES, False),
    ("service_status", "Service Status", SERVICE_STATUSES, True),
    ("department", "Department", DEPARTMENTS, False),
    ("position", "Designation", DESIGNATIONS, True),
    ("category", "Category", CATEGORIES, False),
    ("location", "Location", LOCATIONS, True),
]

_CLI_EXTRA_TEXT_FIELDS = [
    ("ghana_card_no", "Ghana Card No", False),
    ("ssnit_no", "SSNIT No", False),
    ("qualification", "Qualification", False),
    ("emergency_contact", "Emergency Contact", False),
    ("license_no", "License No", False),
    ("license_first_renewal", "1st Renewal Date (YYYY-MM-DD)", True),
    ("license_second_renewal", "2nd Renewal Date (YYYY-MM-DD)", True),
    ("license_expiry", "Expiry Date (YYYY-MM-DD)", True),
]


def _cli_ask_extra_details(employee=None):
    """Ask for the pick-list details, IDs and licence details.

    When ``employee`` is given, pressing Enter keeps the current value.
    Returns a dict of column -> value, or ``None`` if an entry is invalid.
    """
    current = dict(employee) if employee else {}
    editing = bool(employee)
    details = {}
    for column, title, options, required in _CLI_CHOICE_FIELDS:
        # Enter keeps the current value when editing, or skips an
        # optional field for a new employee.
        allow_blank = editing or not required
        if not required and not editing:
            title += " (Enter to skip)"
        value = choose(title, options, allow_blank, current.get(column))
        if value is None and not allow_blank:
            print("Invalid option.")
            return None
        details[column] = value or ""
    for column, label, is_date in _CLI_EXTRA_TEXT_FIELDS:
        if editing:
            value = input(f"{label} [{current.get(column) or ''}]: ").strip()
            value = value or current.get(column) or ""
        else:
            value = input(f"{label}: ").strip()
        if is_date and not is_valid_date(value):
            print("Invalid date. Use YYYY-MM-DD.")
            return None
        details[column] = value
    details["license_type"] = choose(
        "License Type", LICENSE_TYPES, True, current.get("license_type")) or ""
    return details


def _cli_ask_photo(employee_id, current=None):
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
    conn.execute("UPDATE employees SET photo = ? WHERE employee_id = ?",
                 (filename, employee_id))
    conn.commit()
    conn.close()
    print("Photo saved:", photo_path(filename))


def _cli_add_employee():
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
    details = _cli_ask_extra_details()
    if details is None:
        return

    values = {
        "employee_id": employee_id, "first_name": first_name,
        "last_name": last_name, "gender": gender, "phone": phone,
        "email": email, "address": address,
        "date_hired": date_hired, "basic_salary": basic_salary, **details,
    }
    conn = get_connection()
    try:
        conn.execute(f"""
            INSERT INTO employees ({", ".join(values)})
            VALUES ({", ".join("?" for _ in values)})
        """, list(values.values()))
        conn.commit()
        print("\nEmployee added successfully.")
    except sqlite3.IntegrityError:
        print("\nEmployee ID already exists.")
        return
    finally:
        conn.close()
    _cli_ask_photo(employee_id)


def _cli_view_employees():
    print("\n========== EMPLOYEE LIST ==========")
    conn = get_connection()
    employees = conn.execute(
        "SELECT * FROM employees WHERE active = 1 ORDER BY id DESC").fetchall()
    conn.close()
    if not employees:
        print("No employees found.")
        return
    print("-" * 160)
    print(f"{'ID':<10}{'Name':<25}{'Date of Birth':<15}{'Designation':<37}"
          f"{'Category':<10}{'Location':<12}{'Status':<11}{'Salary':<15}{'Phone':<15}")
    print("-" * 160)
    for e in employees:
        name = f"{e['first_name']} {e['last_name']}"
        print(f"{e['employee_id']:<10}{name:<25}{e['date_of_birth'] or '':<15}"
              f"{e['position'] or '':<37}{e['category'] or '':<10}"
              f"{e['location'] or '':<12}{e['employment_type'] or '':<11}"
              f"{e['basic_salary']:<15.2f}{e['phone'] or '':<15}")
    print("-" * 160)


def _cli_search_employee():
    print("\n========== SEARCH EMPLOYEE ==========")
    search = input("Enter employee ID or name: ").strip()
    conn = get_connection()
    employees = conn.execute("""
        SELECT * FROM employees
        WHERE active = 1 AND (
            employee_id LIKE ? OR first_name LIKE ? OR last_name LIKE ?)
    """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    conn.close()
    if not employees:
        print("No employees found.")
        return
    for e in employees:
        print("\n-----------------------------------")
        print("Employee ID :", e["employee_id"])
        print("Name        :", e["first_name"], e["last_name"])
        print("Gender      :", e["gender"])
        print("Phone       :", e["phone"])
        print("Email       :", e["email"])
        print("Address     :", e["address"])
        print("Emergency   :", e["emergency_contact"])
        print("Ghana Card  :", e["ghana_card_no"])
        print("SSNIT No    :", e["ssnit_no"])
        print("Qualification:", e["qualification"])
        print("Department  :", e["department"])
        print("Designation :", e["position"])
        print("Location    :", e["location"])
        print("Category    :", e["category"])
        print("Staff Status:", e["employment_type"])
        print("Company     :", e["company"])
        print("Service     :", e["service_status"])
        print("Date Hired  :", e["date_hired"])
        print("Salary      :", e["basic_salary"])
        print("License No  :", e["license_no"])
        print("License Type:", e["license_type"])
        print("1st Renewal :", e["license_first_renewal"])
        print("2nd Renewal :", e["license_second_renewal"])
        print("Expiry Date :", e["license_expiry"])
        print("Annual Leave:", e["annual_leave"])
        print("Sick Leave  :", e["sick_leave"])
        print("Photo       :", photo_path(e["photo"]) or "None")


def _cli_update_employee():
    print("\n========== UPDATE EMPLOYEE ==========")
    employee_id = input("Employee ID: ").strip()
    employee = get_employee(employee_id)
    if not employee:
        print("Employee not found.")
        return
    print("Leave a field empty to keep the current value.")
    first_name = input(f"First Name [{employee['first_name']}]: ").strip() or employee["first_name"]
    last_name = input(f"Last Name [{employee['last_name']}]: ").strip() or employee["last_name"]
    phone = input(f"Phone [{employee['phone']}]: ").strip() or employee["phone"]
    email = input(f"Email [{employee['email']}]: ").strip() or employee["email"]
    salary_input = input(f"Basic Salary [{employee['basic_salary']}]: ").strip()
    if salary_input:
        try:
            salary = float(salary_input)
        except ValueError:
            print("Invalid salary.")
            return
    else:
        salary = employee["basic_salary"]
    details = _cli_ask_extra_details(employee)
    if details is None:
        return
    details.update(first_name=first_name, last_name=last_name, phone=phone,
                   email=email, basic_salary=salary)
    conn = get_connection()
    conn.execute(f"""
        UPDATE employees SET {", ".join(f"{c} = ?" for c in details)}
        WHERE employee_id = ?
    """, list(details.values()) + [employee_id])
    conn.commit()
    conn.close()
    _cli_ask_photo(employee_id, employee["photo"])
    print("Employee updated successfully.")


def _cli_delete_employee():
    print("\n========== DELETE EMPLOYEE ==========")
    employee_id = input("Employee ID: ").strip()
    employee = get_employee(employee_id)
    if not employee:
        print("Employee not found.")
        return
    confirm = input(
        f"Deactivate {employee['first_name']} {employee['last_name']}? (y/n): ").lower()
    if confirm != "y":
        print("Operation cancelled.")
        return
    conn = get_connection()
    conn.execute("UPDATE employees SET active = 0 WHERE employee_id = ?", (employee_id,))
    conn.commit()
    conn.close()
    print("Employee deactivated successfully.")


def _cli_employee_menu():
    while True:
        print("\n\n========== EMPLOYEE MANAGEMENT ==========")
        print("1. Add Employee")
        print("2. View Employees")
        print("3. Search Employee")
        print("4. Update Employee")
        print("5. Deactivate Employee")
        print("0. Back")
        choice = input("Select option: ").strip()
        if choice == "1":
            _cli_add_employee(); pause()
        elif choice == "2":
            _cli_view_employees(); pause()
        elif choice == "3":
            _cli_search_employee(); pause()
        elif choice == "4":
            _cli_update_employee(); pause()
        elif choice == "5":
            _cli_delete_employee(); pause()
        elif choice == "0":
            break
        else:
            print("Invalid option.")


def _cli_record_attendance():
    print("\n========== RECORD ATTENDANCE ==========")
    employee_id = input("Employee ID: ").strip()
    if not get_employee(employee_id):
        print("Employee not found.")
        return
    attendance_date = input("Date (YYYY-MM-DD) [today]: ").strip() or date.today().isoformat()
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
            INSERT INTO attendance
                (employee_id, attendance_date, shift, check_in, check_out, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee_id, attendance_date, shift, check_in, check_out, status))
        conn.commit()
        print("Attendance recorded successfully.")
    except sqlite3.Error as error:
        print("Error:", error)
    finally:
        conn.close()


def _cli_view_attendance():
    print("\n========== ATTENDANCE RECORDS ==========")
    employee_id = input("Employee ID (leave empty for all): ").strip()
    conn = get_connection()
    if employee_id:
        records = conn.execute("""
            SELECT a.*, e.first_name, e.last_name FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            WHERE a.employee_id = ? ORDER BY a.attendance_date DESC
        """, (employee_id,)).fetchall()
    else:
        records = conn.execute("""
            SELECT a.*, e.first_name, e.last_name FROM attendance a
            JOIN employees e ON a.employee_id = e.employee_id
            ORDER BY a.attendance_date DESC
        """).fetchall()
    conn.close()
    if not records:
        print("No attendance records found.")
        return
    print("-" * 100)
    for r in records:
        name = f"{r['first_name']} {r['last_name']}"
        print(f"{r['attendance_date']} | {r['employee_id']} | {name} | "
              f"Shift: {r['shift'] or '-'} | IN: {r['check_in']} | OUT: {r['check_out']} | {r['status']}")
    print("-" * 100)


def _cli_attendance_menu():
    while True:
        print("\n\n========== ATTENDANCE ==========")
        print("1. Record Attendance")
        print("2. View Attendance")
        print("0. Back")
        choice = input("Select option: ").strip()
        if choice == "1":
            _cli_record_attendance(); pause()
        elif choice == "2":
            _cli_view_attendance(); pause()
        elif choice == "0":
            break
        else:
            print("Invalid option.")


def _cli_request_leave():
    print("\n========== LEAVE REQUEST ==========")
    employee_id = input("Employee ID: ").strip()
    if not get_employee(employee_id):
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
        INSERT INTO leave_requests
            (employee_id, leave_type, start_date, end_date, days, reason)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (employee_id, leave_type, start_date, end_date, days, reason))
    conn.commit()
    conn.close()
    print(f"Leave request submitted for {days} day(s).")


def _cli_view_leave_requests():
    print("\n========== LEAVE REQUESTS ==========")
    conn = get_connection()
    requests = conn.execute("""
        SELECT l.*, e.first_name, e.last_name FROM leave_requests l
        JOIN employees e ON l.employee_id = e.employee_id ORDER BY l.id DESC
    """).fetchall()
    conn.close()
    if not requests:
        print("No leave requests found.")
        return
    for r in requests:
        print("\n-----------------------------------")
        print("Request ID :", r["id"])
        print("Employee   :", r["employee_id"])
        print("Name       :", f"{r['first_name']} {r['last_name']}")
        print("Leave Type :", r["leave_type"])
        print("Start Date :", r["start_date"])
        print("End Date   :", r["end_date"])
        print("Days       :", r["days"])
        print("Reason     :", r["reason"])
        print("Status     :", r["status"])


def _cli_approve_leave():
    print("\n========== APPROVE/REJECT LEAVE ==========")
    _cli_view_leave_requests()
    try:
        request_id = int(input("\nEnter Request ID: "))
    except ValueError:
        print("Invalid ID.")
        return
    print("\n1. Approve\n2. Reject")
    choice = input("Select: ").strip()
    if choice == "1":
        status = "Approved"
    elif choice == "2":
        status = "Rejected"
    else:
        print("Invalid option.")
        return
    conn = get_connection()
    request = conn.execute(
        "SELECT * FROM leave_requests WHERE id = ?", (request_id,)).fetchone()
    if not request:
        print("Leave request not found.")
        conn.close()
        return
    if request["status"] != "Pending":
        print("This request has already been processed.")
        conn.close()
        return
    if status == "Approved" and request["leave_type"] in ("Annual", "Sick"):
        column = "annual_leave" if request["leave_type"] == "Annual" else "sick_leave"
        employee = conn.execute(
            f"SELECT {column} FROM employees WHERE employee_id = ?",
            (request["employee_id"],)).fetchone()
        if employee[column] < request["days"]:
            print(f"Employee does not have enough {request['leave_type'].lower()} leave.")
            conn.close()
            return
        conn.execute(
            f"UPDATE employees SET {column} = {column} - ? WHERE employee_id = ?",
            (request["days"], request["employee_id"]))
    conn.execute("UPDATE leave_requests SET status = ? WHERE id = ?",
                 (status, request_id))
    conn.commit()
    conn.close()
    print(f"Leave request {status.lower()}.")


def _cli_view_leave_balance():
    print("\n========== LEAVE BALANCES ==========")
    employee_id = input("Employee ID: ").strip()
    employee = get_employee(employee_id)
    if not employee:
        print("Employee not found.")
        return
    print("\nEmployee:", employee["first_name"], employee["last_name"])
    print("Annual Leave Remaining:", employee["annual_leave"])
    print("Sick Leave Remaining  :", employee["sick_leave"])


def _cli_leave_menu():
    while True:
        print("\n\n========== LEAVE MANAGEMENT ==========")
        print("1. Request Leave")
        print("2. View Leave Requests")
        print("3. Approve/Reject Leave")
        print("4. View Leave Balance")
        print("0. Back")
        choice = input("Select option: ").strip()
        if choice == "1":
            _cli_request_leave(); pause()
        elif choice == "2":
            _cli_view_leave_requests(); pause()
        elif choice == "3":
            _cli_approve_leave(); pause()
        elif choice == "4":
            _cli_view_leave_balance(); pause()
        elif choice == "0":
            break
        else:
            print("Invalid option.")


def _cli_generate_payroll():
    print("\n========== GENERATE PAYROLL ==========")
    employee_id = input("Employee ID: ").strip()
    employee = get_employee(employee_id)
    if not employee:
        print("Employee not found.")
        return
    month = input("Payroll month (YYYY-MM): ").strip()
    try:
        allowances = float(input("Allowances: "))
        overtime = float(input("Overtime: "))
        deductions = float(input("Deductions: "))
    except ValueError:
        print("Invalid amount.")
        return
    basic_salary = employee["basic_salary"]
    net_salary = basic_salary + allowances + overtime - deductions
    conn = get_connection()
    conn.execute("""
        INSERT INTO payroll
            (employee_id, month, basic_salary, allowances, overtime,
             deductions, net_salary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (employee_id, month, basic_salary, allowances, overtime, deductions,
          net_salary))
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


def _cli_view_payroll():
    print("\n========== PAYROLL HISTORY ==========")
    employee_id = input("Employee ID (leave empty for all): ").strip()
    conn = get_connection()
    if employee_id:
        records = conn.execute("""
            SELECT p.*, e.first_name, e.last_name FROM payroll p
            JOIN employees e ON p.employee_id = e.employee_id
            WHERE p.employee_id = ? ORDER BY p.id DESC
        """, (employee_id,)).fetchall()
    else:
        records = conn.execute("""
            SELECT p.*, e.first_name, e.last_name FROM payroll p
            JOIN employees e ON p.employee_id = e.employee_id ORDER BY p.id DESC
        """).fetchall()
    conn.close()
    if not records:
        print("No payroll records found.")
        return
    print("-" * 110)
    for r in records:
        name = f"{r['first_name']} {r['last_name']}"
        print(f"Employee: {r['employee_id']} - {name}\n"
              f"Month: {r['month']}\n"
              f"Basic: {r['basic_salary']:.2f}\n"
              f"Allowances: {r['allowances']:.2f}\n"
              f"Overtime: {r['overtime']:.2f}\n"
              f"Deductions: {r['deductions']:.2f}\n"
              f"NET: {r['net_salary']:.2f}")
        print("-" * 110)


def _cli_payroll_menu():
    while True:
        print("\n\n========== PAYROLL ==========")
        print("1. Generate Payroll")
        print("2. View Payroll")
        print("0. Back")
        choice = input("Select option: ").strip()
        if choice == "1":
            _cli_generate_payroll(); pause()
        elif choice == "2":
            _cli_view_payroll(); pause()
        elif choice == "0":
            break
        else:
            print("Invalid option.")


def _cli_staff_report():
    print("\n========== STAFF REPORT ==========")
    rows, totals = staff_summary()
    print()
    for kind in EMPLOYMENT_TYPES:
        print(f"{f'Total number of {kind} Staff':<32}: {totals[kind]}")
    print(f"{'Total Staff':<32}: {totals['Total']}")
    width = 16 + 11 * (len(EMPLOYMENT_TYPES) + 1)
    print("\n" + "-" * width)
    print(f"{'Location':<16}" + "".join(f"{k:>11}" for k in EMPLOYMENT_TYPES)
          + f"{'Total':>11}")
    print("-" * width)
    for location, *numbers in rows:
        print(f"{location:<16}" + "".join(f"{n:>11}" for n in numbers))
    print("-" * width)


def _cli_license_report():
    print("\n========== LICENCE EXPIRY REPORT ==========")
    stage = choose("Licence date to check", list(LICENSE_STAGES))
    period = choose("Expiring period", list(EXPIRY_PERIODS)) if stage else None
    if not stage or not period:
        print("Invalid option.")
        return
    results = license_expiry(stage, period)
    print(f"\n{stage} - {period}")
    if not results:
        print("No licences found.")
        return
    print("-" * 100)
    for r in results:
        print(f"{r['employee_id']:<10}{r['name']:<25}{r['license_no']:<15}"
              f"{r['license_type']:<6}{r['date']:<12}{r['days_left']:>5} day(s)")
    print("-" * 100)


def _cli_reports_menu():
    while True:
        print("\n\n========== REPORTS ==========")
        print("1. Staff Report (Permanent / Contract / Casual)")
        print("2. Licence Expiry Report")
        print("0. Back")
        choice = input("Select option: ").strip()
        if choice == "1":
            _cli_staff_report(); pause()
        elif choice == "2":
            _cli_license_report(); pause()
        elif choice == "0":
            break
        else:
            print("Invalid option.")


def _cli_dashboard():
    conn = get_connection()
    employee_count = conn.execute(
        "SELECT COUNT(*) FROM employees WHERE active = 1").fetchone()[0]
    today = date.today().isoformat()
    attendance_today = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date = ?", (today,)).fetchone()[0]
    pending_leave = conn.execute(
        "SELECT COUNT(*) FROM leave_requests WHERE status = 'Pending'").fetchone()[0]
    payroll_count = conn.execute("SELECT COUNT(*) FROM payroll").fetchone()[0]
    conn.close()
    _rows, staff = staff_summary()
    licenses_due = licenses_due_count(30)
    print("\n")
    print("=" * 60)
    print("              HR MANAGEMENT SYSTEM")
    print("=" * 60)
    print()
    print(f"Active Employees     : {employee_count}")
    print(f"  Perm / Contr / Cas : "
          f"{staff['Permanent']} / {staff['Contract']} / {staff['Casual']}")
    print(f"Attendance Today     : {attendance_today}")
    print(f"Pending Leave        : {pending_leave}")
    print(f"Payroll Records      : {payroll_count}")
    print(f"Licenses Due (30d)   : {licenses_due}")
    print("=" * 60)


def run_cli():
    setup_database()
    while True:
        _cli_dashboard()
        print("\nMAIN MENU")
        print("1. Employee Database")
        print("2. Attendance")
        print("3. Leave Management")
        print("4. Payroll")
        print("5. Reports")
        print("0. Exit")
        choice = input("\nSelect option: ").strip()
        if choice == "1":
            _cli_employee_menu()
        elif choice == "2":
            _cli_attendance_menu()
        elif choice == "3":
            _cli_leave_menu()
        elif choice == "4":
            _cli_payroll_menu()
        elif choice == "5":
            _cli_reports_menu()
        elif choice == "0":
            print("\nThank you for using the HR Management System.")
            break
        else:
            print("Invalid option.")


# ===========================================================================
# Entry point
# ===========================================================================


def main():
    if "--cli" in sys.argv or "--terminal" in sys.argv:
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()

