"""
MyKomon 日報CSV自動エクスポートスクリプト
Playwright for Python を使用
"""

import json
import os
import shutil
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

LOGIN_URL = "https://www.mykomon.com/MyKomon/login.do"
EXPORT_URL = "https://www.mykomon.com/groupware/downloadScheduleView?equipmentFlag=0"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)
    if not cfg.get("username") or not cfg.get("password"):
        print("エラー: config.json にユーザー名とパスワードを設定してください。")
        sys.exit(1)
    return cfg


def get_target_month(months_back: int):
    target = datetime.now() - relativedelta(months=months_back)
    return target.year, target.month


def login(page, username: str, password: str):
    print("ログイン中...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")

    # すでにログイン済みの場合はスキップ
    if EXPORT_URL.split("/groupware")[0] in page.url and "login" not in page.url.lower():
        if page.url == LOGIN_URL or "home" in page.url:
            print("ログイン済みを確認")
            return

    # ログインフォームを検出
    page.wait_for_selector("input[name='loginname']", timeout=10000)

    page.fill("input[name='loginname']", username)
    page.fill("input[name='pass']", password)
    page.evaluate("document.getElementById('loginFrm').submit()")
    try:
        page.wait_for_load_state("domcontentloaded", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(2000)

    # ログイン直後の確認ダイアログを閉じる
    try:
        btn = page.locator("button:has-text('確認しました')")
        if btn.count() > 0:
            btn.click()
            page.wait_for_timeout(1500)
    except Exception:
        pass

    print("ログイン完了")


def export_csv(page, year: int, month: int, download_dir: Path):
    print(f"エクスポートページへ移動: {year}年{month}月")
    page.goto(EXPORT_URL, wait_until="domcontentloaded")

    # 期間：月単位ラジオボタンを選択（最初のラジオ）
    radios = page.locator("input[type='radio']")
    if radios.count() > 0:
        radios.first.click()

    # 年月セレクトボックスを設定（開始・終了とも同じ月）
    year_str = str(year)
    month_str = str(month)

    year_selects = page.locator("select").filter(has_text=year_str)
    month_selects = page.locator("select")

    # セレクトボックスを全取得して年月を設定
    all_selects = page.locator("select")
    count = all_selects.count()
    for i in range(count):
        sel = all_selects.nth(i)
        options = sel.locator("option").all_text_contents()
        # 年セレクト（4桁数字の選択肢がある）
        if any(len(o.strip()) == 4 and o.strip().isdigit() for o in options):
            sel.select_option(year_str)
        # 月セレクト（1〜12の選択肢がある）
        elif any(o.strip() in [str(m) for m in range(1, 13)] for o in options):
            sel.select_option(month_str)

    # 業務分類：「すべて」ラジオを選択
    all_radios = page.locator("input[type='radio']")
    for i in range(all_radios.count()):
        r = all_radios.nth(i)
        val = r.get_attribute("value") or ""
        label = page.locator(f"label[for='{r.get_attribute('id')}']").text_content() if r.get_attribute("id") else ""
        if "すべて" in label or val in ["0", "all", ""]:
            try:
                r.click()
            except Exception:
                pass

    # ダウンロード処理
    print("エクスポートボタンをクリック...")
    with page.expect_download(timeout=60000) as download_info:
        page.locator("input[type='submit'][value*='エクスポート'], button:has-text('エクスポート')").click()

    download = download_info.value
    filename = f"日報_{year}{month:02d}.csv"
    save_path = download_dir / filename
    download.save_as(save_path)
    print(f"保存完了: {save_path}")
    return save_path


def main(year=None, month=None):
    cfg = load_config()
    save_dir = Path(cfg["save_dir"])
    save_dir.mkdir(parents=True, exist_ok=True)

    if year is None or month is None:
        months_back = int(cfg.get("months_back", 1))
        year, month = get_target_month(months_back)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            downloads_path=str(BASE_DIR / "tmp_downloads")
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        try:
            login(page, cfg["username"], cfg["password"])
            export_csv(page, year, month, save_dir)
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        finally:
            context.close()
            browser.close()

    print("完了しました。")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=None)
    ap.add_argument("--month", type=int, default=None)
    args = ap.parse_args()
    main(year=args.year, month=args.month)
