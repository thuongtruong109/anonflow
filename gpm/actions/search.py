import asyncio
import random
from dataclasses import dataclass
from typing import List, Optional, Set

from utils import safe_print
from actions.common import (
    safe_click_locator,
    human_scroll_wheel,
    jitter_mouse,
    human_pause,
)

visited_urls: Set[str] = set()
last_actions: List[str] = []

@dataclass
class DomainProfile:
    url: str
    weight: int = 10
    dwell_s: tuple[int, int] = (12, 35)
    actions_range: tuple[int, int] = (2, 6)

DOMAIN_PROFILES: List[DomainProfile] = [
    DomainProfile("https://www.google.com", weight=28, dwell_s=(10, 30), actions_range=(2, 5)),
    DomainProfile("https://www.bing.com", weight=10, dwell_s=(10, 28), actions_range=(2, 5)),
    DomainProfile("https://duckduckgo.com", weight=10, dwell_s=(10, 28), actions_range=(2, 5)),
    DomainProfile("https://search.brave.com", weight=6, dwell_s=(10, 28), actions_range=(2, 5)),
    DomainProfile("https://www.ecosia.org", weight=4, dwell_s=(10, 28), actions_range=(2, 5)),
    DomainProfile("https://www.startpage.com", weight=4, dwell_s=(10, 28), actions_range=(2, 5)),
    DomainProfile("https://www.youtube.com", weight=18, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.tiktok.com", weight=14, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.instagram.com", weight=10, dwell_s=(20, 80), actions_range=(2, 6)),
    DomainProfile("https://www.facebook.com", weight=10, dwell_s=(20, 80), actions_range=(2, 6)),
    DomainProfile("https://twitter.com", weight=8, dwell_s=(15, 60), actions_range=(2, 6)),
    DomainProfile("https://x.com", weight=8, dwell_s=(15, 60), actions_range=(2, 6)),
    DomainProfile("https://www.pinterest.com", weight=6, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.reddit.com", weight=14, dwell_s=(30, 120), actions_range=(3, 7)),
    DomainProfile("https://news.ycombinator.com", weight=8, dwell_s=(20, 60), actions_range=(2, 6)),
    DomainProfile("https://www.quora.com", weight=6, dwell_s=(25, 90), actions_range=(2, 6)),
    DomainProfile("https://stackexchange.com", weight=6, dwell_s=(20, 60), actions_range=(2, 6)),
    DomainProfile("https://www.wikipedia.org", weight=14, dwell_s=(40, 180), actions_range=(2, 6)),
    DomainProfile("https://medium.com", weight=8, dwell_s=(40, 180), actions_range=(2, 6)),
    DomainProfile("https://www.britannica.com", weight=6, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.investopedia.com", weight=6, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.healthline.com", weight=5, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.webmd.com", weight=5, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://github.com", weight=8, dwell_s=(20, 60), actions_range=(2, 6)),
    DomainProfile("https://gitlab.com", weight=5, dwell_s=(20, 60), actions_range=(2, 6)),
    DomainProfile("https://developer.mozilla.org", weight=6, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://stackoverflow.com", weight=8, dwell_s=(20, 60), actions_range=(2, 6)),
    DomainProfile("https://dev.to", weight=5, dwell_s=(25, 90), actions_range=(2, 6)),
    DomainProfile("https://hashnode.com", weight=4, dwell_s=(25, 90), actions_range=(2, 6)),
    DomainProfile("https://www.bbc.com", weight=7, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.reuters.com", weight=6, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://apnews.com", weight=5, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.theguardian.com", weight=5, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.nytimes.com", weight=4, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.cnn.com", weight=4, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.wsj.com", weight=3, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.forbes.com", weight=4, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.bloomberg.com", weight=4, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.amazon.com", weight=10, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.ebay.com", weight=6, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.etsy.com", weight=5, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.walmart.com", weight=5, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.target.com", weight=4, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.bestbuy.com", weight=4, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.newegg.com", weight=4, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.aliexpress.com", weight=4, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://shopee.vn", weight=4, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://www.lazada.vn", weight=4, dwell_s=(20, 90), actions_range=(2, 6)),
    DomainProfile("https://open.spotify.com", weight=6, dwell_s=(30, 120), actions_range=(2, 5)),
    DomainProfile("https://soundcloud.com", weight=4, dwell_s=(30, 120), actions_range=(2, 5)),
    DomainProfile("https://www.netflix.com", weight=4, dwell_s=(30, 120), actions_range=(2, 5)),
    DomainProfile("https://www.imdb.com", weight=5, dwell_s=(20, 60), actions_range=(2, 5)),
    DomainProfile("https://letterboxd.com", weight=4, dwell_s=(20, 60), actions_range=(2, 5)),
    DomainProfile("https://www.tripadvisor.com", weight=4, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.booking.com", weight=4, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.airbnb.com", weight=4, dwell_s=(30, 120), actions_range=(2, 6)),
    DomainProfile("https://www.lonelyplanet.com", weight=3, dwell_s=(30, 120), actions_range=(2, 6)),
]

def pick_domain_profile() -> DomainProfile:
    weights = [p.weight for p in DOMAIN_PROFILES]
    return random.choices(DOMAIN_PROFILES, weights=weights, k=1)[0]

GOOGLE_QUERIES = [
    "how to cook pasta", "best laptop 2026", "weather today", "funny cat videos", "learn python programming", "best restaurants near me", "news today",
    "how to tie a tie", "workout routine", "healthy recipes", "travel destinations", "movie reviews", "book recommendations", "tech news", "science articles",
    "diy projects", "gardening tips", "photography tutorial", "music playlists", "game reviews", "productivity apps", "how to meditate", "investment tips",
    "fashion trends", "home decor ideas", "pet care tips", "language learning", "recipe ideas", "fitness motivation", "car reviews", "smartphone comparison",
    "Planet Fitness", "Pinterest", "Yankees", "Facebook Marketplace", "Zoom", "Pizza Hut", "Subway", "NFL", "Pandora", "Spotify", "Nike", "Twitter", "FedEx", "Food Near Me", "Disney Plus", "Home Depot", "Champions League", "Amazon Prime", "Sams Club",
    "Kahoot", "YouTube TV", "McDonalds", "USPS Tracking", "Hobby Lobby", "Dollar Tree", "Chipotle", "Southwest Airlines", "Apple", "Netflix", "Taco Bell", "Starbucks", "Outlook", "YouTube", "Old Navy",
    "Ikea", "Weather", "Harbor Freight", "FedEx Tracking", "TikTok",  "Daily Mail", "AutoZone", "Translate",
    "MLB", "Amazon", "Internet Speed Test", "Google Drive", "Google Classroom", "CNN", "Dow Jones", "Omegle", "Chase", "CVS", "Walgreens", "Dominos",
    "Roblox", "Premier League", "Target", "NBA", "Capital One", "Bank of America", "American Airlines", "Airbnb", "AOL Mail", "Wordle", "Wells Fargo",
    "Twitch", "Shein", "Restaurants Near Me", "MSN", "Craigslist", "LinkedIn", "Hotmail", "English to Spanish", "Ebay",  "Discord", "Canva", "PayPal", "Etsy", "OnlyFans", "Google Docs",
    "Zillow", "Best Buy", "Costco", "Google Flights", "Instagram", "Weather Tomorrow", "Walmart", "Google Maps",
    "Indeed", "Calculator", "Traductor", "ESPN", "ChatGPT", "Google", "Yahoo Mail", "Fox News", "Yahoo", "Google Translate", "Gmail", "Facebook",
]

async def human_type_text(page, selector: str, text: str):
    try:
        element = await page.wait_for_selector(selector, timeout=5000)
        await element.click()
        await human_pause(200, 600)

        for char in text:
            await element.type(char, delay=random.randint(80, 250))
            if char == ' ' and random.random() < 0.3:
                await human_pause(100, 400)

        await human_pause(300, 800)
    except Exception as e:
        safe_print(f"⚠️ Typing error: {e}")

async def google_search_flow(page, username: str):
    try:
        safe_print(f"🔍 [{username}] Starting Google search flow")

        await page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=30000)
        await human_pause(800, 2000)

        available_queries = [q for q in GOOGLE_QUERIES if q not in last_actions[-5:]]
        if not available_queries:
            available_queries = GOOGLE_QUERIES
        query = random.choice(available_queries)
        last_actions.append(query)
        if len(last_actions) > 10:
            last_actions.pop(0)

        safe_print(f"🔍 [{username}] Searching for: {query}")

        search_selectors = ['textarea[name="q"]', 'input[name="q"]', 'textarea[title="Search"]']
        typed = False
        for selector in search_selectors:
            try:
                await human_type_text(page, selector, query)
                typed = True
                break
            except:
                continue

        if not typed:
            safe_print(f"⚠️ [{username}] Could not find search box")
            return

        if random.random() < 0.7:
            await page.keyboard.press("Enter")
        else:
            try:
                search_btn = await page.wait_for_selector('input[value="Google Search"]', timeout=2000)
                await search_btn.click()
            except:
                await page.keyboard.press("Enter")

        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await human_pause(1000, 2500)

        await human_scroll_wheel(page, random.randint(400, 1200), step_range=(80, 200))
        await human_pause(800, 2000)

        try:
            results = await page.query_selector_all('a h3')
            if results and len(results) > 0:
                start_idx = 1 if random.random() < 0.4 else 0
                result_idx = random.randint(start_idx, min(len(results) - 1, 7))
                result = results[result_idx]

                await result.hover(timeout=1000)
                await human_pause(200, 600)

                parent_link = await result.evaluate_handle('el => el.closest("a")')
                href = await parent_link.evaluate('el => el.href') if parent_link else None

                if href:
                    safe_print(f"🔗 [{username}] Clicking search result #{result_idx + 1}")
                    await parent_link.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    await human_pause(1500, 3500)

                    read_time = random.randint(8, 25)
                    safe_print(f"📖 [{username}] Reading page for {read_time}s")
                    for _ in range(read_time // 4):
                        await human_scroll_wheel(page, random.randint(200, 600))
                        await human_pause(2000, 4500)

                    if random.random() < 0.8:
                        safe_print(f"⬅️ [{username}] Going back to search results")
                        await page.go_back(wait_until="domcontentloaded", timeout=12000)
                        await human_pause(1000, 2500)
        except Exception as e:
            safe_print(f"⚠️ [{username}] Search result click error: {e}")

        safe_print(f"✅ [{username}] Google search flow completed")

    except Exception as e:
        safe_print(f"⚠️ [{username}] Google search flow error: {e}")

async def random_window_adjustment(page):
    try:
        action = random.choice(["resize", "zoom", "scroll_position"])

        if action == "resize":
            current_size = await page.evaluate("() => ({ width: window.innerWidth, height: window.innerHeight })")
            new_width = current_size["width"] + random.randint(-50, 50)
            new_height = current_size["height"] + random.randint(-30, 30)
            new_width = max(800, min(new_width, 1920))
            new_height = max(600, min(new_height, 1080))

            await page.set_viewport_size({"width": new_width, "height": new_height})
            safe_print(f"🖥️ Resized window to {new_width}x{new_height}")

        elif action == "zoom":
            zoom_levels = [0.9, 0.95, 1.0, 1.05, 1.1]
            zoom = random.choice(zoom_levels)
            await page.evaluate(f"document.body.style.zoom = {zoom}")
            safe_print(f"🔍 Set zoom to {int(zoom * 100)}%")

        elif action == "scroll_position":
            scroll_to = random.randint(0, 800)
            await page.evaluate(f"window.scrollTo(0, {scroll_to})")
            safe_print(f"📜 Scrolled to position {scroll_to}")

        await human_pause(400, 1000)

    except Exception as e:
        safe_print(f"⚠️ Window adjustment error: {e}")

async def random_scroll(page):
    patterns = ["smooth", "burst", "reading"]
    pattern = random.choice(patterns)

    if pattern == "smooth":
        total_scroll = random.randint(600, 2400)
        await human_scroll_wheel(
            page,
            total_scroll,
            step_range=(90, 260),
            pause_range=(140, 900),
            sometimes_hesitate=True,
            sometimes_backtrack=True,
        )
    elif pattern == "burst":
        for _ in range(random.randint(2, 5)):
            await human_scroll_wheel(page, random.randint(200, 500), step_range=(150, 300))
            await human_pause(800, 2000)
    else:
        for _ in range(random.randint(3, 7)):
            await human_scroll_wheel(page, random.randint(100, 300), step_range=(50, 120))
            await human_pause(1500, 4000)

async def maybe_back_forward(page):
    if random.random() < 0.12:
        try:
            await page.go_back(wait_until="domcontentloaded", timeout=12000)
            await human_pause(600, 1600)
        except Exception:
            return
    if random.random() < 0.08:
        try:
            await page.go_forward(wait_until="domcontentloaded", timeout=12000)
            await human_pause(600, 1600)
        except Exception:
            return

async def random_click_on_page(page):
    try:
        links = await page.query_selector_all("a[href]")
        if not links:
            return None

        visible_links = []
        for link in links[:50]:
            try:
                is_visible = await link.is_visible()
                if is_visible:
                    visible_links.append(link)
            except:
                continue

        if not visible_links:
            visible_links = links[:35]

        link = random.choice(visible_links)
        href = await link.get_attribute("href")

        if not href:
            return None

        if href in visited_urls and len(visited_urls) < 20:
            return None

        visited_urls.add(href)
        if len(visited_urls) > 30:
            visited_urls.pop()

        safe_print(f"➡️ Clicking link: {href[:80]}")

        try:
            await link.hover(timeout=1000)
            await human_pause(150, 600)
        except Exception:
            pass

        success = await safe_click_locator(link, timeout_ms=5000)
        if success:
            await page.wait_for_load_state("domcontentloaded", timeout=12000)
            await human_pause(1200, 3200)
            return href
    except Exception as e:
        msg = str(e).lower()
        if "closed" in msg or "target" in msg:
            safe_print("🛑 Browser closed during click action")
            raise
        safe_print(f"⚠️ Click action error: {e}")
    return None

async def perform_random_actions(page, actions_count=3):
    recent_actions = []

    for i in range(actions_count):
        try:
            all_actions = ["scroll", "click", "wait", "jitter", "back_forward", "window_adjust", "google_search"]
            available_actions = [a for a in all_actions if a not in recent_actions[-2:]]

            if not available_actions:
                available_actions = all_actions

            action = random.choices(
                available_actions,
                weights=[20 if a == "scroll" else
                        30 if a == "click" else
                        15 if a == "wait" else
                        12 if a == "jitter" else
                        8 if a == "back_forward" else
                        10 if a == "google_search" else
                        5 for a in available_actions],
                k=1,
            )[0]

            recent_actions.append(action)
            if len(recent_actions) > 4:
                recent_actions.pop(0)

            if action == "scroll":
                await random_scroll(page)
            elif action == "click":
                await random_click_on_page(page)
            elif action == "wait":
                wait_time = random.randint(1500, 5500)
                safe_print(f"⏸️ Pausing for {wait_time/1000:.1f}s")
                await human_pause(wait_time, wait_time + 1000)
            elif action == "jitter":
                await jitter_mouse(page, steps_min=2, steps_max=5)
            elif action == "back_forward":
                await maybe_back_forward(page)
            elif action == "window_adjust":
                await random_window_adjustment(page)
            elif action == "google_search":
                if random.random() < 0.3:
                    await google_search_flow(page, "user")

            await human_pause(350, 1800)

        except Exception as e:
            msg = str(e).lower()
            if "closed" in msg or "target" in msg:
                raise
            safe_print(f"⚠️ Random action error: {e}")

async def run_domain_flow(page, username: str, search_time: int):
    safe_print(f"🌐 [{username}] Starting human-like domain flow for {search_time} minutes")

    end_time = asyncio.get_event_loop().time() + (search_time * 60)
    n = 0
    last_domain = None

    while asyncio.get_event_loop().time() < end_time:
        profile = pick_domain_profile()
        retry_count = 0
        while profile.url == last_domain and retry_count < 5:
            profile = pick_domain_profile()
            retry_count += 1

        last_domain = profile.url
        n += 1

        try:
            safe_print(f"🔗 [{username}] Visiting #{n}: {profile.url}")

            if "google.com" in profile.url and random.random() < 0.6:
                await google_search_flow(page, username)
            else:
                await page.goto(profile.url, wait_until="domcontentloaded", timeout=30000)
                await human_pause(1200, 3200)

                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass

            if random.random() < 0.15:
                await random_window_adjustment(page)

            actions_count = random.randint(*profile.actions_range)
            await perform_random_actions(page, actions_count=actions_count)

            dwell = random.randint(*profile.dwell_s)
            chunks = max(1, dwell // 12)

            for i in range(chunks):
                await human_pause(2000, 6000)

                rand = random.random()
                if rand < 0.25:
                    await jitter_mouse(page, steps_min=1, steps_max=3)
                elif rand < 0.45:
                    await human_scroll_wheel(page, random.randint(80, 350))
                elif rand < 0.55:
                    await random_click_on_page(page)
                elif rand < 0.65:
                    await human_scroll_wheel(page, random.randint(100, 200))
                    await human_pause(300, 700)
                    await human_scroll_wheel(page, -random.randint(50, 120))

            await asyncio.sleep(random.uniform(5, 18))

        except Exception as e:
            msg = str(e).lower()
            if "closed" in msg or "target" in msg:
                safe_print(f"🛑 [{username}] Browser/context closed - stopping (visited {n})")
                return
            safe_print(f"⚠️ [{username}] flow error: {e}")
            await asyncio.sleep(random.uniform(4, 10))

    safe_print(f"✅ [{username}] Completed - {n} domain visits")

