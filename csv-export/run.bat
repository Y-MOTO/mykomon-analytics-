@echo off
cd /d "%~dp0"
echo Starting mykomon_export.py ...
python mykomon_export.py
echo.
echo Exit code: %errorlevel%
pause
