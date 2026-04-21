@echo off
cd /d "%~dp0"
echo Starting MyKomon analysis app...
python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
pause
