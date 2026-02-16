@echo off
cd /d "%~dp0"
echo ============================================
echo   Work Monitor Recorder - EXE Build
echo ============================================
echo.

REM Install dependencies
pip install pyinstaller pillow pynput >nul 2>&1

REM Build single-file EXE (no console window)
pyinstaller --onefile --noconsole --name work_recorder recorder.py

echo.
echo ============================================
echo   Build complete!
echo   dist\work_recorder.exe
echo ============================================
echo.
echo Copy dist\work_recorder.exe to each employee PC.
echo.
cmd /k
