import asyncio, random, re
from actions.common import safe_click, safe_click_xpath, press_space_n, sleep_ms, randi

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

async def close_cta_modal_if_any(page: Page) -> bool:
    return await safe_click(page, 'button[data-e2e="alt-middle-cta-cancel-btn"]', timeout_ms=3000)

async def close_exit_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='exit']", timeout_ms=1500)

async def close_profile_share_modal_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='close']", timeout_ms=1500)

async def click_author_avatar_if_any(page: Page) -> bool:
    return await safe_click(page, 'a[data-e2e="video-author-avatar"]', timeout_ms=3000)

def is_bridge_link(url: str) -> bool:
    return re.search(r"(onelink\.me|snssdk)", url, re.IGNORECASE) is not None

async def random_interact_in_profile(page: Page):
    SCROLL_TIMES = 5
    SCROLL_DELAY = (1000, 3000)
    WATCH_TIME = (5000, 15000)
    AFTER_WATCH_DELAY = (3000, 6000)

    # Scroll down profile
    for _ in range(SCROLL_TIMES):
        await page.mouse.wheel(0, 900)
        await sleep_ms(*SCROLL_DELAY)

    # Pick random video link on profile
    links = await page.locator('a[href*="/video/"]').all()
    if len(links) > 3:
        links = links[2:]

    if not links:
        return

    video = random.choice(links)

    try:
        await video.scroll_into_view_if_needed()
    except Exception:
        pass

    await sleep_ms(600, 1200)

    try:
        await video.hover()
        await sleep_ms(300, 700)
        await video.click()
    except Exception:
        return

    await sleep_ms(*WATCH_TIME)

    await page.mouse.move(randi(10, 400), randi(10, 400))
    await sleep_ms(*AFTER_WATCH_DELAY)

    try:
        await page.go_back()
    except Exception:
        await page.keyboard.press("Alt+Left")

async def run_tiktok_flow(
    page: Page,
    *,
    url: str = "https://www.tiktok.com/foryou",
    nav_timeout_ms: int = 60_000,
    action_timeout_ms: int = 15_000,
    will_view_min: int = 5,
    will_view_max: int = 15,
):
    page.set_default_navigation_timeout(nav_timeout_ms)
    page.set_default_timeout(action_timeout_ms)

    await page.goto(url, wait_until="domcontentloaded")

    await close_cta_modal_if_any(page)

    will_view_amount = randi(will_view_min, will_view_max)

    for _ in range(will_view_amount):
        random_scroll = randi(8, 20)

        await press_space_n(page, random_scroll, delay_min_ms=300, delay_max_ms=900)

        video_picked = randi(1, 3)

        if video_picked == 2:
            await sleep_ms(1000, 3000)
            await safe_click_xpath(page, "//*[@data-e2e='comment-icon']", timeout_ms=5000)

            has_bridge = False
            last = page.url
            end_time = asyncio.get_event_loop().time() + 3.0
            while asyncio.get_event_loop().time() < end_time:
                cur = page.url
                if cur != last:
                    last = cur
                    has_bridge = is_bridge_link(cur)
                await asyncio.sleep(0.3)

            if has_bridge:
                pass
            else:
                await close_exit_if_any(page)

        await press_space_n(page, random_scroll)

        await sleep_ms(1000, 3000)
        await click_author_avatar_if_any(page)
        await close_profile_share_modal_if_any(page)
        await page.keyboard.press("Space")

        await random_interact_in_profile(page)
