@echo off
chcp 65001 > nul
echo.
echo ============================================
echo   Anthropic API キー 初回設定
echo ============================================
echo.
echo Anthropic のサイト（https://console.anthropic.com）で
echo 取得した API キー（sk-ant- で始まる文字列）を
echo 貼り付けて Enter を押してください。
echo.
set /p APIKEY="API キー: "

if "%APIKEY%"=="" (
    echo キーが入力されませんでした。設定を中止します。
    pause
    exit /b
)

setx ANTHROPIC_API_KEY "%APIKEY%"

echo.
echo 設定が完了しました。
echo 次回から「起動.bat」を使うと API キーが自動入力されます。
echo （この設定は PC を再起動しても保持されます）
echo.
pause
