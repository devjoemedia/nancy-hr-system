@echo off
rem Builds NancyHR.exe and NancyHR-windows.zip on a Windows PC.
rem Needs Python 3 installed (with "Add python.exe to PATH" ticked).
rem Double-click this file, or run it from a Command Prompt in this folder.

cd /d "%~dp0"

echo Installing build tools...
py -m pip install --upgrade -r requirements.txt || goto :error

echo Building NancyHR.exe...
py -m PyInstaller --onefile --windowed --name NancyHR --noconfirm hr_ms.py || goto :error

echo Packaging the zip...
if exist NancyHR rmdir /s /q NancyHR
mkdir NancyHR
copy dist\NancyHR.exe NancyHR\ >nul
copy logo.jpeg NancyHR\ >nul
copy README.txt NancyHR\ >nul
powershell -NoProfile -Command "Compress-Archive -Path NancyHR -DestinationPath NancyHR-windows.zip -Force" || goto :error

echo.
echo Done: NancyHR-windows.zip is ready to share.
pause
exit /b 0

:error
echo.
echo Build failed - see the messages above.
pause
exit /b 1
