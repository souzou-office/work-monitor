@echo off
chcp 65001 >nul
echo ============================================
echo   Work Monitor - アンインストール
echo ============================================
echo.

REM --- 実行中のプロセスを停止 ---
taskkill /IM work_recorder.exe /F >nul 2>&1
if %errorlevel%==0 (
    echo [OK] 実行中のプロセスを停止しました
) else (
    echo [--] 実行中のプロセスはありませんでした
)

REM --- スタートアップから削除 ---
set SHORTCUT=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\WorkMonitor.vbs
if exist "%SHORTCUT%" (
    del "%SHORTCUT%"
    echo [OK] スタートアップ登録を解除しました
) else (
    echo [--] スタートアップ登録はありませんでした
)

echo.
echo ============================================
echo   アンインストール完了！
echo   EXEフォルダは手動で削除してください
echo ============================================
pause
