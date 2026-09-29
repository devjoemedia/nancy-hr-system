# Nancy HR System

An HR management system (employees, attendance, leave, payroll, reports and
licence tracking, with Export to Excel) built with Python and SQLite.

This repository holds **three separate projects**. Each folder stands on its
own: it has everything it needs, its own README and its own requirements.

| Folder | What it is | Who it's for | Start here |
|---|---|---|---|
| [`desktop/`](desktop/) | The original desktop app: `hr_ms.py` (single file) and `hr_system.py` + `hr/` (modular). Tkinter window, or a terminal menu with `--cli`. | Running from source, e.g. in PyCharm | [desktop/README.md](desktop/README.md) |
| [`windows-exe/`](windows-exe/) | Builds the desktop app into `NancyHR.exe`, which runs on Windows without Python. | Staff on a Windows PC | [windows-exe/README.md](windows-exe/README.md) |
| [`web/`](web/) | The HR system as a website with logins, ready to host free on PythonAnywhere. | Several people sharing one set of records from any browser | [web/README.md](web/README.md) |

Each project keeps its own records (`hr_management.db` and a `photos` folder
next to its code). To start one with another's records, copy those across.

## Quick start

**Desktop (from source):**

```bash
cd desktop
pip install -r requirements.txt
python hr_ms.py
```

**Windows app:** download `NancyHR-windows.zip` from this repository's
**Releases** page, unzip it, and double-click `NancyHR.exe`.

**Website:** follow [web/README.md](web/README.md).

## Keeping the copies in step

The projects share some code by copy, so a fix in one may need copying to
the others:

- `windows-exe/hr_ms.py` is a copy of `desktop/hr_ms.py`.
- `web/hr/` is a trimmed copy of `desktop/hr/` (database, option lists,
  reports, photos, Excel export). New option lists or database columns added to the
  desktop app should be copied into `web/hr/constants.py` and
  `web/hr/database.py` too.
