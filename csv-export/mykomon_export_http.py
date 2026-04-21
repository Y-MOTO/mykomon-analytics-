"""
MyKomon 日報CSV自動エクスポート - HTTPリクエスト版（Playwright不要）
requests + BeautifulSoup でブラウザなしに動作する。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta

import requests
from bs4 import BeautifulSoup

BASE_DIR   = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

BASE_URL    = "https://www.mykomon.com"
LOGIN_URL   = f"{BASE_URL}/MyKomon/login.do"
EXPORT_PAGE = f"{BASE_URL}/groupware/downloadScheduleView?equipmentFlag=0"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
}

# ログインフォームのブラウザ情報hidden項目に入れる値
BROWSER_FIELDS = {
    "appVersion":      "5.0 (Windows NT 10.0; Win64; x64)",
    "appName":         "Netscape",
    "appMinorVersion": "0",
    "browserLanguage": "ja",
    "cpuClass":        "unknown",
    "language":        "ja",
    "platform":        "Win32",
    "systemLanguage":  "ja",
    "userAgent":       HEADERS["User-Agent"],
    "javaEnabled":     "false",
    "taintEnabled":    "false",
    "online":          "true",
    "screenWidth":     "1920",
    "screenHeight":    "1080",
    "browserFlag":     "0",
}


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    if not cfg.get("username") or not cfg.get("password"):
        print("エラー: config.json にユーザー名とパスワードを設定してください。")
        sys.exit(1)
    return cfg


def make_session():
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def login(session, username, password):
    print("ログイン中...")

    # ログインページを取得してhidden項目・Cookieを収集
    resp = session.get(LOGIN_URL, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", id="loginFrm")

    data = {}
    if form:
        for inp in form.find_all("input"):
            name = inp.get("name")
            if name:
                data[name] = inp.get("value", "")

    # 認証情報とブラウザ情報を上書き
    data["loginname"] = username
    data["pass"]      = password
    data.update({k: v for k, v in BROWSER_FIELDS.items() if k in data or not data})

    resp = session.post(
        LOGIN_URL, data=data, timeout=30,
        headers={"Referer": LOGIN_URL,
                 "Content-Type": "application/x-www-form-urlencoded"},
        allow_redirects=True,
    )
    resp.raise_for_status()

    # ログイン失敗チェック（ログインページに戻ってきた場合）
    if "loginFrm" in resp.text:
        raise RuntimeError("ログイン失敗: ユーザー名またはパスワードが正しくありません。")

    print(f"ログイン完了 → {resp.url}")
    return session


def export_csv(session, year, month, save_dir):
    print(f"エクスポートページを取得中: {year}年{month}月")

    resp = session.get(EXPORT_PAGE, timeout=30)
    resp.raise_for_status()

    # エクスポートページのHTMLをデバッグ用に保存
    debug_path = BASE_DIR / "debug_export_page.html"
    debug_path.write_text(resp.text, encoding="utf-8")
    print(f"エクスポートページHTML保存: {debug_path}")

    soup = BeautifulSoup(resp.text, "html.parser")

    # フォームを探す（エクスポートフォーム）
    form = soup.find("form")
    if not form:
        raise RuntimeError("エクスポートフォームが見つかりません。HTMLを確認してください。")

    action = form.get("action", "")
    if not action.startswith("http"):
        action = BASE_URL + ("" if action.startswith("/") else "/") + action
    print(f"フォームアクション: {action}")

    # フォームデータを収集
    data = {}
    for inp in form.find_all("input"):
        name      = inp.get("name")
        inp_type  = inp.get("type", "text").lower()
        value     = inp.get("value", "")
        if not name or inp_type in ("submit", "button", "image"):
            continue
        if inp_type == "radio":
            if inp.get("checked") is not None:
                data[name] = value
        elif inp_type == "checkbox":
            if inp.get("checked") is not None:
                data[name] = value
        else:
            data[name] = value

    # セレクトボックスの処理（年・月を設定）
    for sel in form.find_all("select"):
        name = sel.get("name")
        if not name:
            continue
        options = [o.get("value", "") for o in sel.find_all("option") if o.get("value")]
        # 年セレクト（4桁数字）
        if any(len(v) == 4 and v.isdigit() for v in options):
            data[name] = str(year)
        # 月セレクト（1〜12）
        elif any(v in [str(m) for m in range(1, 13)] for v in options):
            data[name] = str(month)
        else:
            # 選択済みの値をデフォルトに
            selected = sel.find("option", selected=True)
            data[name] = selected.get("value", "") if selected else (options[0] if options else "")

    # 年月を明示的に上書き（YYYY/MM形式）
    ym = f"{year}/{month:02d}"
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    for key in list(data.keys()):
        if "fromYearMonth" in key or "FromYearMonth" in key:
            data[key] = ym
        elif "toYearMonth" in key or "ToYearMonth" in key:
            data[key] = ym
        elif "toDateInput" in key or "ToDateInput" in key:
            data[key] = f"{year}/{month:02d}/{last_day}"
        elif "fromDay" in key or "FromDay" in key:
            data[key] = "1"

    print(f"送信データ: {data}")
    print("エクスポート実行中...")

    resp = session.post(action, data=data, timeout=60, stream=True,
                        headers={"Referer": EXPORT_PAGE})
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    print(f"レスポンスContent-Type: {content_type}")

    if "text/html" in content_type:
        # 失敗：HTMLが返ってきた場合はデバッグ用に保存
        err_path = BASE_DIR / "debug_export_error.html"
        err_path.write_text(resp.text, encoding="utf-8")
        raise RuntimeError(
            f"CSVではなくHTMLが返されました。エクスポート設定を確認してください。\n"
            f"詳細: {err_path}"
        )

    filename  = f"日報_{year}{month:02d}.csv"
    save_path = Path(save_dir) / filename
    save_path.parent.mkdir(parents=True, exist_ok=True)

    with open(save_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"保存完了: {save_path}")
    return str(save_path)


def main(year=None, month=None):
    cfg = load_config()

    if year is None or month is None:
        months_back = int(cfg.get("months_back", 1))
        target = datetime.now() - relativedelta(months=months_back)
        year, month = target.year, target.month

    session = make_session()
    login(session, cfg["username"], cfg["password"])
    export_csv(session, year, month, cfg["save_dir"])
    print("完了しました。")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--year",  type=int, default=None)
    ap.add_argument("--month", type=int, default=None)
    args = ap.parse_args()
    main(year=args.year, month=args.month)
