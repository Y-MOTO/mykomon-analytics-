"""
エクスポートページのボタン要素を調査するデバッグスクリプト
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
LOGIN_URL = "https://www.mykomon.com/MyKomon/welcome.do"
EXPORT_URL = "https://www.mykomon.com/groupware/downloadScheduleView?equipmentFlag=0"


def main():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("ログイン中...")
        page.goto("https://www.mykomon.com/MyKomon/login.do", wait_until="networkidle")
        page.wait_for_selector("input[name='loginname']", timeout=10000)
        page.fill("input[name='loginname']", cfg["username"])
        page.fill("input[name='pass']", cfg["password"])
        page.evaluate("document.getElementById('loginFrm').submit()")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        print(f"ログイン後URL: {page.url}")

        # ログイン直後のダイアログ（確認しました）を閉じる
        try:
            btn = page.locator("button:has-text('確認しました')")
            if btn.count() > 0:
                print("確認ダイアログを閉じます...")
                btn.click()
                page.wait_for_timeout(1500)
                print(f"ダイアログ閉じた後のURL: {page.url}")
        except Exception as e:
            print(f"ダイアログ処理スキップ: {e}")

        print(f"\nエクスポートページへ移動...")
        page.goto(EXPORT_URL, wait_until="networkidle")
        print(f"現在のURL: {page.url}")

        # スクリーンショット
        ss_path = BASE_DIR / "export_screenshot.png"
        page.screenshot(path=str(ss_path))
        print(f"スクリーンショット保存: {ss_path}")

        # ボタン・サブミット要素を列挙
        print("\n=== button要素 ===")
        for btn in page.locator("button").all():
            print(f"  text={btn.text_content()!r}, type={btn.get_attribute('type')!r}")

        print("\n=== input[type=submit] ===")
        for inp in page.locator("input[type='submit']").all():
            print(f"  value={inp.get_attribute('value')!r}, name={inp.get_attribute('name')!r}")

        print("\n=== input[type=button] ===")
        for inp in page.locator("input[type='button']").all():
            print(f"  value={inp.get_attribute('value')!r}, name={inp.get_attribute('name')!r}, onclick={inp.get_attribute('onclick')!r}")

        print("\n=== a[href] (リンク) ===")
        for a in page.locator("a").all():
            text = a.text_content() or ""
            href = a.get_attribute("href") or ""
            if "export" in href.lower() or "download" in href.lower() or "csv" in text.lower() or "エクスポート" in text:
                print(f"  text={text.strip()!r}, href={href!r}")

        print("\n--- 調査完了。Enterキーで終了 ---")
        input()
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
