@echo off
cd /d "%~dp0"
echo Starting analysis...
python analyzer.py %*
cmd /k
