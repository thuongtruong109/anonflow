from playwright.async_api import Page
from actions.common import sleep_ms
from utils import safe_print
from config import EXTENSION_ID

EXT_URL = f"chrome-extension://{EXTENSION_ID}/index.html"

async def import_cookie(page: Page, profile_name: str, cookie_path: str) -> bool:
    ext_page = await page.context.new_page()
    try:
        await ext_page.goto(EXT_URL, wait_until="domcontentloaded")

        file_input = ext_page.locator('css=input#files[type="file"]').first
        await file_input.wait_for(state="attached", timeout=8000)

        await file_input.wait_for(state="visible", timeout=8000)

        await file_input.set_input_files(cookie_path)
        await sleep_ms(500, 1000)
        return True

    finally:
        await sleep_ms(800, 1500)
        safe_print(f"✅ Imported cookies for {profile_name}")
        await ext_page.close()
