import asyncio
import random
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote_plus, urlparse

from utils import safe_print
from actions.common import (
    safe_click_locator,
    human_scroll_wheel,
    jitter_mouse,
    human_pause,
)

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

    DomainProfile("https://www.youtube.com", weight=18, dwell_s=(25, 80), actions_range=(2, 6)),
    DomainProfile("https://www.instagram.com", weight=10, dwell_s=(18, 60), actions_range=(2, 6)),
    DomainProfile("https://www.facebook.com", weight=10, dwell_s=(18, 60), actions_range=(2, 6)),
    DomainProfile("https://www.reddit.com", weight=14, dwell_s=(20, 70), actions_range=(3, 7)),
    DomainProfile("https://news.ycombinator.com", weight=8, dwell_s=(18, 55), actions_range=(2, 6)),

    DomainProfile("https://www.wikipedia.org", weight=12, dwell_s=(25, 90), actions_range=(2, 6)),
    DomainProfile("https://medium.com", weight=6, dwell_s=(25, 90), actions_range=(2, 6)),
    DomainProfile("https://www.quora.com", weight=5, dwell_s=(20, 70), actions_range=(2, 6)),

    DomainProfile("https://github.com", weight=8, dwell_s=(18, 55), actions_range=(2, 6)),
    DomainProfile("https://developer.mozilla.org", weight=6, dwell_s=(18, 65), actions_range=(2, 6)),
    DomainProfile("https://stackoverflow.com", weight=8, dwell_s=(18, 60), actions_range=(2, 6)),

    DomainProfile("https://www.bbc.com", weight=7, dwell_s=(22, 75), actions_range=(2, 6)),
    DomainProfile("https://www.reuters.com", weight=6, dwell_s=(22, 75), actions_range=(2, 6)),
    DomainProfile("https://apnews.com", weight=5, dwell_s=(22, 75), actions_range=(2, 6)),
    DomainProfile("https://www.theguardian.com", weight=5, dwell_s=(22, 75), actions_range=(2, 6)),
    DomainProfile("https://www.nytimes.com", weight=4, dwell_s=(22, 75), actions_range=(2, 6)),

    DomainProfile("https://www.amazon.com", weight=10, dwell_s=(18, 60), actions_range=(2, 6)),
    DomainProfile("https://www.ebay.com", weight=6, dwell_s=(18, 60), actions_range=(2, 6)),
    DomainProfile("https://www.etsy.com", weight=4, dwell_s=(18, 60), actions_range=(2, 6)),
    DomainProfile("https://www.walmart.com", weight=4, dwell_s=(18, 60), actions_range=(2, 6)),
    DomainProfile("https://www.aliexpress.com", weight=4, dwell_s=(18, 60), actions_range=(2, 6)),

    DomainProfile("https://open.spotify.com", weight=6, dwell_s=(20, 70), actions_range=(2, 5)),
    DomainProfile("https://www.netflix.com", weight=4, dwell_s=(20, 60), actions_range=(2, 5)),
]

def pick_domain_profile() -> DomainProfile:
    weights = [p.weight for p in DOMAIN_PROFILES]
    return random.choices(DOMAIN_PROFILES, weights=weights, k=1)[0]

async def random_scroll(page):
    total_scroll = random.randint(600, 2400)
    await human_scroll_wheel(
        page,
        total_scroll,
        step_range=(90, 260),
        pause_range=(140, 900),
        sometimes_hesitate=True,
        sometimes_backtrack=True,
    )

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

        candidates = links[: min(35, len(links))]
        link = random.choice(candidates)

        href = await link.get_attribute("href")
        if not href:
            return None

        safe_print(f"➡️ Clicking link: {href}")

        try:
            await link.hover(timeout=800)
            await human_pause(120, 520)
        except Exception:
            pass

        success = await safe_click_locator(link, timeout_ms=5000)
        if success:
            await page.wait_for_load_state("domcontentloaded", timeout=12000)
            await human_pause(900, 2600)
            return href
    except Exception as e:
        msg = str(e).lower()
        if "closed" in msg or "target" in msg:
            safe_print("🛑 Browser closed during click action")
            raise
        safe_print(f"⚠️ Click action error: {e}")
    return None

async def perform_random_actions(page, actions_count=3):
    for _ in range(actions_count):
        try:
            action = random.choices(
                ["scroll", "click", "wait", "jitter", "back_forward"],
                weights=[34, 22, 20, 14, 10],
                k=1,
            )[0]

            if action == "scroll":
                await random_scroll(page)
            elif action == "click":
                await random_click_on_page(page)
            elif action == "wait":
                await human_pause(1200, 4800)
            elif action == "jitter":
                await jitter_mouse(page, steps_min=1, steps_max=3)
            elif action == "back_forward":
                await maybe_back_forward(page)

            await human_pause(250, 1200)

        except Exception as e:
            msg = str(e).lower()
            if "closed" in msg or "target" in msg:
                raise
            safe_print(f"⚠️ Random action error: {e}")

async def run_domain_flow(page, username: str, search_time: int):
    safe_print(f"🌐 [{username}] Starting human-like domain flow for {search_time} minutes")

    end_time = asyncio.get_event_loop().time() + (search_time * 60)
    n = 0

    while asyncio.get_event_loop().time() < end_time:
        profile = pick_domain_profile()
        n += 1

        try:
            safe_print(f"🔗 [{username}] Visiting #{n}: {profile.url}")
            await page.goto(profile.url, wait_until="domcontentloaded", timeout=30000)

            await human_pause(1200, 3200)

            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            actions_count = random.randint(*profile.actions_range)
            await perform_random_actions(page, actions_count=actions_count)

            dwell = random.randint(*profile.dwell_s)
            for _ in range(max(1, dwell // 15)):
                await human_pause(2500, 5200)
                if random.random() < 0.25:
                    await jitter_mouse(page, steps_min=1, steps_max=2)
                if random.random() < 0.30:
                    await human_scroll_wheel(page, random.randint(120, 380))

            await asyncio.sleep(random.uniform(6, 16))

        except Exception as e:
            msg = str(e).lower()
            if "closed" in msg or "target" in msg:
                safe_print(f"🛑 [{username}] Browser/context closed - stopping (visited {n})")
                return
            safe_print(f"⚠️ [{username}] flow error: {e}")
            await asyncio.sleep(random.uniform(4, 10))

    safe_print(f"✅ [{username}] Completed - {n} domain visits")
