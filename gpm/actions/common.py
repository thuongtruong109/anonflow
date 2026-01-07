import asyncio, random, time, re, math
from typing import Optional, Tuple

from playwright.async_api import Page, Locator, TimeoutError as PlaywrightTimeoutError

def randi(min_v: int, max_v: int) -> int:
    return random.randint(min_v, max_v)

def chance(p: float) -> bool:
    return random.random() < p

async def sleep_ms(min_ms: int, max_ms: int | None = None):
    """
    Sleep với distribution tự nhiên hơn, thêm micro-pause ngẫu nhiên
    """
    if max_ms is None:
        ms = min_ms
    else:
        # Dùng beta distribution thay vì gaussian để có skew tự nhiên hơn
        # Con người thường nhanh hơn nhưng đôi khi chậm bất ngờ
        alpha, beta = 2.5, 5  # skew về phía nhanh hơn
        normalized = random.betavariate(alpha, beta)
        ms = min_ms + (max_ms - min_ms) * normalized

        # Thêm micro-jitter (dao động nhỏ) - con người không bao giờ timing hoàn hảo
        jitter = random.uniform(-0.05, 0.05) * ms
        ms = int(ms + jitter)
        ms = max(min_ms, min(max_ms, ms))

    await asyncio.sleep(ms / 1000)

    # 8% cơ hội có micro-pause bất ngờ (như khi con người lơ đãng hoặc suy nghĩ)
    if chance(0.08):
        await asyncio.sleep(random.uniform(0.05, 0.3))

async def human_pause(min_ms: int = 250, max_ms: int = 900):
    """
    Natural human pause với micro-variations
    """
    await sleep_ms(min_ms, max_ms)

    # 5% cơ hội có "double take" pause (dừng, rồi dừng thêm)
    if chance(0.05):
        await sleep_ms(200, 600)

async def natural_rest_cycle(page: Page, duration_ms: int = 10000):
    """
    Chu kỳ nghỉ ngơi tự nhiên - con người đôi khi cần rest giữa các session
    - Giảm activity
    - Đôi khi di chuyển chuột lười biếng
    - Đôi khi scroll một chút
    """
    end_time = asyncio.get_event_loop().time() + (duration_ms / 1000)

    while asyncio.get_event_loop().time() < end_time:
        await sleep_ms(2000, 5000)

        # 30% cơ hội di chuyển chuột lười biếng
        if chance(0.30):
            await jitter_mouse(page, steps_min=1, steps_max=2)

        # 15% cơ hội scroll nhẹ
        if chance(0.15):
            await page.mouse.wheel(0, random.randint(-100, 100))
            await sleep_ms(500, 1500)

        # 10% cơ hội "wake up" sớm
        if chance(0.10):
            break

async def safe_click(page: Page, selector: str, *, timeout_ms: int = 8000) -> bool:
    """
    Click với các hành vi tự nhiên như con người:
    - Đôi khi miss và phải click lại
    - Pause trước khi click
    - Hover trước khi click (như con người di chuyển chuột đến)
    """
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout_ms)

        # 75% thời gian hover trước khi click (như con người di chuyển chuột)
        if chance(0.75):
            try:
                await loc.hover()
                await sleep_ms(80, 350)  # pause nhỏ sau khi hover
            except Exception:
                pass

        # Pause trước khi click (con người cần thời gian nhận diện + quyết định)
        await sleep_ms(100, 400)

        # 3% cơ hội "miss" lần đầu (click sai vị trí)
        if chance(0.03):
            # Click gần đó nhưng không đúng
            box = await loc.bounding_box()
            if box:
                offset_x = random.uniform(-10, 10)
                offset_y = random.uniform(-10, 10)
                await page.mouse.click(
                    box["x"] + box["width"]/2 + offset_x,
                    box["y"] + box["height"]/2 + offset_y
                )
                await sleep_ms(150, 350)  # nhận ra miss

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
    """
    Di chuyển chuột tự nhiên hơn với:
    - Đường cong Bezier thay vì đường thẳng
    - Tốc độ thay đổi (chậm ở đầu/cuối, nhanh ở giữa)
    - Đôi khi overshoot và correct lại
    """
    x1, y1, x2, y2 = area
    steps = randi(steps_min, steps_max)

    current_x, current_y = 0, 0
    try:
        # Lấy vị trí chuột hiện tại nếu có thể
        viewport = page.viewport_size
        current_x = random.randint(x1, x2)
        current_y = random.randint(y1, y2)
    except:
        pass

    for _ in range(steps):
        target_x = randi(x1, x2)
        target_y = randi(y1, y2)

        # 15% cơ hội overshoot (đi quá đích rồi quay lại)
        if chance(0.15):
            overshoot_x = target_x + random.randint(-30, 30)
            overshoot_y = target_y + random.randint(-30, 30)
            overshoot_x = max(x1, min(x2, overshoot_x))
            overshoot_y = max(y1, min(y2, overshoot_y))

            # Di chuyển đến overshoot
            await _move_mouse_naturally(page, current_x, current_y, overshoot_x, overshoot_y)
            await sleep_ms(50, 150)

            # Correct lại
            await _move_mouse_naturally(page, overshoot_x, overshoot_y, target_x, target_y)
        else:
            # Di chuyển bình thường
            await _move_mouse_naturally(page, current_x, current_y, target_x, target_y)

        current_x, current_y = target_x, target_y
        await sleep_ms(120, 520)

        # 10% cơ hội pause giữa chừng (như đang đọc hoặc suy nghĩ)
        if chance(0.10):
            await sleep_ms(400, 1200)

async def _move_mouse_naturally(page: Page, start_x: int, start_y: int, end_x: int, end_y: int):
    """
    Di chuyển chuột theo đường cong tự nhiên với tốc độ thay đổi (ease in/out)
    """
    steps = random.randint(15, 35)

    for i in range(steps + 1):
        t = i / steps

        # Easing function (ease in-out cubic) - tạo gia tốc tự nhiên
        if t < 0.5:
            eased_t = 4 * t * t * t
        else:
            eased_t = 1 - pow(-2 * t + 2, 3) / 2

        # Thêm một chút bezier curve cho path không thẳng
        # Control point ngẫu nhiên để tạo đường cong
        ctrl_x = (start_x + end_x) / 2 + random.randint(-20, 20)
        ctrl_y = (start_y + end_y) / 2 + random.randint(-20, 20)

        # Quadratic Bezier curve
        x = (1 - eased_t) ** 2 * start_x + 2 * (1 - eased_t) * eased_t * ctrl_x + eased_t ** 2 * end_x
        y = (1 - eased_t) ** 2 * start_y + 2 * (1 - eased_t) * eased_t * ctrl_y + eased_t ** 2 * end_y

        # Thêm micro jitter (tay người run)
        x += random.uniform(-0.5, 0.5)
        y += random.uniform(-0.5, 0.5)

        await page.mouse.move(int(x), int(y))

        # Delay ngắn giữa các bước
        if i < steps:
            await asyncio.sleep(random.uniform(0.001, 0.003))

async def human_scroll_wheel(
    page: Page,
    total_px: int,
    *,
    step_range: Tuple[int, int] = (110, 240),
    pause_range: Tuple[int, int] = (160, 650),
    sometimes_hesitate: bool = True,
    sometimes_backtrack: bool = True,
):
    """
    Scroll tự nhiên hơn với:
    - Acceleration/deceleration (chậm ở đầu, nhanh giữa, chậm cuối)
    - Variable step sizes
    - Reading pauses (dừng đọc nội dung)
    - Momentum effect
    """
    if total_px == 0:
        return

    remaining = abs(total_px)
    direction = 1 if total_px > 0 else -1
    step_count = 0
    total_steps = remaining // ((step_range[0] + step_range[1]) // 2)

    while remaining > 0:
        # Tính progress để điều chỉnh tốc độ
        progress = step_count / max(total_steps, 1)

        # Acceleration curve - chậm ở đầu và cuối, nhanh ở giữa
        if progress < 0.2:  # Starting - chậm
            speed_multiplier = 0.5 + progress * 2.5
        elif progress > 0.8:  # Ending - chậm lại
            speed_multiplier = 0.5 + (1 - progress) * 2.5
        else:  # Middle - nhanh
            speed_multiplier = 1.0 + random.uniform(-0.2, 0.3)

        base_step = randi(*step_range)
        step = min(remaining, int(base_step * speed_multiplier))

        # Jitter cho mỗi scroll
        jitter = randi(-25, 25)
        delta = direction * max(30, step + jitter)

        await page.mouse.wheel(0, delta)
        remaining -= step
        step_count += 1

        # Variable pause - đôi khi dừng đọc lâu hơn
        base_pause = randi(*pause_range)

        # 20% cơ hội "reading pause" (dừng đọc nội dung)
        if chance(0.20):
            reading_pause = random.randint(800, 2500)
            await sleep_ms(base_pause + reading_pause, base_pause + reading_pause + 500)
        else:
            await sleep_ms(base_pause, base_pause + 200)

        # Hesitation (do dự, như khi thấy nội dung thú vị)
        if sometimes_hesitate and chance(0.12):
            await sleep_ms(900, 2600)
            # 40% cơ hội scroll lại một tí để xem kỹ hơn
            if chance(0.40):
                await page.mouse.wheel(0, -direction * randi(30, 100))
                await sleep_ms(300, 800)
                # Scroll tiếp
                await page.mouse.wheel(0, direction * randi(20, 80))
                await sleep_ms(200, 500)

        # Backtrack (scroll ngược lại vì scroll quá)
        if sometimes_backtrack and chance(0.08):
            await page.mouse.wheel(0, -direction * randi(40, 120))
            await sleep_ms(140, 480)

        # 5% cơ hội "momentum scroll" - scroll thêm 1-2 lần nhanh (như scroll bánh xe mạnh)
        if chance(0.05) and remaining > step:
            momentum_scrolls = random.randint(1, 2)
            for _ in range(momentum_scrolls):
                await page.mouse.wheel(0, direction * randi(50, 100))
                await sleep_ms(50, 150)

async def watch_like_human(
    page: Page,
    *,
    min_ms: int = 5000,
    max_ms: int = 16000,
    mouse_jitter: bool = True,
):
    """
    Xem video tự nhiên hơn với:
    - Variable attention (đôi khi tập trung, đôi khi lơ đãng)
    - Natural engagement patterns
    - Realistic pauses and micro-movements
    """
    # Tính tổng thời gian xem với distribution lệch (skewed)
    # Con người thường xem nhanh hơn average, nhưng đôi khi xem rất lâu
    alpha, beta = 2, 3
    normalized = random.betavariate(alpha, beta)
    total = int(min_ms + (max_ms - min_ms) * normalized)

    # Thêm variability lớn (10-30% dao động)
    variance = random.uniform(0.9, 1.3)
    total = int(total * variance)
    total = max(min_ms, min(max_ms, total))

    end = asyncio.get_event_loop().time() + (total / 1000)

    # Track engagement level (0-1) - thay đổi theo thời gian
    engagement = random.uniform(0.6, 1.0)

    while asyncio.get_event_loop().time() < end:
        # Engagement decay và recover (con người mất tập trung rồi lại tập trung)
        engagement += random.uniform(-0.15, 0.10)
        engagement = max(0.3, min(1.0, engagement))

        # Pause duration phụ thuộc vào engagement
        if engagement > 0.7:  # Đang tập trung
            base_pause = random.randint(350, 900)
        else:  # Đang lơ đãng
            base_pause = random.randint(200, 500)

        await sleep_ms(base_pause, base_pause + 300)

        # Mouse activity phụ thuộc vào engagement
        if mouse_jitter:
            # High engagement = nhiều mouse movement hơn
            mouse_chance = 0.15 + (engagement * 0.15)
            if chance(mouse_chance):
                await jitter_mouse(page, steps_min=1, steps_max=3)

        # Đôi khi "bored" pause (mất tập trung hoàn toàn)
        if engagement < 0.5 and chance(0.15):
            await sleep_ms(1500, 4000)
            # Sau pause thường recover engagement
            engagement = min(1.0, engagement + 0.3)

        # Active engagement behaviors
        if engagement > 0.75:
            # 10% cơ hội scroll nhỏ (đọc comments hoặc description)
            if chance(0.10):
                await page.mouse.wheel(0, random.randint(-50, 150))
                await sleep_ms(200, 600)
                # Scroll back
                if chance(0.6):
                    await page.mouse.wheel(0, random.randint(-100, 50))
                    await sleep_ms(150, 400)

        # 8% cơ hội long pause (như khi bị distracted)
        if chance(0.08):
            distraction_time = random.randint(2000, 5000)
            await sleep_ms(distraction_time, distraction_time + 1000)
            # Thường quay lại với engagement thấp
            engagement = random.uniform(0.4, 0.7)

        # 5% cơ hội hover vào các element (như muốn click)
        if chance(0.05):
            # Simulate hover near interactive elements
            viewport = page.viewport_size
            if viewport:
                hover_x = random.randint(viewport['width'] - 200, viewport['width'] - 50)
                hover_y = random.randint(100, viewport['height'] - 100)
                await page.mouse.move(hover_x, hover_y)
                await sleep_ms(300, 800)
                # Sometimes click away (changed mind)
                if chance(0.3):
                    await page.mouse.move(hover_x + random.randint(-50, 50), hover_y + random.randint(-50, 50))
                    await sleep_ms(150, 400)

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
    Space-n for TikTok feed với các hành vi tự nhiên:
    - Variable watch time per video (con người không xem đều)
    - Occasional "oops" behaviors (double-press, skip back)
    - Natural rhythm breaks
    """
    # Track watch pattern để tạo rhythm tự nhiên
    last_watch_was_long = False
    skip_streak = 0  # Đếm số lần skip liên tiếp

    for i in range(n):
        if humanize:
            # Video đầu tiên thường xem ngắn hơn (con người test xem có thú vị không)
            if i == 0 and chance(0.40):
                await sleep_ms(900, 4200)
            else:
                # Tạo rhythm tự nhiên: ngắn-dài-ngắn-dài thay vì đều đặn
                if last_watch_was_long and chance(0.6):
                    # Sau video dài thường xem ngắn hơn (fatigue)
                    watch_time = random.randint(watch_min_ms, (watch_min_ms + watch_max_ms) // 2)
                    last_watch_was_long = False
                elif not last_watch_was_long and chance(0.4):
                    # Sau video ngắn có thể xem dài (found interest)
                    watch_time = random.randint((watch_min_ms + watch_max_ms) // 2, watch_max_ms)
                    last_watch_was_long = True
                else:
                    # Random normal
                    watch_time = random.randint(watch_min_ms, watch_max_ms)
                    last_watch_was_long = watch_time > (watch_min_ms + watch_max_ms) * 0.7

                await sleep_ms(watch_time, watch_time + 1000)

            # Skip streak behavior - con người đôi khi skip nhanh nhiều video
            if skip_streak > 2 and chance(0.7):
                # Sau skip streak dài, thường dừng lại xem kỹ
                await sleep_ms(watch_max_ms // 2, watch_max_ms)
                skip_streak = 0
            elif skip_streak > 0:
                skip_streak += 1

        # 6% cơ hội accidental double press (nhấn nhầm 2 lần)
        if humanize and chance(0.06):
            await page.keyboard.press("Space")
            await sleep_ms(80, 240)
            # Nhận ra là nhấn nhầm, đợi một chút rồi tiếp tục
            await sleep_ms(200, 600)
            skip_streak += 2  # Count as 2 skips

        await page.keyboard.press("Space")

        # 3% cơ hội nhấn nhầm quá nhanh rồi quay lại (oops, that was interesting)
        if humanize and i > 0 and chance(0.03):
            await sleep_ms(300, 800)
            # Nhấn arrow up để quay lại video trước
            await page.keyboard.press("ArrowUp")
            await sleep_ms(2000, 5000)  # Xem lại một lúc
            # Rồi skip tiếp
            await page.keyboard.press("Space")
            await sleep_ms(400, 900)

        if delay_max_ms > 0:
            await sleep_ms(delay_min_ms, delay_max_ms)

        if humanize:
            # Variable post-press pause
            base_pause = random.randint(250, 1100)

            # 8% cơ hội long pause (distracted hoặc reading comments)
            if chance(0.08):
                base_pause += random.randint(900, 2400)

            await sleep_ms(base_pause, base_pause + 300)

            # Update skip streak
            if base_pause < 500:
                skip_streak += 1
            else:
                skip_streak = max(0, skip_streak - 1)

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

        page.locator(":text('Switch to public')"),
        page.locator(":text('Got it')"),
        page.locator(":text('Continue')"),
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