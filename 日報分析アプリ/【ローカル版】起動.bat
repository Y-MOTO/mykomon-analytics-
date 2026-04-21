@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo MyKomon 日報分析アプリを起動します...

python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

if errorlevel 1 (
    echo.
    echo エラーが発生しました。以下を確認してください：
    echo   1. pip install -r requirements.txt が完了しているか
    echo   2. Pythonが PATH に含まれているか
    pause
)
