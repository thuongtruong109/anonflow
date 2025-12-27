import asyncio, random

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

def randi(min_v: int, max_v: int) -> int:
    return random.randint(min_v, max_v)

async def sleep_ms(min_ms: int, max_ms: int | None = None):
    ms = min_ms if max_ms is None else randi(min_ms, max_ms)
    await asyncio.sleep(ms / 1000)

async def safe_click(page: Page, selector: str, *, timeout_ms: int = 3000) -> bool:
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout_ms)
        await loc.click()
        return True
    except PlaywrightTimeoutError:
        return False

async def safe_click_xpath(page: Page, xpath: str, *, timeout_ms: int = 3000) -> bool:
    return await safe_click(page, f"xpath={xpath}", timeout_ms=timeout_ms)

async def press_space_n(page: Page, n: int, *, delay_min_ms: int = 0, delay_max_ms: int = 0):
    for _ in range(n):
        await page.keyboard.press("Space")
        if delay_max_ms > 0:
            await sleep_ms(delay_min_ms, delay_max_ms)