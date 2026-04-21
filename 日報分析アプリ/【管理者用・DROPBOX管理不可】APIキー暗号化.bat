@echo off
chcp 65001 > nul

:: ============================================
::  ★ 管理者がここにAPIキーを書いてください ★
::  実行後このファイルは所長PCから必ず削除すること
:: ============================================
set APIKEY=ここにAPIキーを貼り付ける

:: ============================================
::  以下は編集不要
:: ============================================

echo.
echo ============================================
echo   Anthropic API キー 暗号化・登録（管理者用）
echo ============================================
echo.

if "%APIKEY%"=="ここにAPIキーを貼り付ける" (
    echo エラー：APIキーが設定されていません。
    echo BATファイルを右クリック→「メモ帳で編集」で開き、
    echo set APIKEY= の行にAPIキーを貼り付けてから再実行してください。
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

setx ANTHROPIC_API_KEY "%APIKEY%" > nul

echo.
echo ============================================
echo  完了しました。
echo  - APIキーは暗号化されてPCに保存されました
echo  - 環境変数 ANTHROPIC_API_KEY も登録済みです
echo  ----------------------------------------
echo  ★ このBATファイルを今すぐ削除してください ★
echo ============================================
echo.
pause
