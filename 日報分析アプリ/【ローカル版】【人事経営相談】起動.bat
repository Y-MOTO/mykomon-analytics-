@echo off
cd /d "%~dp0"
python -m streamlit run consult_app.py --server.port 8502
pause
