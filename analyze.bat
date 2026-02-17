@echo off
cd /d "%~dp0"

REM APIキーを設定してください（.envファイルがあればそちらが優先されます）
if "%ANTHROPIC_API_KEY%"=="" (
    if exist .env (
        for /f "tokens=1,* delims==" %%a in (.env) do (
            if "%%a"=="ANTHROPIC_API_KEY" set ANTHROPIC_API_KEY=%%b
        )
    )
)
if "%ANTHROPIC_API_KEY%"=="" (
    echo [ERROR] ANTHROPIC_API_KEY が設定されていません。
    echo .env ファイルに ANTHROPIC_API_KEY=sk-ant-xxxxx を記載してください。
    echo.
    cmd /k
    exit /b 1
)

echo Starting analysis...
python analyzer.py %*
cmd /k
