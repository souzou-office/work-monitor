@echo off
cd /d "%~dp0"
echo ============================================
echo   Work Monitor Recorder - EXE Build
echo ============================================
echo.

REM Check Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 goto :no_python

REM Install dependencies
echo Installing dependencies...
python -m pip install pyinstaller pillow pynput
if %errorlevel% neq 0 goto :pip_fail

REM Build single-file EXE (no console window)
echo.
echo Building EXE...
python -m PyInstaller --onefile --noconsole --name work_recorder recorder.py
if %errorlevel% neq 0 goto :build_fail

echo.
echo ============================================
echo   Build complete!
echo   dist\work_recorder.exe
echo ============================================
echo.
echo Copy dist\work_recorder.exe to each employee PC.
echo.
cmd /k
exit /b 0

:no_python
echo.
echo [ERROR] Python not found.
echo Please install from https://www.python.org/downloads/
echo Check "Add Python to PATH" during installation.
echo.
cmd /k
exit /b 1

:pip_fail
echo.
echo [ERROR] pip install failed.
echo.
cmd /k
exit /b 1

:build_fail
echo.
echo [ERROR] PyInstaller build failed. See error messages above.
echo.
cmd /k
exit /b 1
