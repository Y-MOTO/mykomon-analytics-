@echo off
cd /d "%~dp0"
echo Installing packages...
python -m pip install -r requirements.txt
echo.
echo Done. Now run start.bat to launch the app.
pause
