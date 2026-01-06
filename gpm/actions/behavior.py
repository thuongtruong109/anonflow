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

TARGET_PIVOT = "https://www.tiktok.com/@moises2743"

# Global để lưu URL video hiện tại
_current_video_url = None

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


# async def inject_video_detector(page: Page) -> bool:
#     """
#     Inject JavaScript code để detect video đang xem hiện tại.
#     Script này sẽ tự động track video URL và expose qua console.

#     Returns:
#         True nếu inject thành công, False nếu không
#     """
#     try:
#         # Đọc nội dung file detect-video.js
#         script_path = Path(__file__).parent / "detect-video.js"

#         if not script_path.exists():
#             print(f"Warning: {script_path} not found")
#             return False

#         with open(script_path, "r", encoding="utf-8") as f:
#             js_code = f.read()

#         # Inject script vào page
#         await page.evaluate(js_code)
#         await sleep_ms(500, 800)
#         return True

#     except Exception as e:
#         print(f"Error injecting video detector: {e}")
#         return False


async def get_current_video_url(page: Page) -> str | None:
    """
    Lấy URL của video đang xem hiện tại từ JavaScript detector.

    Returns:
        URL của video hoặc None nếu không detect được
    """
    try:
        # Gọi hàm JavaScript để lấy current video URL
        js_code = r"""
        (() => {
          const BASE = "https://www.tiktok.com";

          const extractLongNumber = (s) => {
            const nums = (s || "").match(/\d{10,}/g);
            if (!nums) return null;
            return nums.sort((a, b) => b.length - a.length)[0];
          };

          const getActivePlayer = () => {
            const players = [...document.querySelectorAll(".tiktok-web-player")];
            if (!players.length) return null;

            for (const p of players) {
              const v = p.querySelector("video");
              if (v && !v.paused && !v.ended && v.currentTime > 0) return p;
            }

            const vpH = window.innerHeight;
            const visibleRatio = (el) => {
              const r = el.getBoundingClientRect();
              const visible = Math.max(0, Math.min(r.bottom, vpH) - Math.max(r.top, 0));
              return visible / Math.max(1, r.height);
            };

            return players.sort((a, b) => visibleRatio(b) - visibleRatio(a))[0];
          };

          const findUsernameNear = (root) => {
            let node = root;
            for (let i = 0; i < 12 && node; i++) {
              const links = [...(node.querySelectorAll?.('a[href^="/@"]') || [])];
              for (const a of links) {
                const href = a.getAttribute("href") || "";
                const m = href.match(/^\/@([^/?#]+)/);
                if (m?.[1]) return m[1];
              }
              node = node.parentElement;
            }
            return null;
          };

          const player = getActivePlayer();
          if (!player) return null;

          const videoId = extractLongNumber(player.id);
          if (!videoId) return null;

          const username = findUsernameNear(player);
          return username
            ? `${BASE}/@${username}/video/${videoId}`
            : `${BASE}/video/${videoId}`;
        })();
        """

        video_url = await page.evaluate(js_code)
        return video_url if video_url else None

    except Exception as e:
        return None


async def track_and_log_video(page: Page, username: str = "unknown") -> None:
    global _current_video_url

    try:
        video_url = await get_current_video_url(page)

        if video_url and video_url != _current_video_url:
            _current_video_url = video_url

            if username and username != "unknown":
                _log_action("like.log", username, video_url, "Now watching")

    except Exception as e:
        pass


async def check_login_status(page: Page, username: str = "unknown") -> bool:
    try:
        # Wait a bit for the page to load elements (TikTok can be slow)
        await sleep_ms(2000, 4000)

        logged_in_selector = '[data-e2e="edit-profile-entrance"]'
        not_logged_in_selector = '[data-e2e="follow-button"]'

        # Additional potential selectors (based on common TikTok patterns; verify via browser inspect)
        alt_logged_in_selectors = [
            '[data-e2e="profile-edit-button"]',  # Alternative edit button
            'a[href*="/setting"]',  # Settings link often present when logged in
        ]
        alt_not_logged_in_selectors = [
            '[data-e2e="nav-profile"]',  # Profile nav might differ
        ]

        # Check primary logged-in selector
        logged_in_el = page.locator(logged_in_selector).first
        if await logged_in_el.count() > 0 and await logged_in_el.is_visible():
            if username and username != "unknown":
                _log_action(
                    "login.log",
                    username,
                    page.url,
                    "Login status: true (edit-profile-entrance found)"
                )
            return True

        # Check alternative logged-in selectors
        for selector in alt_logged_in_selectors:
            el = page.locator(selector).first
            if await el.count() > 0 and await el.is_visible():
                if username and username != "unknown":
                    _log_action(
                        "login.log",
                        username,
                        page.url,
                        f"Login status: true"
                    )
                return True

        # Check not-logged-in selectors
        not_logged_in_el = page.locator(not_logged_in_selector).first
        if await not_logged_in_el.count() > 0 and await not_logged_in_el.is_visible():
            if username and username != "unknown":
                _log_action(
                    "login.log",
                    username,
                    page.url,
                    "Login status: false"
                )
            return False

        # Check alternative not-logged-in selectors
        for selector in alt_not_logged_in_selectors:
            el = page.locator(selector).first
            if await el.count() > 0 and await el.is_visible():
                if username and username != "unknown":
                    _log_action(
                        "login.log",
                        username,
                        page.url,
                        f"Login status: false"
                    )
                return False

        # Fallback: If on own profile and no follow button, assume logged in (but log for review)
        # This is a heuristic—test carefully to avoid false positives
        if username and username != "unknown" and f"/@{username}" in page.url:
            follow_check = page.locator('[data-e2e="follow-button"]')
            if await follow_check.count() == 0:
                _log_action(
                    "login.log",
                    username,
                    page.url,
                    "Login status: true (fallback: no follow button on own profile)"
                )
                return True

        # No match found
        if username and username != "unknown":
            _log_action(
                "login.log",
                username,
                page.url,
                "Login status: false (no matching element)"
            )
        return False

    except Exception as e:
        if username and username != "unknown":
            _log_action(
                "login.log",
                username,
                page.url,
                f"Login status: false (exception: {str(e)})"
            )
        return False

async def close_cta_modal_if_any(page: Page) -> bool:
    return await safe_click(page, 'button[data-e2e="alt-middle-cta-cancel-btn"]', timeout_ms=3000)

async def close_exit_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='exit']", timeout_ms=2000)

async def close_profile_share_modal_if_any(page: Page) -> bool:
    return await safe_click(page, "[aria-label='close']", timeout_ms=2000)

async def click_author_avatar_if_any(page: Page) -> bool:
    return await safe_click(page, 'a[data-e2e="video-author-avatar"]', timeout_ms=3500)

async def visit_target_pivot_and_follow(page: Page, username: str = "unknown", max_retries: int = 3) -> bool:
    """
    Vào TARGET_PIVOT profile và click nút follow.

    Args:
        page: Playwright Page object
        username: Tên người dùng thực hiện action (người follow)
        max_retries: Số lần retry nếu fail

    Returns:
        True nếu follow thành công, False nếu không
    """
    target_username = TARGET_PIVOT.split("/@")[-1] if "/@" in TARGET_PIVOT else "unknown"

    for attempt in range(max_retries):
        try:
            # Navigate đến TARGET_PIVOT profile - để tự load, không set timeout cứng
            await page.goto(TARGET_PIVOT, wait_until="domcontentloaded")
            await sleep_ms(2000, 4000)

            # Close modal nếu có
            await close_cta_modal_if_any(page)
            await close_profile_share_modal_if_any(page)
            await sleep_ms(800, 1500)

            # Tìm nút follow - chờ đủ lâu để nó load
            follow_button_selector = 'button[data-e2e="follow-button"]'

            # Chờ button xuất hiện, không set timeout cứng
            try:
                await page.wait_for_selector(follow_button_selector, state="visible", timeout=30000)
            except Exception:
                if attempt < max_retries - 1:
                    await sleep_ms(2000, 3000)
                    continue
                return False

            follow_btn = page.locator(follow_button_selector).first

            # Đợi thêm để chắc chắn button đã sẵn sàng
            await sleep_ms(1000, 1500)

            if await follow_btn.count() > 0 and await follow_btn.is_visible():
                # Kiểm tra xem đã follow chưa
                try:
                    button_text = await follow_btn.inner_text(timeout=5000)

                    # Nếu button text là "Following" hoặc "Đang follow" thì đã follow rồi
                    if button_text and ("following" in button_text.lower() or "đang" in button_text.lower()):
                        return False
                except Exception:
                    pass

                # Scroll button vào view nếu cần
                try:
                    await follow_btn.scroll_into_view_if_needed(timeout=5000)
                    await sleep_ms(500, 1000)
                except Exception:
                    pass

                # Click nút follow với force click để chắc chắn
                try:
                    await follow_btn.click(force=True, timeout=10000)
                    await sleep_ms(1500, 2500)

                    # Verify click thành công bằng cách check text đã đổi chưa
                    try:
                        new_text = await follow_btn.inner_text(timeout=5000)
                        if new_text and ("following" in new_text.lower() or "đang" in new_text.lower()):
                            # Follow thành công! Log vào follow.log
                            _log_action("follow.log", username, TARGET_PIVOT, f"Successfully followed {target_username}")
                            return True
                    except Exception:
                        pass

                    # Nếu không verify được bằng text, coi như thành công và log
                    _log_action("follow.log", username, TARGET_PIVOT, f"Clicked follow button for {target_username}")
                    return True

                except Exception as click_err:
                    if attempt < max_retries - 1:
                        await sleep_ms(2000, 3000)
                        continue
                    return False

            return False

        except Exception as e:
            if attempt < max_retries - 1:
                await sleep_ms(2000, 3000)
                continue
            return False

    return False


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
    # Kiểm tra xem profile có video không trước khi scroll
    no_content_texts = [
        "Upload your first video",
        "Your videos will appear here",
        "No content",
        "This user has not published any videos."
    ]

    has_no_content = False
    for text in no_content_texts:
        try:
            element = page.locator(f'p:text-is("{text}")').first
            if await element.count() > 0 and await element.is_visible():
                has_no_content = True
                break
        except Exception:
            continue

    # Nếu không có video trong profile, quay về /foryou ngay lập tức
    if has_no_content:
        try:
            await page.goto("https://www.tiktok.com/foryou?lang=en", wait_until="load")
            await page.wait_for_load_state("networkidle", timeout=60000)
            await sleep_ms(2000, 4000)
            await close_cta_modal_if_any(page)
        except Exception:
            pass
        return

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

    # Nếu không tìm thấy video nào trong profile sau khi scroll, quay về /foryou để lướt
    if not links:
        try:
            await page.goto("https://www.tiktok.com/foryou?lang=en", wait_until="load")
            await page.wait_for_load_state("networkidle", timeout=60000)
            await sleep_ms(2000, 4000)
            await close_cta_modal_if_any(page)
        except Exception:
            pass
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

    # Đợi page load sau khi click vào video
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=30000)
        await sleep_ms(1000, 2000)
    except Exception:
        pass

    # Track và log video đang xem trong profile
    await track_and_log_video(page, username=username)

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

    # Thêm hành vi visit TARGET_PIVOT và follow - CHỈ KHI ĐÃ LOGIN
    if is_logged_in and chance(0.12):  # 12% cơ hội follow TARGET_PIVOT từ profile
        await sleep_ms(1000, 2500)
        follow_success = await visit_target_pivot_and_follow(page, username=username)
        if follow_success:
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
    will_view_min: int = 5,
    will_view_max: int = 15,
    username: str = "foryou",
):
    """
    More natural feed browsing:
    - watch time per video
    - small scroll adjustments
    - occasional comments open/close
    - occasional profile visit
    - track video URL và log vào like.log

    Args:
        username: Tên profile/user thực hiện actions (để log)
    """

    # 1. Vào profile page để check login status
    await page.goto(f"https://www.tiktok.com/@{username}?lang=en", wait_until="load")
    await page.wait_for_load_state("networkidle", timeout=30000)

    # ✅ start watcher (background)
    watcher = start_popup_watcher(page)

    try:
        await close_cta_modal_if_any(page)

        # 2. Kiểm tra login status
        is_logged_in = await check_login_status(page, username=username)

        # 3. Nếu chưa login, dừng ngay, không làm gì cả
        if not is_logged_in:
            _log_action("login.log", username, page.url, "Not logged in - stopping all actions")
            return

        # 4. Nếu đã login, chuyển về /foryou để thực hiện behaviors
        try:
            await page.goto("https://www.tiktok.com/foryou?lang=en", wait_until="load")
            await page.wait_for_load_state("networkidle", timeout=30000)
            await sleep_ms(2000, 4000)
            await close_cta_modal_if_any(page)
        except Exception:
            pass

        will_view_amount = randi(will_view_min, will_view_max)

        for _ in range(will_view_amount):
            # 0) Track và log video đang xem
            await track_and_log_video(page, username=username)

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

            # 3.5) sometimes visit TARGET_PIVOT and follow - CHỈ KHI ĐÃ LOGIN
            if is_logged_in and chance(0.8):  # 30% cơ hội follow TARGET_PIVOT
                await sleep_ms(1000, 2500)
                follow_success = await visit_target_pivot_and_follow(page, username=username)
                if follow_success:
                    await sleep_ms(1500, 3000)
                    # Sau khi follow, quay về /foryou
                    try:
                        await page.goto("https://www.tiktok.com/foryou?lang=en", wait_until="load")
                        await page.wait_for_load_state("networkidle", timeout=30000)
                        await sleep_ms(2000, 4000)
                        await close_cta_modal_if_any(page)
                    except Exception:
                        pass

            # 4) sometimes visit author profile and interact
            if chance(0.18):
                await sleep_ms(900, 2600)
                ok = await click_author_avatar_if_any(page)
                if ok:
                    # Đợi page load sau khi click vào avatar
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=30000)
                        await sleep_ms(1000, 2000)
                    except Exception:
                        pass

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

