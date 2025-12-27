import asyncio, logging, math
from pathlib import Path
from typing import Optional, Dict, List, Tuple

from playwright.async_api import async_playwright, TimeoutError

from actions import run_tiktok_flow

MAX_CONCURRENT = 5
HEADLESS = False
PROXIES_FILE = "proxies.txt"

PROFILES_DIR = Path("profiles")
PROFILES_DIR.mkdir(exist_ok=True)

GRID_COLS = 3
MARGIN_X = 6
MARGIN_Y = 6
GAP_X = 6
GAP_Y = 12
WINDOW_W = 640
WINDOW_H = 520

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "proxies.log"
SHOT_DIR = LOG_DIR / "screens"
SHOT_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("proxy_runner")
logger.setLevel(logging.INFO)

if not logger.handlers:
    _fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    _console = logging.StreamHandler()
    _console.setFormatter(_fmt)
    logger.addHandler(_console)

    _file = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _file.setFormatter(_fmt)
    logger.addHandler(_file)

def load_proxies() -> List[str]:
    with open(PROXIES_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def parse_proxy(proxy_str: str) -> Optional[Dict[str, str]]:
    parts = proxy_str.split(":")
    if len(parts) != 4:
        logger.warning("Proxy sai định dạng: %s (expect ip:port:user:pass)", proxy_str)
        return None
    ip, port, user, pwd = parts
    return {"server": f"http://{ip}:{port}", "username": user, "password": pwd}

def grid_position(index0: int) -> Tuple[int, int]:
    col = index0 % GRID_COLS
    row = index0 // GRID_COLS
    x = MARGIN_X + col * (WINDOW_W + GAP_X)
    y = MARGIN_Y + row * (WINDOW_H + GAP_Y)
    return x, y

def profile_path_for(index1: int) -> Path:
    return PROFILES_DIR / f"proxy_{index1:03d}"

async def run_proxy(playwright, proxy: Dict[str, str], index1: int) -> None:
    idx0 = index1 - 1
    x, y = grid_position(idx0)
    user_data_dir = profile_path_for(index1)

    context = None
    page = None

    try:
        logger.info("[PROXY %s] Launching | %s | profile=%s", index1, proxy["server"], user_data_dir)

        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=HEADLESS,
            proxy=proxy,
            viewport={"width": WINDOW_W - 20, "height": WINDOW_H - 120},
            args=[
                f"--window-position={x},{y}",
                f"--window-size={WINDOW_W},{WINDOW_H}",
            ] if not HEADLESS else [],
        )

        context.set_default_timeout(30_000)
        context.set_default_navigation_timeout(120_000)

        page = context.pages[0] if context.pages else await context.new_page()

        await run_tiktok_flow(page)

    except TimeoutError:
        logger.error("[PROXY %s] TIMEOUT | %s", index1, proxy.get("server"))
        if page:
            try:
                await page.screenshot(path=str(SHOT_DIR / f"timeout_{index1:03d}.png"), full_page=True)
            except Exception:
                pass
    except Exception as e:
        logger.exception("[PROXY %s] ERROR | %s | %s", index1, proxy.get("server"), e)
        if page:
            try:
                await page.screenshot(path=str(SHOT_DIR / f"error_{index1:03d}.png"), full_page=True)
            except Exception:
                pass
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
            logger.info("[PROXY %s] CLOSED", index1)

async def main():
    proxies_raw = load_proxies()
    proxies: List[Dict[str, str]] = []
    for p in proxies_raw:
        px = parse_proxy(p)
        if px:
            proxies.append(px)

    if not proxies:
        logger.warning("Không có proxy hợp lệ trong %s", PROXIES_FILE)
        return

    total = len(proxies)
    rows = math.ceil(total / GRID_COLS)
    logger.info(
        "START | proxies=%s | workers=%s | headless=%s | grid=%sx%s",
        total, MAX_CONCURRENT, HEADLESS, rows, GRID_COLS
    )

    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async with async_playwright() as p:
        async def limited_run(px, i):
            async with sem:
                await run_proxy(p, px, i)

        await asyncio.gather(*(limited_run(px, i + 1) for i, px in enumerate(proxies)))

    logger.info("DONE ALL TASKS")

if __name__ == "__main__":
    asyncio.run(main())
