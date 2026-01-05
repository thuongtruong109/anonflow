import json
from playwright.async_api import Page
from actions.common import sleep_ms, safe_click_xpath
from utils import safe_print
from config import COOKIE_IMPORTER_EXTENSION_ID
from urllib.parse import quote

EXT_URL = f"chrome-extension://{COOKIE_IMPORTER_EXTENSION_ID}/index.html"

async def import_txt_cookie(page: Page, profile_name: str, cookie_path: str) -> bool:
    ext_page = await page.context.new_page()
    try:
        await ext_page.goto(EXT_URL, wait_until="domcontentloaded")

        clear_button = ext_page.locator('css=button#clear-all-data-btn').first
        await clear_button.wait_for(state="attached", timeout=8000)
        await clear_button.wait_for(state="visible", timeout=8000)
        await clear_button.click()
        await sleep_ms(1000, 1500)

        file_input = ext_page.locator('css=input#files[type="file"]').first
        await file_input.wait_for(state="attached", timeout=8000)
        await file_input.wait_for(state="visible", timeout=8000)
        await file_input.set_input_files(cookie_path)
        await sleep_ms(1000, 1500)

        for p in page.context.pages:
            if p != page:
                await p.close()

        username = profile_name.lstrip("@").strip()
        profile_url = f"https://www.tiktok.com/@{quote(username)}"
        await page.goto(profile_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        return True

    finally:
        safe_print(f"✅ Imported cookies for {profile_name}")

async def import_json_cookie(page: Page, profile_name: str, cookie_path: str) -> bool:
    ext_page = await page.context.new_page()
    with open(cookie_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    try:
        await ext_page.goto(EXT_URL, wait_until="domcontentloaded")

        ok = await safe_click_xpath(
            ext_page,
            "/html/body/nav/div/div[2]/button",
            timeout_ms=8000
        )
        if not ok:
            return False

        input_loc = ext_page.locator('xpath=//*[@id="import_content"]').first
        await input_loc.wait_for(state="visible", timeout=8000)
        await input_loc.click()
        await input_loc.fill(json.dumps(data))

        submit_btn = ext_page.locator(
            "button.js-cookie-import-execute-button"
        ).first

        await submit_btn.wait_for(state="visible", timeout=8000)
        await submit_btn.click()

        await sleep_ms(1000, 1500)

        for p in page.context.pages:
            if p != page:
                await p.close()

        username = profile_name.lstrip("@").strip()
        profile_url = f"https://www.tiktok.com/@{quote(username)}"
        await page.goto(profile_url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        return True

    finally:
        safe_print(f"✅ Imported cookies for {profile_name}")