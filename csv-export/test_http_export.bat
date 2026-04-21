@echo off
cd /d "%~dp0"
echo HTTPリクエスト版エクスポートをテスト中...
python -m pip install requests beautifulsoup4 python-dateutil -q
python mykomon_export_http.py --year 2026 --month 2
pause
