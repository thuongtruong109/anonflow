import asyncio, requests
from typing import List, Tuple, Dict, Any

from playwright.async_api import async_playwright
from actions.cookie import import_cookie
from utils import safe_print, copy_folder
from actions.behavior import run_tiktok_flow
import config

Job = Tuple[str, str, str]  # (profile_name, addr, cookie)

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

# async def _force_english(context, page):
#     """
#     Best-effort force English for most websites:
#     - navigator.language + languages
#     - (optionally) set cookie 'lang=en' for tiktok domains (safe no-op if not used)
#     """
#     # 1) Override navigator.language for JS checks
#     await context.add_init_script("""
#     Object.defineProperty(navigator, 'language', {get: () => 'en-US'});
#     Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
#     """)

#     # 2) TikTok commonly respects /?lang=en OR a cookie-based preference
#     #    We'll set a cookie on likely domains. If domain mismatch, it simply won't apply.
#     try:
#         await context.add_cookies([
#             {"name": "lang", "value": "en", "domain": ".tiktok.com", "path": "/"},
#             {"name": "language", "value": "en", "domain": ".tiktok.com", "path": "/"},
#         ])
#     except Exception:
#         pass

async def _run_browser_one(p, name: str, addr: str, cookie: str, actions: Dict[str, Any]):
    try:
        if not addr:
            safe_print(f"❌ [{name}] Missing addr")
            return

        if addr.startswith("ws://"):
            browser = await p.chromium.connect(addr)
            safe_print(f"✅ [{name}] Connected to CDP WS: {addr}")
        else:
            ok = await _wait_cdp_http_ready(addr)
            if not ok:
                safe_print(f"❌ [{name}] CDP not ready (timeout): {addr}")
                return
            browser = await p.chromium.connect_over_cdp(addr)
            safe_print(f"✅ [{name}] Connected to CDP HTTP: {addr}")

        context = browser.contexts[0] if browser.contexts else await browser.new_context(
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        context.set_default_timeout(30_000)
        context.set_default_navigation_timeout(120_000)

        page = context.pages[0] if context.pages else await context.new_page()

        # await _force_english(context, page)

        if actions.get("import"):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.connect_over_cdp(addr)
                    context = browser.contexts[0]
                    page = await context.new_page()
                    await import_cookie(page, name, cookie)
                    safe_print(f"✅ Imported cookie for {name}")
            except Exception as e:
                safe_print(f"❌ Import failed for {name}: {e}")

        if actions.get("start"):
            await run_tiktok_flow(page)

    except Exception as e:
        safe_print(f"❌ [PW] {name}: {e}")

async def run_all_playwright(jobs: List[Job], actions: Dict[str, Any]):
    if actions.get("import"):
        copy_folder(config.EXTENSIONS_DIR, config.GPM_EXTENSION_LOCATE)
        safe_print(f"✅ Extensions copied to GPM location")

    async with async_playwright() as p:
        await asyncio.gather(
            *(_run_browser_one(p, name, addr, cookie, actions) for name, addr, cookie in jobs),
            return_exceptions=True
        )