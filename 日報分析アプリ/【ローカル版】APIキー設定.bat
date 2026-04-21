@echo off
chcp 65001 > nul
echo.
echo ============================================
echo   Anthropic API キー 環境変数登録
echo ============================================
echo.

:: 暗号化ファイルの存在確認
if not exist "%APPDATA%\MyKomon\apikey.enc" (
    echo エラー：APIキーの暗号化ファイルが見つかりません。
    echo 管理者に「管理者用APIキー暗号化.bat」の実行を依頼してください。
    pause
    exit /b
)

:: PowerShell でDPAPI復号して環境変数に登録
for /f "delims=" %%i in ('powershell -NoProfile -Command ^
  "Add-Type -AssemblyName System.Security;" ^
  "$b64 = Get-Content \"$env:APPDATA\MyKomon\apikey.enc\" -Encoding UTF8;" ^
  "$enc = [System.Convert]::FromBase64String($b64);" ^
  "$dec = [System.Security.Cryptography.ProtectedData]::Unprotect($enc, $null, 'CurrentUser');" ^
  "[System.Text.Encoding]::UTF8.GetString($dec)"') do set APIKEY=%%i

if "%APIKEY%"=="" (
    echo エラー：APIキーの復号に失敗しました。
    echo 管理者に再度「管理者用APIキー暗号化.bat」の実行を依頼してください。
    pause
    exit /b
)

setx ANTHROPIC_API_KEY "%APIKEY%" > nul

echo 完了しました。APIキーが環境変数に登録されました。
echo 次回から「起動.bat」を使うとAPIキーが自動入力されます。
echo.
pause
