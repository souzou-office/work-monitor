@echo off
cd /d "%~dp0"
set ANTHROPIC_API_KEY=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
echo Running analysis...
echo.
python analyzer.py
echo.
echo ==============================
echo Done. Check above for errors.
echo ==============================
cmd /k