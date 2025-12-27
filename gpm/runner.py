import asyncio, requests
from typing import List, Tuple

from playwright.async_api import async_playwright
from utils import safe_print
from actions import run_tiktok_flow

async def _wait_cdp_http_ready(http_base: str, retries: int = 25, delay: float = 0.5) -> bool:
    url = http_base.rstrip("/") + "/json/version"

    def _try_once() -> bool:
        try:
            rr = requests.get(url, timeout=3)
            return rr.status_code == 200
        except Exception:
            return False

    for _ in range(retries):
        ok = await asyncio.to_thread(_try_once)
        if ok:
            return True
        await asyncio.sleep(delay)
    return False

async def _run_browser_one(p, name: str, addr: str):
    try:
        if addr.startswith("ws://"):
            browser = await p.chromium.connect(addr)
        else:
            ok = await _wait_cdp_http_ready(addr)
            if not ok:
                safe_print(f"❌ [{name}] CDP not ready (timeout): {addr}")
                return

            browser = await p.chromium.connect_over_cdp(addr)

        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        context.set_default_timeout(30_000)
        context.set_default_navigation_timeout(120_000)

        page = context.pages[0] if context.pages else await context.new_page()

        # await page.goto("https://whoer.net", wait_until="domcontentloaded")

        await run_tiktok_flow(page)
        safe_print(f"✅ [PW] {name}: done")

    except Exception as e:
        safe_print(f"❌ [PW] {name}: {e}")

async def run_all_playwright(pairs: List[Tuple[str, str]]):
    async with async_playwright() as p:
        await asyncio.gather(*(_run_browser_one(p, n, a) for n, a in pairs))
