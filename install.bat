@echo off
chcp 65001 > nul
echo.
echo ============================================
echo  MyKomon 日報入力補助 インストーラー
echo ============================================
echo.

:: インストール先フォルダ
set DEST=%LOCALAPPDATA%\MKH-Extension

:: バッチファイルと同じフォルダにある拡張機能フォルダを取得
set SRC=%~dp0edge-extension

:: 既存のインストールを確認
if exist "%DEST%" (
  echo 既にインストールされています。最新版に更新します...
  rmdir /s /q "%DEST%"
)

:: コピー実行
echo 拡張機能をインストール中...
xcopy "%SRC%" "%DEST%" /e /i /q
if %errorlevel% neq 0 (
  echo.
  echo [エラー] コピーに失敗しました。
  echo 管理者にお問い合わせください。
  pause
  exit /b 1
)

echo インストール完了！
echo.
echo ============================================
echo  次の手順でEdgeに登録してください
echo ============================================
echo.
echo 1. 今からEdgeの拡張機能ページが開きます
echo 2. 右上の「開発者モード」をオンにする
echo 3. 「パッケージ化されていない拡張機能を読み込む」をクリック
echo 4. 以下のフォルダを選択してOKを押す
echo.
echo    %DEST%
echo.
echo ============================================
echo.
pause

:: Edgeの拡張機能ページを開く
start msedge "edge://extensions/"

echo.
echo フォルダのパスはメモしておいてください：
echo %DEST%
echo.
pause
