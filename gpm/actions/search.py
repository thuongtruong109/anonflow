import asyncio
import random
from urllib.parse import quote_plus, urlparse
from utils import safe_print
from actions.common import safe_click_locator, human_scroll_wheel, jitter_mouse, human_pause

# Danh sách các domain phổ biến để truy cập ngẫu nhiên
DOMAIN_LIST = [
    "https://www.google.com",
    "https://www.youtube.com",
    "https://www.facebook.com",
    "https://www.twitter.com",
    "https://www.instagram.com",
    "https://www.reddit.com",
    "https://www.wikipedia.org",
    "https://www.amazon.com",
    "https://www.netflix.com",
    "https://www.spotify.com",
    "https://www.github.com",
    "https://www.stackoverflow.com",
    "https://www.nytimes.com",
    "https://www.bbc.com",
    "https://www.cnn.com",
]

# Không còn giới hạn allowed domains, cho phép click vào bất kỳ liên kết nào
ALLOWED_CLICK_DOMAINS = set()  # Để trống để cho phép tất cả

def host_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""

def is_allowed_click(url: str) -> bool:
    return True  # Cho phép tất cả domain

async def random_scroll(page, seconds_min=8, seconds_max=20):
    # Sử dụng human_scroll_wheel từ common.py để scroll tự nhiên hơn
    total_scroll = random.randint(800, 2000)
    await human_scroll_wheel(page, total_scroll)

async def random_click_on_page(page):
    # Tìm tất cả liên kết trên trang
    links = await page.query_selector_all("a[href]")
    if links:
        # Chọn một liên kết ngẫu nhiên
        link = random.choice(links[:min(20, len(links))])  # Giới hạn để tránh quá nhiều
        href = await link.get_attribute("href")
        if href:
            safe_print(f"➡️ Clicking random link: {href}")
            # Sử dụng safe_click_locator từ common.py để click an toàn hơn
            success = await safe_click_locator(link, timeout_ms=5000)
            if success:
                await page.wait_for_load_state("domcontentloaded")
                return href
            else:
                safe_print(f"⚠️ Click failed: Element not clickable")
    return None

async def perform_random_actions(page, actions_count=3):
    for _ in range(actions_count):
        action = random.choice(["scroll", "click", "wait", "jitter"])
        if action == "scroll":
            await random_scroll(page, 5, 10)
        elif action == "click":
            await random_click_on_page(page)
        elif action == "wait":
            await human_pause(1000, 3000)  # Sử dụng human_pause từ common.py
        elif action == "jitter":
            await jitter_mouse(page, steps_min=1, steps_max=3)  # Di chuyển chuột ngẫu nhiên

async def run_domain_flow(page, username: str, search_time: int):
    safe_print(f"🌐 [{username}] Starting random domain visit flow for {search_time} minutes")

    end_time = asyncio.get_event_loop().time() + (search_time * 60)
    n = 0

    while asyncio.get_event_loop().time() < end_time:
        try:
            domain = random.choice(DOMAIN_LIST)
            n += 1

            safe_print(f"🔗 [{username}] Visiting domain #{n}: {domain}")
            await page.goto(domain, wait_until="domcontentloaded")
            await human_pause(2000, 4000)  # Sử dụng human_pause thay vì asyncio.sleep
            # Chờ thêm để đảm bảo trang load hoàn toàn
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Thực hiện các thao tác ngẫu nhiên trên domain
            await perform_random_actions(page, random.randint(1, 5))

            await asyncio.sleep(random.uniform(8, 18))

        except Exception as e:
            safe_print(f"⚠️ [{username}] flow error: {e}")
            await asyncio.sleep(random.uniform(5, 10))

    safe_print(f"✅ [{username}] Completed - {n} domain visits")
