@echo off
cd /d "%~dp0"
taskkill /f /im pythonw.exe 2>nul
timeout /t 1 /nobreak >nul
start "" pythonw.exe recorder.py
echo Recording started.
timeout /t 3
