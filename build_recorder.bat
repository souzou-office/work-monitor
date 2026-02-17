@echo off
cd /d "%~dp0"
echo ============================================
echo   Work Monitor Recorder - EXE Build
echo ============================================
echo.

REM Install dependencies
echo Installing dependencies...
pip install pyinstaller pillow pynput
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] pip install に失敗しました。
    echo Python と pip がインストールされているか確認してください。
    echo.
    cmd /k
    exit /b 1
)

REM Build single-file EXE (no console window)
echo.
echo Building EXE...
pyinstaller --onefile --noconsole --name work_recorder recorder.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] pyinstaller によるビルドに失敗しました。
    echo 上記のエラーメッセージを確認してください。
    echo.
    cmd /k
    exit /b 1
)

echo.
echo ============================================
echo   Build complete!
echo   dist\work_recorder.exe
echo ============================================
echo.
echo Copy dist\work_recorder.exe to each employee PC.
echo.
cmd /k
