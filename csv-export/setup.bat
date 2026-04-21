@echo off
chcp 65001 > nul
echo ========================================
echo  MyKomon 日報CSV自動エクスポート セットアップ
echo ========================================
echo.

:: Python確認
python --version > nul 2>&1
if errorlevel 1 (
    echo エラー: Pythonがインストールされていません。
    echo https://www.python.org/ からPython 3.10以上をインストールしてください。
    pause
    exit /b 1
)

:: 依存パッケージインストール
echo 必要なパッケージをインストール中...
pip install playwright python-dateutil
if errorlevel 1 goto error

:: Playwrightブラウザインストール
echo Playwright（Edge）をセットアップ中...
playwright install msedge
if errorlevel 1 goto error

:: config.jsonの設定案内
echo.
echo ----------------------------------------
echo config.json を開いてユーザー名・パスワード・保存先を設定してください。
echo ----------------------------------------
start notepad "%~dp0config.json"
echo.

:: タスクスケジューラ登録確認
set /p REG="タスクスケジューラに毎月1日 AM9:00 の自動実行を登録しますか？ (y/n): "
if /i "%REG%"=="y" (
    schtasks /create /tn "MyKomon日報CSV取得" /xml "%~dp0task_scheduler.xml" /f
    if errorlevel 1 (
        echo タスクスケジューラの登録に失敗しました。管理者権限で実行してください。
    ) else (
        echo タスクスケジューラに登録しました。
    )
)

echo.
echo セットアップ完了。
echo 手動実行する場合は run.bat をダブルクリックしてください。
pause
exit /b 0

:error
echo エラーが発生しました。
pause
exit /b 1
