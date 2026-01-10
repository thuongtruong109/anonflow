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


async def track_and_log_video(page: Page, username: str = "") -> None:
    global _current_video_url

    try:
        video_url = await get_current_video_url(page)

        if video_url and video_url != _current_video_url:
            _current_video_url = video_url

            if username and username != "":
                _log_action("like.log", username, video_url, "Now watching")

    except Exception as e:
        pass


async def check_login_status(page: Page, username: str = "") -> bool:
    """
    Kiểm tra login status bằng cách navigate đến /setting.
    Nếu redirect đến /foryou hoặc /login thì chưa login, nếu không redirect thì đã login.

    Args:
        page: Playwright Page object
        username: Tên người dùng để log (optional)

    Returns:
        True nếu đã login (không redirect), False nếu chưa login (redirect đến foryou/login)
    """
    try:
        # Lưu URL hiện tại để quay lại sau
        original_url = page.url

        # Navigate đến /setting để check login
        await page.goto("https://www.tiktok.com/setting?lang=en", wait_until="domcontentloaded", timeout=30000)

        # Đợi một lúc để xem có redirect không (3-5 giây)
        await sleep_ms(3000, 5000)

        # Kiểm tra URL hiện tại
        current_url = page.url

        # Nếu redirect đến /foryou hoặc /login thì chưa login
        if "/foryou" in current_url.lower() or "/login" in current_url.lower():
            redirect_reason = "foryou" if "/foryou" in current_url.lower() else "login"
            if username and username != "":
                _log_action(
                    "login.log",
                    username,
                    original_url,
                    f"Login status: false (redirected to {redirect_reason})"
                )
            return False
        else:
            # Không redirect, vẫn ở /setting -> đã login
            if username and username != "":
                _log_action(
                    "login.log",
                    username,
                    original_url,
                    "Login status: true (no redirect)"
                )
            return True

    except Exception as e:
        # Nếu có lỗi, coi như chưa login
        if username and username != "":
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

async def visit_target_pivot_and_follow(
    page: Page,
    username: str = "",
    target_username: str = None,
    max_retries: int = 3
) -> bool:
    """
    Vào target profile và click nút follow.

    Args:
        page: Playwright Page object
        username: Tên người dùng thực hiện action (người follow)
        target_username: Username để follow (bắt buộc)
        max_retries: Số lần retry nếu fail

    Returns:
        True nếu follow thành công, False nếu không
    """
    # Kiểm tra target_username
    if not target_username:
        print(f"⚠️ [{username}] No target username provided")
        return False

    # Xử lý target_username (có thể có @ hoặc không)
    target_user = target_username.lstrip("@")
    target_url = f"https://www.tiktok.com/@{target_user}"

    print(f"🎯 [{username}] Attempting to follow: {target_user}\n")

    for attempt in range(max_retries):
        try:
            # Navigate đến target profile với timeout rõ ràng
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            except Exception as goto_err:
                print(f"⚠️ [{username}] Failed to navigate to {target_user} (attempt {attempt+1}/{max_retries}): {goto_err}")
                if attempt < max_retries - 1:
                    await sleep_ms(2000, 3000)
                    continue
                return False

            await sleep_ms(2000, 4000)

            # Close modal nếu có
            await close_cta_modal_if_any(page)
            await close_profile_share_modal_if_any(page)
            await sleep_ms(800, 1500)

            # Tìm nút follow - chờ tối đa 30 giây
            follow_button_selector = 'button[data-e2e="follow-button"]'

            try:
                await page.wait_for_selector(follow_button_selector, state="visible", timeout=30000)
            except Exception as wait_err:
                print(f"⚠️ [{username}] Follow button not found (attempt {attempt+1}/{max_retries}): {wait_err}")
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
                    # Lấy text trước khi click
                    text_before = ""
                    try:
                        text_before = (await follow_btn.inner_text(timeout=3000)).lower()
                    except:
                        pass

                    print(f"👥 [{username}] Clicking follow button for {target_user}...")
                    await follow_btn.click(force=True, timeout=10000)

                    # Đợi lâu hơn để TikTok xử lý request (3-5s thay vì 1.5-2.5s)
                    await sleep_ms(3000, 5000)

                    # Verify click thành công bằng cách check text đã đổi chưa
                    follow_success = False
                    try:
                        new_text = (await follow_btn.inner_text(timeout=5000)).lower()

                        # Nếu text đổi từ "follow" sang "following"
                        if "follow" in text_before and "following" in new_text:
                            follow_success = True
                        # Hoặc nếu text hiện tại là "following"
                        elif "following" in new_text or "đang" in new_text:
                            follow_success = True

                        print(f"✅ [{username}] Follow verification: text_before='{text_before}', new_text='{new_text}', success={follow_success}")
                    except Exception as verify_err:
                        print(f"⚠️ [{username}] Cannot verify follow text: {verify_err}")
                        # Không verify được, đợi thêm rồi check lại
                        await sleep_ms(2000, 3000)
                        try:
                            final_text = (await follow_btn.inner_text(timeout=5000)).lower()
                            if "following" in final_text or "đang" in final_text:
                                follow_success = True
                                print(f"✅ [{username}] Follow verification (retry): final_text='{final_text}', success={follow_success}")
                        except:
                            pass

                    if follow_success:
                        # Follow thành công! Log vào follow.log
                        _log_action("follow.log", username, target_url, f"Successfully followed {target_user}")
                        print(f"🎉 [{username}] Successfully followed {target_user}")
                        return True
                    else:
                        # Click rồi nhưng không chắc có thành công
                        _log_action("follow.log", username, target_url, f"Clicked follow button for {target_user} (unverified)")
                        print(f"⚠️ [{username}] Clicked follow but cannot verify success")
                        return True  # Vẫn return True vì đã click rồi

                except Exception as click_err:
                    print(f"❌ [{username}] Follow click error: {click_err}")
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


async def random_like_video(page: Page, username: str = "") -> bool:
    """
    Thực hiện like video hiện tại với hành vi tự nhiên:
    - Đôi khi miss button và phải click lại
    - Pause trước khi like (như đang suy nghĩ)
    - Đôi khi unlike ngay sau đó (changed mind)

    Hỗ trợ 2 loại like button:
    1. Feed video: span[data-e2e="like-icon"]
    2. Profile video: span[data-e2e="browse-like-icon"]

    Args:
        page: Playwright Page object
        username: Tên người dùng thực hiện action (để log)

    Returns:
        True nếu like thành công, False nếu không.
    """
    # Pause trước khi like - con người cần thời gian quyết định
    await sleep_ms(500, 1800)

    # Selector cho like button (theo thứ tự ưu tiên)
    like_button_selectors = [
        'span[data-e2e="like-icon"]',         # Feed video
        'span[data-e2e="browse-like-icon"]',  # Profile video
    ]

    like_success = False

    for selector in like_button_selectors:
        try:
            like_btn = page.locator(selector).first
            if await like_btn.count() > 0 and await like_btn.is_visible():
                # Kiểm tra xem đã like chưa
                try:
                    parent = like_btn.locator('..').first
                    parent_classes = await parent.get_attribute("class") or ""
                    aria_pressed = await like_btn.get_attribute("aria-pressed")

                    if aria_pressed == "true" or "liked" in parent_classes.lower() or "active" in parent_classes.lower():
                        return False
                except Exception:
                    pass

                # Hover trước khi click (như chuột di chuyển đến)
                try:
                    await like_btn.hover()
                    await sleep_ms(150, 500)
                except Exception:
                    pass

                # 5% cơ hội miss lần đầu (click chệch)
                if chance(0.05):
                    # Click gần button nhưng không trúng
                    box = await like_btn.bounding_box()
                    if box:
                        offset_x = random.uniform(-15, 15)
                        offset_y = random.uniform(-15, 15)
                        await page.mouse.click(
                            box["x"] + box["width"]/2 + offset_x,
                            box["y"] + box["height"]/2 + offset_y
                        )
                        await sleep_ms(200, 500)  # nhận ra miss

                # Click thực sự
                await like_btn.click(timeout=2000)
                like_success = True
                await sleep_ms(800, 1500)

                # 3% cơ hội "changed mind" - unlike ngay sau đó
                if chance(0.03):
                    await sleep_ms(500, 1200)
                    try:
                        # Click lại để unlike
                        await like_btn.click(timeout=2000)
                        await sleep_ms(400, 900)
                        # Rồi like lại (or not)
                        if chance(0.5):
                            await sleep_ms(300, 700)
                            await like_btn.click(timeout=2000)
                    except Exception:
                        pass

                # Log action
                if username and username != "":
                    # Lấy URL của video cụ thể thay vì page URL
                    video_url = await get_current_video_url(page)
                    if not video_url:
                        video_url = page.url  # Fallback nếu không lấy được
                    _log_action("like.log", username, video_url, "Liked video")

                break
        except Exception:
            continue

    return like_success

async def random_follow_in_feed(page: Page, username: str = "") -> bool:
    """
    Click nút follow ngẫu nhiên khi đang lướt feed với hành vi tự nhiên.

    Selector: button[data-e2e="feed-follow"]

    Verify success bằng cách check button có chứa checkmark SVG sau khi click:
    - Before: SVG với path chứa "M26 7a1 1 0 0 0-1-1h-2..." (plus icon)
    - After: SVG với path chứa "M43 6.08c.7.45..." (checkmark icon)

    Args:
        page: Playwright Page object
        username: Tên người dùng thực hiện action (để log)

    Returns:
        True nếu follow thành công, False nếu không
    """
    try:
        # Pause trước khi follow (như đang quyết định)
        await sleep_ms(500, 1500)

        # Tìm nút follow trong feed
        feed_follow_selector = 'button[data-e2e="feed-follow"]'
        follow_btn = page.locator(feed_follow_selector).first

        # Check button có tồn tại và visible không
        if await follow_btn.count() == 0 or not await follow_btn.is_visible():
            return False

        # Check xem đã follow chưa bằng cách kiểm tra SVG path
        try:
            svg_path = follow_btn.locator('svg path').first
            if await svg_path.count() > 0:
                path_d = await svg_path.get_attribute('d')
                # Nếu có checkmark icon thì đã follow rồi
                if path_d and 'M43 6.08c.7.45' in path_d:
                    return False
        except Exception:
            pass

        # Hover trước khi click
        try:
            await follow_btn.hover()
            await sleep_ms(200, 600)
        except Exception:
            pass

        # 5% cơ hội miss lần đầu
        if chance(0.05):
            box = await follow_btn.bounding_box()
            if box:
                offset_x = random.uniform(-10, 10)
                offset_y = random.uniform(-10, 10)
                await page.mouse.click(
                    box["x"] + box["width"]/2 + offset_x,
                    box["y"] + box["height"]/2 + offset_y
                )
                await sleep_ms(200, 500)

        # Click nút follow
        await follow_btn.click(timeout=3000)
        await sleep_ms(1000, 2000)

        # Verify follow thành công bằng cách check SVG path đã đổi chưa
        follow_success = False
        try:
            svg_path = follow_btn.locator('svg path').first
            if await svg_path.count() > 0:
                new_path_d = await svg_path.get_attribute('d')
                # Check xem có checkmark icon không
                if new_path_d and 'M43 6.08c.7.45' in new_path_d:
                    follow_success = True
        except Exception:
            pass

        # Nếu không verify được, đợi thêm rồi check lại
        if not follow_success:
            await sleep_ms(1000, 1500)
            try:
                svg_path = follow_btn.locator('svg path').first
                if await svg_path.count() > 0:
                    final_path_d = await svg_path.get_attribute('d')
                    if final_path_d and 'M43 6.08c.7.45' in final_path_d:
                        follow_success = True
            except Exception:
                pass

        # Log action nếu follow thành công
        if follow_success and username and username != "":
            # Lấy URL của video cụ thể thay vì page URL
            video_url = await get_current_video_url(page)
            if not video_url:
                video_url = page.url  # Fallback nếu không lấy được
            # Lấy username của author nếu có
            try:
                author_link = page.locator('a[data-e2e="video-author-uniqueid"]').first
                if await author_link.count() > 0:
                    author_href = await author_link.get_attribute("href")
                    if author_href and "/@" in author_href:
                        target_user = author_href.split("/@")[-1].split("/")[0].split("?")[0]
                        _log_action("follow.log", username, video_url, f"Followed {target_user} (feed)")
            except Exception:
                _log_action("follow.log", username, video_url, "Followed author (feed)")

        return follow_success

    except Exception as e:
        return False

async def random_comment_on_video(page: Page, username: str = "", text_randomizer: TextRandomizer = None) -> bool:
    """
    Thêm comment ngẫu nhiên vào video hiện tại với hành vi tự nhiên:
    - Typing speed thay đổi (nhanh-chậm-nhanh)
    - Đôi khi pause giữa chừng (suy nghĩ)
    - Đôi khi sửa lỗi chính tả (backspace)
    - Đôi khi xóa và viết lại

    Hỗ trợ 2 loại selector:
    1. Comment trong profile video: div[data-e2e="comment-input"]
    2. Comment trong feed video: div.public-DraftEditorPlaceholder-inner

    Returns True nếu comment thành công, False nếu không.
    """
    if text_randomizer is None:
        text_randomizer = TextRandomizer(lang="en")

    # Sinh comment text ngẫu nhiên
    comment_text = text_randomizer.comment(
        context=random.choice(["generic", "like", "reply"]),
        tone=random.choice(["friendly", "enthusiastic", "polite"]),
        length=random.choice(["short", "medium"]),
        unique=True
    )

    # Pause trước khi comment (suy nghĩ nội dung)
    await sleep_ms(800, 2000)

    # Thử click vào comment input
    profile_comment_selector = 'div[data-e2e="comment-input"]'
    feed_comment_selector = 'div.public-DraftEditorPlaceholder-inner'

    comment_clicked = False

    # Thử selector cho profile video
    try:
        profile_input = page.locator(profile_comment_selector).first
        if await profile_input.count() > 0 and await profile_input.is_visible():
            # Hover trước khi click
            try:
                await profile_input.hover()
                await sleep_ms(200, 500)
            except Exception:
                pass
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
                try:
                    await feed_input.hover()
                    await sleep_ms(200, 500)
                except Exception:
                    pass
                await feed_input.click(timeout=3000)
                comment_clicked = True
                await sleep_ms(500, 1000)
        except Exception:
            pass

    if not comment_clicked:
        return False

    # Tìm text editor để nhập comment
    try:
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
                    await editor.focus(timeout=2000)
                    await sleep_ms(300, 600)

                    # Typing tự nhiên với variable speed và behaviors
                    words = comment_text.split()
                    typing_speed_base = random.randint(50, 150)  # Base WPM

                    for word_idx, word in enumerate(words):
                        # 10% cơ hội pause trước từ (như đang suy nghĩ)
                        if word_idx > 0 and chance(0.10):
                            await sleep_ms(500, 1500)

                        # Typing từng ký tự với speed thay đổi
                        for char_idx, char in enumerate(word):
                            # Tốc độ typing thay đổi theo vị trí trong từ
                            if char_idx == 0:  # Đầu từ chậm hơn
                                delay = typing_speed_base + random.randint(20, 50)
                            elif char_idx == len(word) - 1:  # Cuối từ cũng chậm
                                delay = typing_speed_base + random.randint(10, 30)
                            else:  # Giữa từ nhanh hơn
                                delay = typing_speed_base - random.randint(0, 20)

                            # Thêm jitter
                            delay = max(30, delay + random.randint(-15, 15))

                            # 2% cơ hội typo (gõ sai rồi backspace)
                            if chance(0.02) and char_idx < len(word) - 1:
                                # Gõ sai
                                wrong_char = random.choice('qwertyuiopasdfghjklzxcvbnm')
                                await page.keyboard.type(wrong_char, delay=delay)
                                await sleep_ms(100, 300)  # Nhận ra sai
                                await page.keyboard.press("Backspace")
                                await sleep_ms(50, 150)

                            await page.keyboard.type(char, delay=delay)

                        # Thêm space sau mỗi từ (trừ từ cuối)
                        if word_idx < len(words) - 1:
                            await page.keyboard.press("Space")
                            await sleep_ms(50, 150)

                        # 5% cơ hội pause giữa các từ (đang suy nghĩ)
                        if chance(0.05):
                            await sleep_ms(300, 1000)

                    editor_found = True

                    # Pause trước khi submit (đọc lại comment)
                    await sleep_ms(800, 2000)

                    # 3% cơ hội xóa và viết lại (changed mind)
                    if chance(0.03):
                        # Select all và xóa
                        await page.keyboard.press("Control+A")
                        await sleep_ms(200, 500)
                        await page.keyboard.press("Backspace")
                        await sleep_ms(500, 1200)

                        # Viết lại (có thể khác hoặc giống)
                        if chance(0.5):
                            # Viết lại comment khác
                            new_comment = text_randomizer.comment(
                                context=random.choice(["generic", "like"]),
                                tone=random.choice(["friendly", "enthusiastic"]),
                                length="short",
                                unique=True
                            )
                            for char in new_comment:
                                await page.keyboard.type(char, delay=random.randint(50, 120))
                        else:
                            # Viết lại comment cũ
                            for char in comment_text:
                                await page.keyboard.type(char, delay=random.randint(50, 120))

                        await sleep_ms(500, 1200)

                    break
            except Exception:
                continue

        if not editor_found:
            return False

        # Submit comment
        await sleep_ms(500, 1000)

        # Thử tìm và click nút Post
        post_button_clicked = False
        try:
            post_button = page.locator('div[data-e2e="comment-post"][aria-disabled="false"]').first
            if await post_button.count() > 0 and await post_button.is_visible():
                # Hover trước khi click
                try:
                    await post_button.hover()
                    await sleep_ms(150, 400)
                except Exception:
                    pass
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

        # Log action - chỉ log khi có username thực sự (không phải "")
        if username and username != "":
            # Lấy URL của video cụ thể thay vì page URL
            video_url = await get_current_video_url(page)
            if not video_url:
                video_url = page.url  # Fallback nếu không lấy được
            _log_action("comment.log", username, video_url, f"Commented: {comment_text}")

        return True

    except Exception as e:
        return False

async def click_author_avatar_if_any(page: Page) -> bool:
    return await safe_click(page, 'a[data-e2e="video-author-avatar"]', timeout_ms=3500)

def is_bridge_link(url: str) -> bool:
    return re.search(r"(onelink\.me|snssdk)", url, re.IGNORECASE) is not None

async def random_interact_in_profile(page: Page, username: str = "", is_logged_in: bool = True):
    """
    Human-ish profile browsing với các hành vi tự nhiên:
    - Variable scroll patterns (không đều đặn)
    - Reading pauses at different content
    - Natural video selection (không random hoàn toàn)
    - Realistic engagement behaviors

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
        "Something went wrong"
        "Sorry about that! Please try again later."
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

    # Nếu không có video trong profile, quay về homepage
    if has_no_content:
        try:
            await page.goto("https://www.tiktok.com/?lang=en", wait_until="load")
            await page.wait_for_load_state("networkidle", timeout=60000)
            await sleep_ms(2000, 4000)
            await close_cta_modal_if_any(page)
        except Exception:
            pass
        return

    # Scroll với pattern tự nhiên - không đều đặn
    scroll_rounds = randi(3, 7)
    for i in range(scroll_rounds):
        # Variable scroll distance - đôi khi scroll nhiều, đôi khi ít
        if chance(0.3):  # 30% scroll ngắn (reading)
            scroll_px = randi(300, 700)
        elif chance(0.15):  # 15% scroll dài (skimming)
            scroll_px = randi(1200, 2000)
        else:  # 55% scroll bình thường
            scroll_px = randi(700, 1200)

        await human_scroll_wheel(
            page,
            scroll_px,
            step_range=(90, 210),
            pause_range=(180, 720),
            sometimes_hesitate=True,
            sometimes_backtrack=True,
        )

        # Đôi khi backtrack nhiều hơn (nhìn lại video vừa scroll qua)
        if chance(0.25):
            await human_scroll_wheel(
                page,
                -randi(180, 600),
                step_range=(70, 150),
                pause_range=(160, 560),
            )

        # Variable pause between scrolls - đôi khi đọc lâu
        if chance(0.3):
            await sleep_ms(1500, 3500)  # Reading pause
        else:
            await sleep_ms(700, 2200)

        # 10% cơ hội mouse hover trên video thumbnail (như đang xem preview)
        if chance(0.10):
            try:
                videos = await page.locator('a[href*="/video/"]').all()
                if videos:
                    random_video = random.choice(videos)
                    await random_video.hover()
                    await sleep_ms(800, 2000)
            except Exception:
                pass

    links = await page.locator('a[href*="/video/"]').all()
    if len(links) > 3:
        links = links[2:]

    # Nếu không tìm thấy video nào, quay về homepage
    if not links:
        try:
            await page.goto("https://www.tiktok.com/?lang=en", wait_until="load")
            await page.wait_for_load_state("networkidle", timeout=60000)
            await sleep_ms(2000, 4000)
            await close_cta_modal_if_any(page)
        except Exception:
            pass
        return

    # Chọn video theo pattern tự nhiên (không hoàn toàn random)
    # Con người thường chọn video ở vị trí đặc biệt (đầu list, hoặc video đã scroll đến)
    if chance(0.4):  # 40% chọn video ở đầu/gần đầu
        video = links[0] if len(links) == 1 else links[random.randint(0, min(2, len(links)-1))]
    elif chance(0.3):  # 30% chọn video ở giữa
        mid = len(links) // 2
        video = links[random.randint(max(0, mid-2), min(len(links)-1, mid+2))]
    else:  # 30% random hoàn toàn
        video = random.choice(links)

    try:
        await video.scroll_into_view_if_needed()
    except Exception:
        pass

    await sleep_ms(900, 2200)

    try:
        # Hover trước khi click
        await video.hover()
        await sleep_ms(450, 1400)

        # Jitter mouse đôi khi (như đang xem preview)
        if chance(0.25):
            await jitter_mouse(page, steps_min=1, steps_max=2)

        # 3% cơ hội miss click
        if chance(0.03):
            box = await video.bounding_box()
            if box:
                # Click chệch
                await page.mouse.click(
                    box["x"] + box["width"]/2 + random.uniform(-20, 20),
                    box["y"] + box["height"]/2 + random.uniform(-20, 20)
                )
                await sleep_ms(300, 700)  # nhận ra miss

        await video.click()
    except Exception:
        return

    # Đợi page load
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=60000)
        await sleep_ms(1000, 2000)
    except Exception:
        pass

    # Watch với variable engagement
    await watch_like_human(page, min_ms=7000, max_ms=22000, mouse_jitter=True)
    await sleep_ms(1200, 5200)

    # Like với tỉ lệ tự nhiên - CHỈ KHI ĐÃ LOGIN
    if is_logged_in and chance(0.45):  # 45% cơ hội like (tăng từ 40%)
        await sleep_ms(600, 1800)
        like_success = await random_like_video(page, username=username)
        if like_success:
            await sleep_ms(800, 1800)

    # Comment với tỉ lệ thấp hơn - CHỈ KHI ĐÃ LOGIN
    if is_logged_in and chance(0.25):  # 25% cơ hội comment (giảm từ 30%)
        await sleep_ms(800, 1800)
        comment_success = await random_comment_on_video(page, username=username)
        if comment_success:
            await sleep_ms(1500, 3000)

    # Go back với natural behavior
    try:
        # 70% dùng back button, 30% dùng keyboard
        if chance(0.7):
            await page.go_back()
        else:
            await page.keyboard.press("Alt+Left")
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
    username: str = "",
    follow: bool = False,
    like_video: bool = False,
    comment: bool = False,
    view_video: bool = True,
    view_amount: int = None,
    follow_mode: str = "random",
    follow_target: str = None,
    all_usernames: list = None,
):
    """
    More natural feed browsing:
    - watch time per video
    - small scroll adjustments
    - occasional comments open/close
    - occasional profile visit

    Args:
        username: Tên profile/user thực hiện actions (để log)
        follow_mode: Mode follow - "random", "mutual", hoặc "target"
        follow_target: Username để follow (nếu follow_mode="target")
        all_usernames: Danh sách tất cả usernames (nếu follow_mode="mutual")
    """

    # DEBUG LOG
    print(f"🎯 [{username}] run_tiktok_flow CALLED with: follow={follow}, like={like_video}, comment={comment}, view={view_video}\n")

    # ✅ start watcher (background)
    watcher = start_popup_watcher(page)

    try:
        # 1. Kiểm tra login status TRƯỚC KHI navigate đến TikTok
        print(f"🔐 [{username}] Checking login status...\n")
        is_logged_in = await check_login_status(page, username=username)
        print(f"🔐 [{username}] Login status: {is_logged_in}\n")

        # 2. Nếu chưa login, dừng ngay, không làm gì cả
        if not is_logged_in:
            print(f"❌ [{username}] NOT LOGGED IN - stopping all actions")
            return

        print(f"✅ [{username}] LOGGED IN - proceeding with TikTok navigation")

        # 3. Chỉ khi đã login mới navigate đến TikTok
        print(f"🌐 [{username}] Navigating to TikTok homepage...")
        try:
            await page.goto("https://www.tiktok.com/?lang=en", wait_until="load", timeout=90000)
            try:
                # Chỉ đợi networkidle 30 giây thôi, nếu quá lâu thì bỏ qua
                await asyncio.wait_for(
                    page.wait_for_load_state("networkidle"),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                print(f"⚠️ [{username}] Network idle timeout - continuing anyway")
            await sleep_ms(2000, 4000)
            print(f"✅ [{username}] TikTok homepage loaded")
        except Exception as nav_error:
            print(f"⚠️ [{username}] Navigation failed: {nav_error}")
            # Nếu navigate fail, thử reload page hiện tại
            try:
                await page.reload(wait_until="load", timeout=60000)
                await sleep_ms(2000, 3000)
            except Exception as reload_error:
                print(f"❌ [{username}] Reload also failed: {reload_error}")
                # Nếu reload cũng fail thì return luôn, không làm gì nữa
                return

        await close_cta_modal_if_any(page)

        will_view_amount = view_amount if view_amount is not None else randi(will_view_min, will_view_max)

        print(f"📹 [{username}] view_video={view_video}, will_view_amount={will_view_amount}")

        if view_video:
            print(f"🎬 [{username}] Starting view video loop for {will_view_amount} videos")

            # Track fatigue và engagement để điều chỉnh behavior
            fatigue_level = 0.0  # 0-1, càng cao càng mệt
            session_engagement = random.uniform(0.6, 0.9)  # Engagement ban đầu

            for i in range(will_view_amount):
                print(f"👀 [{username}] Watching video {i+1}/{will_view_amount}\n")

                # Update fatigue (tăng dần theo thời gian, đôi khi recover)
                fatigue_level += random.uniform(0.02, 0.08)
                if chance(0.15):  # 15% cơ hội "refresh" (như khi thấy video hay)
                    fatigue_level = max(0, fatigue_level - random.uniform(0.1, 0.3))
                    session_engagement = min(1.0, session_engagement + 0.1)
                fatigue_level = min(1.0, fatigue_level)

                # Engagement decay với fatigue
                session_engagement -= fatigue_level * 0.05
                session_engagement = max(0.3, min(1.0, session_engagement))

                # 1) Watch với duration phụ thuộc vào engagement và fatigue
                # High engagement + low fatigue = watch lâu hơn
                # Low engagement + high fatigue = watch ngắn hơn
                engagement_multiplier = (session_engagement * (1 - fatigue_level * 0.5))
                watch_min = int(2000 * (0.5 + engagement_multiplier * 0.5))  # Giảm từ 6000 xuống 2000
                watch_max = int(8000 * (0.5 + engagement_multiplier * 0.5))  # Giảm từ 20000 xuống 8000

                await watch_like_human(page, min_ms=watch_min, max_ms=watch_max, mouse_jitter=True)

                # 1.5) Like phụ thuộc vào engagement - CHỈ KHI ĐÃ LOGIN
                if is_logged_in and like_video:
                    # Tỉ lệ like tăng với engagement, giảm với fatigue
                    like_chance = 0.35 * session_engagement * (1 - fatigue_level * 0.3)
                    if chance(like_chance):
                        await sleep_ms(600, 1400)
                        like_success = await random_like_video(page, username=username)
                        if like_success:
                            await sleep_ms(800, 1800)
                            # Like thành công tăng engagement một chút
                            session_engagement = min(1.0, session_engagement + 0.05)

                # 1.6) Follow in feed - CHỈ KHI ĐÃ LOGIN và follow enabled
                if is_logged_in and follow:
                    # Tỉ lệ follow giảm với fatigue (thấp hơn like)
                    feed_follow_chance = 0.20 * session_engagement * (1 - fatigue_level * 0.5)
                    if chance(feed_follow_chance):
                        await sleep_ms(800, 1800)
                        follow_success = await random_follow_in_feed(page, username=username)
                        if follow_success:
                            await sleep_ms(1000, 2000)
                            # Follow thành công tăng engagement
                            session_engagement = min(1.0, session_engagement + 0.08)

                # 1.7) Chuyển sang video tiếp theo - ĐẢM BẢO chuyển video sau khi watch xong
                print(f"🔄 [{username}] Switching to next video after watching {i+1}")
                await sleep_ms(800, 1500)

                # Thử scroll xuống để load video mới (ưu tiên)
                scroll_success = False
                if chance(0.8):  # 80% cơ hội scroll
                    try:
                        # Scroll lớn hơn để đảm bảo chuyển video
                        await human_scroll_wheel(page, randi(800, 1200), step_range=(80, 160), pause_range=(150, 500))
                        await sleep_ms(1000, 2000)  # Đợi video load
                        scroll_success = True
                        print(f"📜 [{username}] Scrolled to next video")
                    except Exception as e:
                        print(f"⚠️ [{username}] Scroll failed: {e}")

                # Nếu scroll không thành công, thử press space (backup)
                if not scroll_success:
                    try:
                        await page.keyboard.press("ArrowDown")
                        await sleep_ms(500, 1000)
                        print(f"⬇️ [{username}] Used arrow down to next video")
                    except Exception as e:
                        print(f"⚠️ [{username}] Arrow down failed: {e}")

                # 2) Scroll behaviors bổ sung - giảm dần khi fatigue cao
                if chance(0.55 * (1 - fatigue_level * 0.5)):
                    # Scroll nhỏ hơn để tương tác tự nhiên
                    await human_scroll_wheel(page, randi(200, 400), step_range=(70, 150), pause_range=(120, 420))
                if chance(0.10):
                    await human_scroll_wheel(page, -randi(120, 260), step_range=(60, 120), pause_range=(120, 420))

                # 3) Comments - tỉ lệ thấp và phụ thuộc vào engagement
                should_open_comments = (comment and chance(0.6)) or chance(0.22 * session_engagement)
                if should_open_comments:
                    await sleep_ms(900, 2400)
                    await safe_click_xpath(page, "//*[@data-e2e='comment-icon']", timeout_ms=6000)

                    # "read" comments
                    reading_time = randi(1800, 6000)
                    # High engagement = đọc lâu hơn
                    reading_time = int(reading_time * (0.7 + session_engagement * 0.3))
                    await sleep_ms(reading_time, reading_time + 1000)

                    # Comment scroll
                    if chance(0.35 * session_engagement):
                        await human_scroll_wheel(page, randi(220, 700), step_range=(90, 170), pause_range=(160, 520))

                    # Comment nếu enabled - CHỈ KHI ĐÃ LOGIN
                    if is_logged_in and comment:
                        # Tỉ lệ comment giảm với fatigue
                        comment_chance = 0.7 * (1 - fatigue_level * 0.4)
                        if chance(comment_chance):
                            await sleep_ms(800, 1800)
                            comment_success = await random_comment_on_video(page, username=username)
                            if comment_success:
                                await sleep_ms(1500, 3000)
                                # Comment thành công tăng engagement
                                session_engagement = min(1.0, session_engagement + 0.08)

                    # Detect bridge navigation
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

                # 3.5) Follow - tỉ lệ giảm với fatigue - CHỈ KHI ĐÃ LOGIN
                follow_chance = 0.50 * (1 - fatigue_level * 0.6)
                if is_logged_in and follow and chance(follow_chance):
                    await sleep_ms(1000, 2500)

                    target_to_follow = None

                    if follow_mode == "random":
                        try:
                            author_link = page.locator('a[data-e2e="video-author-uniqueid"]').first
                            if await author_link.count() > 0:
                                author_href = await author_link.get_attribute("href")
                                if author_href and "/@" in author_href:
                                    target_to_follow = author_href.split("/@")[-1].split("/")[0].split("?")[0]
                                    print(f"🎲 [{username}] Random mode: Following author {target_to_follow}")
                        except Exception as e:
                            print(f"⚠️ [{username}] Cannot get random author: {e}")

                    elif follow_mode == "mutual":
                        if all_usernames and len(all_usernames) > 1:
                            other_users = [u for u in all_usernames if u != username]
                            if other_users:
                                target_to_follow = random.choice(other_users)
                                print(f"🔄 [{username}] Mutual mode: Following {target_to_follow}")

                    elif follow_mode == "target":
                        if follow_target:
                            target_to_follow = follow_target
                            print(f"🎯 [{username}] Target mode: Following {target_to_follow}\n")

                    if target_to_follow:
                        follow_success = await visit_target_pivot_and_follow(
                            page,
                            username=username,
                            target_username=target_to_follow
                        )
                        if follow_success:
                            await sleep_ms(1500, 3000)
                            # Quay về /
                            try:
                                await page.goto("https://www.tiktok.com/?lang=en", wait_until="load", timeout=60000)
                                try:
                                    await asyncio.wait_for(
                                        page.wait_for_load_state("networkidle"),
                                        timeout=20.0
                                    )
                                except asyncio.TimeoutError:
                                    print(f"⚠️ [{username}] Network idle timeout after follow - continuing")
                                await sleep_ms(2000, 4000)
                                await close_cta_modal_if_any(page)
                            except Exception as nav_err:
                                print(f"⚠️ [{username}] Failed to return to homepage after follow: {nav_err}")
                    else:
                        print(f"⚠️ [{username}] No target to follow in mode: {follow_mode}")

                # 4) Profile visit - giảm với fatigue
                if chance(0.18 * (1 - fatigue_level * 0.7)):
                    await sleep_ms(900, 2600)
                    ok = await click_author_avatar_if_any(page)
                    if ok:
                        try:
                            await page.wait_for_load_state("domcontentloaded", timeout=60000)
                            await sleep_ms(1000, 2000)
                        except Exception:
                            pass

                        await close_profile_share_modal_if_any(page)
                        await sleep_ms(800, 2200)
                        await random_interact_in_profile(page, username=username, is_logged_in=is_logged_in)
                        await sleep_ms(700, 2000)

                # 5) Next video - với pause phụ thuộc fatigue
                # High fatigue = pause lâu hơn trước next
                base_pause = 900 + int(fatigue_level * 1500)
                await page.keyboard.press("Space")
                await sleep_ms(base_pause, base_pause + 1500)

                # 6) Fatigue break - khi fatigue cao, đôi khi nghỉ dài
                if fatigue_level > 0.6 and chance(0.15):
                    print(f"😴 [{username}] Taking fatigue break...")
                    await sleep_ms(5000, 12000)
                    # Reset fatigue một phần
                    fatigue_level = max(0.3, fatigue_level - 0.4)
                    session_engagement = random.uniform(0.5, 0.8)

                # 7) Rare fast swipe streak - chỉ khi engagement thấp hoặc fatigue cao
                if chance(0.06) and (fatigue_level > 0.5 or session_engagement < 0.5):
                    print(f"⚡ [{username}] Fast swipe streak (bored/tired)")
                    await press_space_n(
                        page,
                        randi(2, 4),
                        delay_min_ms=400,
                        delay_max_ms=1300,
                        watch_min_ms=1500,  # Ngắn hơn bình thường
                        watch_max_ms=4000,
                        humanize=True,
                    )
                    # Fast swipe tăng fatigue
                    fatigue_level = min(1.0, fatigue_level + 0.15)
    finally:
        await stop_popup_watcher(watcher)

