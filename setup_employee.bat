@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Work Monitor - セットアップ
echo ============================================
echo.

REM --- 従業員名を入力 ---
set /p EMP_NAME="従業員名を入力してください: "
if "%EMP_NAME%"=="" (
    echo エラー: 名前が入力されていません
    pause
    exit /b 1
)

REM --- config.json を作成 ---
echo {"employee_name": "%EMP_NAME%"} > config.json
echo [OK] config.json を作成しました (%EMP_NAME%)

REM --- スタートアップに登録 ---
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT=%STARTUP%\WorkMonitor.vbs

echo Set ws = CreateObject("WScript.Shell") > "%SHORTCUT%"
echo ws.Run """%~dp0work_recorder.exe""", 0, False >> "%SHORTCUT%"

echo [OK] Windows起動時に自動実行を登録しました
echo     %SHORTCUT%
echo.

REM --- 今すぐ起動するか確認 ---
set /p START_NOW="今すぐ録画を開始しますか？ (Y/N): "
if /i "%START_NOW%"=="Y" (
    start "" "%~dp0work_recorder.exe"
    echo [OK] 録画を開始しました
)

echo.
echo ============================================
echo   セットアップ完了！
echo   PCを再起動しても自動で記録が始まります
echo ============================================
pause
