# HR System – Windows App (.exe)

This folder builds the desktop HR system into a single Windows program,
`NancyHR.exe`, that runs on any Windows PC **without Python**. It is a
standalone project: `hr_ms.py` here is the single-file desktop app.

## What's in this folder

| File | Purpose |
|---|---|
| `hr_ms.py` | The app that gets packaged (copy of `desktop/hr_ms.py`) |
| `logo.jpeg` | Logo shipped next to the `.exe` |
| `README.txt` | Instructions for the people who use the `.exe` (goes in the zip) |
| `build.bat` | Builds the `.exe` and zip on a Windows PC |
| `requirements.txt` | Build tools: PyInstaller and Pillow |

## Option 1: let GitHub build it (no Windows PC needed)

The workflow in `.github/workflows/build-windows.yml` builds on GitHub's
Windows machines.

- **Make a release:** push a version tag. GitHub builds the `.exe` and
  publishes `NancyHR-windows.zip` on the repository's **Releases** page.

  ```bash
  git tag v1.0
  git push origin v1.0
  ```

- **Just a test build:** on GitHub open **Actions → Build Windows app →
  Run workflow**. The zip appears under that run's **Artifacts**.

## Option 2: build on a Windows PC

Install Python 3 (tick **"Add python.exe to PATH"**), then double-click
`build.bat`. When it finishes, `NancyHR-windows.zip` is in this folder.

## Where the app keeps its data

When packaged, the app stores `hr_management.db` and the `photos` folder
**next to `NancyHR.exe`**, and reads `logo.jpeg` from there too. Users should
unzip it somewhere permanent (e.g. `Documents\NancyHR`) and back up that folder.

## Updating the app

`hr_ms.py` here is a copy. After changing the desktop app, copy the new
version in before building:

```bash
cp desktop/hr_ms.py windows-exe/hr_ms.py
```

To give users the update, send only the new `NancyHR.exe`; their
`hr_management.db` and `photos` folder stay as they are.
