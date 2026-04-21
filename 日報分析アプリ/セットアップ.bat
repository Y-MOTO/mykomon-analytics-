@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ライブラリをインストールします...
pip install -r requirements.txt

echo.
echo 完了しました。「起動.bat」をダブルクリックしてアプリを起動してください。
pause
