import asyncio, random, time, re
from typing import Optional, Tuple

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

def randi(min_v: int, max_v: int) -> int:
    return random.randint(min_v, max_v)

def chance(p: float) -> bool:
    return random.random() < p

async def sleep_ms(min_ms: int, max_ms: int | None = None):
    if max_ms is None:
        ms = min_ms
    else:
        mu = (min_ms + max_ms) / 2
        sigma = max(1.0, (max_ms - min_ms) / 6)
        ms = int(random.gauss(mu, sigma))
        ms = max(min_ms, min(max_ms, ms))
    await asyncio.sleep(ms / 1000)

async def human_pause(min_ms: int = 250, max_ms: int = 900):
    await sleep_ms(min_ms, max_ms)

async def safe_click(page: Page, selector: str, *, timeout_ms: int = 3000) -> bool:
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout_ms)
        await loc.click()
        return True
    except PlaywrightTimeoutError:
        return False
    except Exception:
        return False

async def safe_click_xpath(page: Page, xpath: str, *, timeout_ms: int = 3000) -> bool:
    return await safe_click(page, f"xpath={xpath}", timeout_ms=timeout_ms)

async def safe_hover(page: Page, selector: str, *, timeout_ms: int = 2500) -> bool:
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout_ms)
        await loc.hover()
        return True
    except Exception:
        return False

async def safe_click_locator(loc: Locator, *, timeout_ms: int = 900) -> bool:
    try:
        target = loc.first

        if await target.count() == 0:
            return False
        if not await target.is_visible():
            return False

        try:
            if not await target.is_enabled():
                return False
        except Exception:
            pass

        await target.click(timeout=timeout_ms)
        return True

    except PlaywrightTimeoutError:
        return False
    except Exception:
        return False

async def jitter_mouse(
    page: Page,
    *,
    area: Tuple[int, int, int, int] = (40, 80, 980, 680),  # x1,y1,x2,y2
    steps_min: int = 2,
    steps_max: int = 6,
):
    x1, y1, x2, y2 = area
    steps = randi(steps_min, steps_max)

    for _ in range(steps):
        x = randi(x1, x2)
        y = randi(y1, y2)
        await page.mouse.move(x, y, steps=randi(10, 26))
        await sleep_ms(120, 520)

async def human_scroll_wheel(
    page: Page,
    total_px: int,
    *,
    step_range: Tuple[int, int] = (110, 240),
    pause_range: Tuple[int, int] = (160, 650),
    sometimes_hesitate: bool = True,
    sometimes_backtrack: bool = True,
):
    if total_px == 0:
        return

    remaining = abs(total_px)
    direction = 1 if total_px > 0 else -1

    while remaining > 0:
        step = min(remaining, randi(*step_range))
        jitter = randi(-25, 25)
        delta = direction * max(30, step + jitter)

        await page.mouse.wheel(0, delta)
        remaining -= step

        await sleep_ms(*pause_range)

        if sometimes_hesitate and chance(0.12):
            await sleep_ms(900, 2600)

        if sometimes_backtrack and chance(0.08):
            await page.mouse.wheel(0, -direction * randi(40, 120))
            await sleep_ms(140, 480)

async def watch_like_human(
    page: Page,
    *,
    min_ms: int = 5000,
    max_ms: int = 16000,
    mouse_jitter: bool = True,
):
    """
    Spend time "watching" with natural micro-pauses & tiny cursor moves.
    """
    total = randi(min_ms, max_ms)
    end = asyncio.get_event_loop().time() + (total / 1000)

    while asyncio.get_event_loop().time() < end:
        await sleep_ms(350, 900)

        if mouse_jitter and chance(0.22):
            await jitter_mouse(page, steps_min=1, steps_max=3)

        if chance(0.10):
            await sleep_ms(1200, 3600)

async def press_space_n(
    page: Page,
    n: int,
    *,
    delay_min_ms: int = 0,
    delay_max_ms: int = 0,
    # Humanization knobs
    watch_min_ms: int = 3500,
    watch_max_ms: int = 14000,
    humanize: bool = True,
):
    """
    Space-n for TikTok feed:
    - humanize=True adds watch time between spaces and occasional "oops" double-press.
    - delay_min_ms/delay_max_ms remain supported.
    """
    for i in range(n):
        if humanize:
            # first move can happen a bit quicker sometimes
            if i == 0 and chance(0.35):
                # short initial watch
                await sleep_ms(900, 4200)
            else:
                # actual "watch"
                await sleep_ms(watch_min_ms, watch_max_ms)

        # occasional accidental quick double press
        if humanize and chance(0.06):
            await page.keyboard.press("Space")
            await sleep_ms(80, 240)

        await page.keyboard.press("Space")

        if delay_max_ms > 0:
            await sleep_ms(delay_min_ms, delay_max_ms)

        if humanize:
            await sleep_ms(250, 1100)
            if chance(0.08):
                await sleep_ms(900, 2400)

def build_common_popup_locators(page: Page):
    """
    Priority-ordered locators to dismiss common popups.
    Add/remove as you see fit.
    """
    return [
        # Known close buttons from your project
        page.locator('button[data-e2e="alt-middle-cta-cancel-btn"]'),
        page.locator("[aria-label='exit']"),
        page.locator("[aria-label='close']"),

        page.get_by_role("button", name=re.compile(r"^Not now$", re.I)),
        page.locator("button:has-text('Not now')"),
        page.locator("button.TUXButton:has-text('Not now')"),

        page.get_by_role(
            "button",
            name=re.compile(r"maybe later|later|cancel|close|dismiss|skip|no thanks", re.I),
        ),
        page.locator("button:has-text('Maybe later')"),
        page.locator("button:has-text('Cancel')"),
        page.locator("button:has-text('Close')"),
        page.locator("button:has-text('Skip')"),
        page.locator("button:has-text('No thanks')"),

        page.locator("button[aria-label*='close' i]"),
        page.locator("button[aria-label*='dismiss' i]"),
    ]

async def popup_watcher(
    page: Page,
    *,
    poll_s: float = 0.25,
    global_cooldown_s: float = 1.2,
    per_target_cooldown_s: float = 2.5,
):
    """
    Background task:
    - auto-detect popups and click them
    - flow chính vẫn chạy bình thường
    - cooldown để không spam click
    """
    locators = build_common_popup_locators(page)
    last_global_click = 0.0
    last_click_by_idx: dict[int, float] = {}

    while True:
        try:
            if page.is_closed():
                return

            now = time.monotonic()
            if now - last_global_click < global_cooldown_s:
                await asyncio.sleep(poll_s)
                continue

            clicked = False

            for idx, loc in enumerate(locators):
                last = last_click_by_idx.get(idx, 0.0)
                if now - last < per_target_cooldown_s:
                    continue

                ok = await safe_click_locator(loc, timeout_ms=650)
                if ok:
                    t = time.monotonic()
                    last_global_click = t
                    last_click_by_idx[idx] = t
                    clicked = True
                    break

            await asyncio.sleep(0.4 if clicked else poll_s)

        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0.5)

def start_popup_watcher(page: Page) -> asyncio.Task:
    return asyncio.create_task(popup_watcher(page))

async def stop_popup_watcher(task: Optional[asyncio.Task]):
    if not task:
        return
    task.cancel()
    try:
        await task
    except Exception:
        pass