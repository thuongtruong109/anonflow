import asyncio, random, re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

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
    start_popup_watcher,
    stop_popup_watcher,
)
from comment import TextRandomizer

# Helper functions cho logging
def _log_action(log_file: str, username: str, video_url: str, action_details: str = ""):
    """Ghi log action vào file"""
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] User: {username} | Video: {video_url}"

        if action_details:
            log_entry += f" | {action_details}"

        log_entry += "\n"

        log_path = log_dir / log_file
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error logging to {log_file}: {e}")

def _with_lang_param(url: str, lang: str = "en") -> str:
    try:
        p = urlparse(url)
        q = parse_qs(p.query)
        q["lang"] = [lang]
        new_query = urlencode(q, doseq=True)
        return urlunparse((p.scheme, p.netloc, p.path, p.params, new_query, p.fragment))
    except Exception:
        return url

async def check_login_status(page: Page, username: str = "unknown") -> bool:
    """
    Kiểm tra xem user đã login chưa bằng cách tìm activity button.

    Returns:
        True nếu đã login (tìm thấy activity button)
        False nếu chưa login (không tìm thấy activity button)
    """
    try:
        # Selector cho activity button
        activity_button_selector = 'button[data-e2e="nav-activity"][aria-label="Activity"]'

        try:
            activity_btn = page.locator(activity_button_selector).first
            if await activity_btn.count() > 0 and await activity_btn.is_visible():
                # Tìm thấy activity button -> đã đăng nhập
                if username and username != "unknown":
                    _log_action("login.log", username, page.url, "Login status: true")
                return True
        except Exception:
            pass

        # Không tìm thấy activity button -> chưa đăng nhập
        if username and username != "unknown":
            _log_action("login.log", username, page.url, "Login status: false")
        return False

    except Exception:
        # Nếu có lỗi, giả định là chưa login để skip like/comment nhưng vẫn thực hiện các hành vi khác
        return False

async def close_cta_modal_if_any(page: Page) -> bool:
    return await safe_click(page, 'button[data-e2e="alt-middle-cta-cancel-btn"]', timeout_ms=3000)

async def close_exit_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='exit']", timeout_ms=2000)

async def close_profile_share_modal_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='close']", timeout_ms=2000)

async def click_author_avatar_if_any(page: Page) -> bool:
    return await safe_click(page, 'a[data-e2e="video-author-avatar"]', timeout_ms=3500)

async def random_like_video(page: Page, username: str = "unknown") -> bool:
    """
    Thực hiện like video hiện tại.

    Hỗ trợ 2 loại like button:
    1. Feed video: span[data-e2e="like-icon"]
    2. Profile video: span[data-e2e="browse-like-icon"]

    Args:
        page: Playwright Page object
        username: Tên người dùng thực hiện action (để log)

    Returns:
        True nếu like thành công, False nếu không.
    """
    await sleep_ms(500, 1200)

    # Selector cho like button (theo thứ tự ưu tiên)
    # 1. Video feed ngoài profile: span[data-e2e="like-icon"]
    # 2. Video trong profile: span[data-e2e="browse-like-icon"]
    like_button_selectors = [
        'span[data-e2e="like-icon"]',         # Feed video
        'span[data-e2e="browse-like-icon"]',  # Profile video
    ]

    like_success = False

    for selector in like_button_selectors:
        try:
            like_btn = page.locator(selector).first
            if await like_btn.count() > 0 and await like_btn.is_visible():
                # Kiểm tra xem đã like chưa bằng cách check parent element hoặc SVG fill color
                try:
                    # TikTok thường thay đổi class hoặc thuộc tính khi đã like
                    # Có thể check SVG fill color (red = đã like, white/gray = chưa like)
                    parent = like_btn.locator('..').first
                    parent_classes = await parent.get_attribute("class") or ""

                    # Hoặc check aria-pressed nếu có
                    aria_pressed = await like_btn.get_attribute("aria-pressed")
                    if aria_pressed == "true":
                        # Đã like rồi
                        return False

                    # Check trong class name xem có chứa "liked" hoặc "active"
                    if "liked" in parent_classes.lower() or "active" in parent_classes.lower():
                        return False
                except Exception:
                    pass

                await like_btn.click(timeout=2000)
                like_success = True
                await sleep_ms(800, 1500)

                # Log action - chỉ log khi có username thực sự (không phải "unknown")
                if username and username != "unknown":
                    video_url = page.url
                    _log_action("like.log", username, video_url, "Liked video")

                break
        except Exception:
            continue

    return like_success

async def random_comment_on_video(page: Page, username: str = "unknown", text_randomizer: TextRandomizer = None) -> bool:
    """
    Thêm comment ngẫu nhiên vào video hiện tại.
    Hỗ trợ 2 loại selector:
    1. Comment trong profile video: div[data-e2e="comment-input"]
    2. Comment trong feed video: div.public-DraftEditorPlaceholder-inner

    Returns True nếu comment thành công, False nếu không.
    """
    if text_randomizer is None:
        # Khởi tạo TextRandomizer với ngôn ngữ tiếng Anh (có thể đổi sang "vi")
        text_randomizer = TextRandomizer(lang="en")

    # Sinh comment text ngẫu nhiên
    comment_text = text_randomizer.comment(
        context=random.choice(["generic", "like", "reply"]),
        tone=random.choice(["friendly", "enthusiastic", "polite"]),
        length=random.choice(["short", "medium"]),
        unique=True
    )

    await sleep_ms(800, 1500)

    # Thử click vào comment input (profile video)
    profile_comment_selector = 'div[data-e2e="comment-input"]'
    feed_comment_selector = 'div.public-DraftEditorPlaceholder-inner'

    comment_clicked = False

    # Thử selector cho profile video
    try:
        profile_input = page.locator(profile_comment_selector).first
        if await profile_input.count() > 0 and await profile_input.is_visible():
            await profile_input.click(timeout=3000)
            comment_clicked = True
            await sleep_ms(500, 1000)
    except Exception:
        pass

    # Nếu không thấy profile input, thử feed input
    if not comment_clicked:
        try:
            feed_input = page.locator(feed_comment_selector).first
            if await feed_input.count() > 0 and await feed_input.is_visible():
                await feed_input.click(timeout=3000)
                comment_clicked = True
                await sleep_ms(500, 1000)
        except Exception:
            pass

    if not comment_clicked:
        return False

    # Tìm text editor để nhập comment
    # TikTok sử dụng contenteditable div
    try:
        # Thử tìm text editor
        editor_selectors = [
            'div[data-e2e="comment-text"] div[contenteditable="true"]',
            'div[contenteditable="true"][data-text="true"]',
            'div.DraftEditor-editorContainer div[contenteditable="true"]',
        ]

        editor_found = False
        for selector in editor_selectors:
            try:
                editor = page.locator(selector).first
                if await editor.count() > 0:
                    # Focus vào editor
                    await editor.focus(timeout=2000)
                    await sleep_ms(300, 600)

                    # Gõ text từng ký tự với delay ngẫu nhiên (giống người thật)
                    for char in comment_text:
                        await page.keyboard.type(char, delay=random.randint(50, 150))

                    editor_found = True
                    await sleep_ms(800, 1500)
                    break
            except Exception:
                continue

        if not editor_found:
            return False

        # Submit comment: thử click nút Post trước, nếu không có thì nhấn Enter
        await sleep_ms(500, 1000)

        # Thử tìm và click nút Post (chỉ khi aria-disabled="false")
        post_button_clicked = False
        try:
            post_button = page.locator('div[data-e2e="comment-post"][aria-disabled="false"]').first
            if await post_button.count() > 0 and await post_button.is_visible():
                await post_button.click(timeout=2000)
                post_button_clicked = True
                await sleep_ms(1000, 2000)
        except Exception:
            pass

        # Nếu không click được nút Post, thử nhấn Enter
        if not post_button_clicked:
            try:
                await page.keyboard.press("Enter")
                await sleep_ms(1000, 2000)
            except Exception:
                pass

        # Log action - chỉ log khi có username thực sự (không phải "unknown")
        if username and username != "unknown":
            video_url = page.url
            _log_action("comment.log", username, video_url, f"Commented: {comment_text}")

        return True

    except Exception as e:
        return False

async def click_author_avatar_if_any(page: Page) -> bool:
    return await safe_click(page, 'a[data-e2e="video-author-avatar"]', timeout_ms=3500)

def is_bridge_link(url: str) -> bool:
    return re.search(r"(onelink\.me|snssdk)", url, re.IGNORECASE) is not None

async def random_interact_in_profile(page: Page, username: str = "unknown", is_logged_in: bool = True):
    """
    Human-ish profile browsing:
    - slow scroll chunks
    - occasional backtrack
    - hover, pause, open a random video

    Args:
        username: Tên profile/user thực hiện actions (để log)
        is_logged_in: Login status (để quyết định có thực hiện like/comment không)
    """
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

    await watch_like_human(page, min_ms=7000, max_ms=22000, mouse_jitter=True)
    await sleep_ms(1200, 5200)

    # Thêm hành vi like ngẫu nhiên (tỉ lệ cao hơn comment) - CHỈ KHI ĐÃ LOGIN
    if is_logged_in and chance(0.40):  # 40% cơ hội like
        await sleep_ms(600, 1400)
        like_success = await random_like_video(page, username=username)
        if like_success:
            await sleep_ms(800, 1800)

    # Thêm hành vi comment ngẫu nhiên khi xem video trong profile - CHỈ KHI ĐÃ LOGIN
    if is_logged_in and chance(0.30):  # 30% cơ hội comment (thấp hơn like một xíu)
        await sleep_ms(800, 1800)
        comment_success = await random_comment_on_video(page, username=username)
        if comment_success:
            await sleep_ms(1500, 3000)

    try:
        await page.go_back()
    except Exception:
        try:
            await page.keyboard.press("Alt+Left")
        except Exception:
            pass

async def run_tiktok_flow(
    page: Page,
    *,
    url: str = "https://www.tiktok.com/foryou",
    nav_timeout_ms: int = 60_000,
    action_timeout_ms: int = 15_000,
    will_view_min: int = 5,
    will_view_max: int = 15,
    username: str = "unknown",
):
    """
    More natural feed browsing:
    - watch time per video
    - small scroll adjustments
    - occasional comments open/close
    - occasional profile visit

    Args:
        username: Tên profile/user thực hiện actions (để log)
    """
    page.set_default_navigation_timeout(nav_timeout_ms)
    page.set_default_timeout(action_timeout_ms)

    # Thêm param ?lang=en vào URL trước khi navigate
    # url_with_lang = _with_lang_param(url, lang="en")
    # await page.goto(url_with_lang, wait_until="domcontentloaded")

    await page.goto(url, wait_until="domcontentloaded")

    # ✅ start watcher (background)
    watcher = start_popup_watcher(page)

    try:
        await close_cta_modal_if_any(page)

        # Kiểm tra login status trước khi thực hiện actions
        is_logged_in = await check_login_status(page, username=username)

        will_view_amount = randi(will_view_min, will_view_max)

        for _ in range(will_view_amount):
            # 1) watch current video naturally
            await watch_like_human(page, min_ms=6000, max_ms=20000, mouse_jitter=True)

            # 1.5) sometimes like the video (tỉ lệ cao) - CHỈ KHI ĐÃ LOGIN
            if is_logged_in and chance(0.35):  # 35% cơ hội like video
                await sleep_ms(600, 1400)
                like_success = await random_like_video(page, username=username)
                if like_success:
                    await sleep_ms(800, 1800)

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

                # Thêm hành vi comment ngẫu nhiên vào video feed - CHỈ KHI ĐÃ LOGIN
                if is_logged_in and chance(0.40):  # 40% cơ hội comment khi đã mở comment section
                    await sleep_ms(800, 1800)
                    comment_success = await random_comment_on_video(page, username=username)
                    if comment_success:
                        await sleep_ms(1500, 3000)

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
                    await random_interact_in_profile(page, username=username, is_logged_in=is_logged_in)
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
    finally:
        await stop_popup_watcher(watcher)
