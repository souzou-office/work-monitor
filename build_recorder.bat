@echo off
chcp 65001 >nul
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
pyinstaller --onefile --noconsole --name work_recorder recorder.py
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
echo [ERROR] Python が見つかりません。
echo https://www.python.org/downloads/ からインストールしてください。
echo インストール時に「Add Python to PATH」にチェックを入れてください。
echo.
cmd /k
exit /b 1

:pip_fail
echo.
echo [ERROR] pip install に失敗しました。
echo Python と pip がインストールされているか確認してください。
echo.
cmd /k
exit /b 1

:build_fail
echo.
echo [ERROR] pyinstaller によるビルドに失敗しました。
echo 上記のエラーメッセージを確認してください。
echo.
cmd /k
exit /b 1
