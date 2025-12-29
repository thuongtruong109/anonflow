import json
from playwright.async_api import Page
from actions.common import safe_click_xpath, sleep_ms
from utils import safe_print

EXT_URL = "chrome-extension://bgffajlinmbdcileomeilpihjdgjiphb/index.html"

async def import_cookie(page: Page, profile_name: str, cookie_path: str) -> bool:
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

        return True

    finally:
        await sleep_ms(800, 1500)
        safe_print(f"✅ Imported cookies for {profile_name}")
        await ext_page.close()
