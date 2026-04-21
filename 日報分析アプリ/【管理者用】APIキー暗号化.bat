@echo off
chcp 65001 > nul
echo.
echo ============================================
echo   Anthropic API キー 暗号化・登録（管理者用）
echo ============================================
echo.
echo このツールは所長のPCで管理者が1回だけ実行します。
echo APIキーをWindowsアカウントに紐付けて暗号化し、
echo 所長がキーを直接扱わなくて済む状態にします。
echo.
set /p APIKEY="API キーを貼り付けてEnter: "

if "%APIKEY%"=="" (
    echo キーが入力されませんでした。処理を中止します。
    pause
    exit /b
)

:: 保存先フォルダを作成
mkdir "%APPDATA%\MyKomon" 2>nul

:: PowerShell でDPAPI暗号化して保存 + 環境変数に登録
powershell -NoProfile -Command ^
  "Add-Type -AssemblyName System.Security;" ^
  "$key = [System.Text.Encoding]::UTF8.GetBytes('%APIKEY%');" ^
  "$enc = [System.Security.Cryptography.ProtectedData]::Protect($key, $null, 'CurrentUser');" ^
  "$b64 = [System.Convert]::ToBase64String($enc);" ^
  "Set-Content -Path \"$env:APPDATA\MyKomon\apikey.enc\" -Value $b64 -Encoding UTF8;" ^
  "Write-Host '暗号化ファイルを保存しました。'"

:: 環境変数にも登録（即時有効）
setx ANTHROPIC_API_KEY "%APIKEY%" > nul

echo.
echo ============================================
echo  完了しました。
echo  - APIキーは暗号化されてPCに保存されました
echo  - 環境変数 ANTHROPIC_API_KEY も登録済みです
echo  - このBATファイルは所長のPCから削除してください
echo ============================================
echo.
pause
