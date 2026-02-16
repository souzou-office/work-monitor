@echo off
taskkill /f /im pythonw.exe 2>nul
echo Recording stopped.
timeout /t 3
