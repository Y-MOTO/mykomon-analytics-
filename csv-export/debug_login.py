"""
ログインページのフォーム要素を調査するデバッグスクリプト
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent
LOGIN_URL = "https://www.mykomon.com/app/homeAo"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False)
        context = browser.new_context()
        page = context.new_page()

        print(f"ログインページへ移動: {LOGIN_URL}")
        page.goto(LOGIN_URL, wait_until="networkidle")

        print(f"\n現在のURL: {page.url}")
        print(f"ページタイトル: {page.title()}")

        # スクリーンショット保存
        screenshot_path = BASE_DIR / "login_screenshot.png"
        page.screenshot(path=str(screenshot_path))
        print(f"\nスクリーンショット保存: {screenshot_path}")

        # すべてのinput要素を列挙
        inputs = page.locator("input").all()
        print(f"\n=== input要素一覧 ({len(inputs)}個) ===")
        for inp in inputs:
            attrs = {}
            for attr in ["id", "name", "type", "class", "placeholder"]:
                val = inp.get_attribute(attr)
                if val:
                    attrs[attr] = val
            print(f"  {attrs}")

        # すべてのform要素
        forms = page.locator("form").all()
        print(f"\n=== form要素一覧 ({len(forms)}個) ===")
        for form in forms:
            action = form.get_attribute("action") or ""
            id_ = form.get_attribute("id") or ""
            print(f"  action={action}, id={id_}")

        print("\n--- 調査完了。ブラウザを閉じるには Enterキーを押してください ---")
        input()
        context.close()
        browser.close()


if __name__ == "__main__":
    main()
