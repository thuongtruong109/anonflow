import asyncio, random, re

from playwright.async_api import Page

from actions.common import (
    safe_click,
    safe_click_xpath,
    press_space_n,
    sleep_ms,
    randi,
    chance,
    human_scroll_wheel,
    jitter_mouse,
    watch_like_human,
)

# -----------------------------
# Small UI helpers
# -----------------------------
async def close_cta_modal_if_any(page: Page) -> bool:
    return await safe_click(page, 'button[data-e2e="alt-middle-cta-cancel-btn"]', timeout_ms=3000)


async def close_exit_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='exit']", timeout_ms=2000)


async def close_profile_share_modal_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='close']", timeout_ms=2000)


async def click_author_avatar_if_any(page: Page) -> bool:
    return await safe_click(page, 'a[data-e2e="video-author-avatar"]', timeout_ms=3500)


def is_bridge_link(url: str) -> bool:
    return re.search(r"(onelink\.me|snssdk)", url, re.IGNORECASE) is not None


# -----------------------------
# Profile interactions
# -----------------------------
async def random_interact_in_profile(page: Page):
    """
    Human-ish profile browsing:
    - slow scroll chunks
    - occasional backtrack
    - hover, pause, open a random video
    """
    # slow scroll profile
    scroll_rounds = randi(3, 7)
    for _ in range(scroll_rounds):
        await human_scroll_wheel(
            page,
            randi(700, 1500),
            step_range=(90, 210),
            pause_range=(180, 720),
            sometimes_hesitate=True,
            sometimes_backtrack=True,
        )
        if chance(0.18):
            await human_scroll_wheel(
                page,
                -randi(180, 460),
                step_range=(70, 150),
                pause_range=(160, 560),
            )
        await sleep_ms(700, 2200)

    # pick random video link on profile
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

    await sleep_ms(900, 2200)

    try:
        await video.hover()
        await sleep_ms(450, 1400)
        if chance(0.25):
            await jitter_mouse(page, steps_min=1, steps_max=2)
        await video.click()
    except Exception:
        return

    # watch naturally
    await watch_like_human(page, min_ms=7000, max_ms=22000, mouse_jitter=True)
    await sleep_ms(1200, 5200)

    # go back
    try:
        await page.go_back()
    except Exception:
        try:
            await page.keyboard.press("Alt+Left")
        except Exception:
            pass


# -----------------------------
# Main TikTok flow
# -----------------------------
async def run_tiktok_flow(
    page: Page,
    *,
    url: str = "https://www.tiktok.com/foryou",
    nav_timeout_ms: int = 60_000,
    action_timeout_ms: int = 15_000,
    will_view_min: int = 5,
    will_view_max: int = 15,
):
    """
    More natural feed browsing:
    - watch time per video
    - small scroll adjustments
    - occasional comments open/close
    - occasional profile visit
    """
    page.set_default_navigation_timeout(nav_timeout_ms)
    page.set_default_timeout(action_timeout_ms)

    await page.goto(url, wait_until="domcontentloaded")
    await close_cta_modal_if_any(page)

    will_view_amount = randi(will_view_min, will_view_max)

    for _ in range(will_view_amount):
        # 1) watch current video naturally
        await watch_like_human(page, min_ms=6000, max_ms=20000, mouse_jitter=True)

        # 2) small scroll nudges (not big jumps)
        if chance(0.55):
            await human_scroll_wheel(page, randi(160, 520), step_range=(70, 150), pause_range=(120, 420))
        if chance(0.10):
            await human_scroll_wheel(page, -randi(120, 260), step_range=(60, 120), pause_range=(120, 420))

        # 3) sometimes open comments briefly
        if chance(0.22):
            await sleep_ms(900, 2400)
            await safe_click_xpath(page, "//*[@data-e2e='comment-icon']", timeout_ms=6000)

            # "read" comments
            await sleep_ms(1800, 6000)

            # small comment scroll
            if chance(0.35):
                await human_scroll_wheel(page, randi(220, 700), step_range=(90, 170), pause_range=(160, 520))

            # detect possible bridge navigation
            has_bridge = False
            last = page.url
            end_time = asyncio.get_event_loop().time() + 3.0
            while asyncio.get_event_loop().time() < end_time:
                cur = page.url
                if cur != last:
                    last = cur
                    has_bridge = is_bridge_link(cur)
                await asyncio.sleep(0.3)

            if not has_bridge:
                await close_exit_if_any(page)

        # 4) sometimes visit author profile and interact
        if chance(0.18):
            await sleep_ms(900, 2600)
            ok = await click_author_avatar_if_any(page)
            if ok:
                await close_profile_share_modal_if_any(page)
                await sleep_ms(800, 2200)
                await random_interact_in_profile(page)
                await sleep_ms(700, 2000)

        # 5) go next video: ONE space, with a tiny pause after
        await page.keyboard.press("Space")
        await sleep_ms(900, 2400)

        # optional: rare "fast swipe streak" (still human-ish) using press_space_n
        if chance(0.06):
            await press_space_n(
                page,
                randi(1, 2),
                delay_min_ms=400,
                delay_max_ms=1300,
                watch_min_ms=2200,
                watch_max_ms=6500,
                humanize=True,
            )
