import asyncio, requests
from typing import List, Tuple, Dict, Any

from playwright.async_api import async_playwright
from actions.cookie import import_txt_cookie
from utils import safe_print
from actions.behavior import run_tiktok_flow
from actions.search import run_domain_flow
import config

Job = Tuple[str, str, str]  # (profile_name, addr, cookie)

async def _wait_cdp_http_ready(http_base: str, retries: int = 120, delay: float = 1.0) -> bool:
    """Wait for CDP connection to be ready. Increased retries from 60 to 120 (2 minutes)"""
    url = http_base.rstrip("/") + "/json/version"

    def _try_once() -> bool:
        try:
            rr = requests.get(url, timeout=5)
            return rr.status_code == 200
        except Exception:
            return False

    for i in range(retries):
        ok = await asyncio.to_thread(_try_once)
        if ok:
            return True
        # Log progress every 15 seconds to show it's still trying
        if i > 0 and i % 15 == 0:
            safe_print(f"⏳ Still waiting for CDP connection... ({i}/{retries} seconds)")
        await asyncio.sleep(delay)
    return False

async def _run_browser_one(p, name: str, addr: str, cookie: str, actions: Dict[str, Any]):
    try:
        if not addr:
            safe_print(f"❌ [{name}] Missing addr")
            return

        safe_print(f"⏳ [{name}] Waiting for CDP connection: {addr}")
        ok = await _wait_cdp_http_ready(addr)
        if not ok:
            safe_print(f"❌ [{name}] CDP not ready (timeout after 120 seconds): {addr}")
            safe_print(f"💡 Tip: This profile might be slow to start. Try:")
            safe_print(f"   - Reduce START_LIMIT (current: {config.START_LIMIT})")
            safe_print(f"   - Close other profiles to free resources")
            safe_print(f"   - Check if GPM is overloaded")
            return
        browser = await p.chromium.connect_over_cdp(addr)
        safe_print(f"✅ [{name}] Connected to CDP: {addr}")

        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        page = context.pages[0] if context.pages else await context.new_page()

        if actions.get("import"):
            try:
                safe_print(f"🍪 [{name}] Starting cookie import...")
                browser = await p.chromium.connect_over_cdp(addr)
                context = browser.contexts[0]
                page = await context.new_page()
                await import_txt_cookie(page, name, cookie)
                safe_print(f"✅ [{name}] Imported cookies successfully")
            except Exception as e:
                safe_print(f"❌ [{name}] Import failed: {e}")

        # Run behavior actions if pw mode is enabled (CDP mode)
        if actions.get("pw"):
            behavior_mode = actions.get("behavior_mode", "tiktok")

            if behavior_mode == "search":
                # Search mode
                search_time = actions.get("search_time", 5)
                safe_print(f"🔍 [{name}] Running domain visit flow for {search_time} minutes")

                try:
                    safe_print(f"🚀 [{name}] Calling run_domain_flow()...")
                    # Increased timeout: search_time * 60 + 5 minutes buffer (instead of 1 minute)
                    # This gives more time for slow pages, network issues, etc.
                    timeout_seconds = (search_time * 60) + 300
                    safe_print(f"⏱️ [{name}] Flow timeout set to {timeout_seconds//60} minutes")
                    await asyncio.wait_for(
                        run_domain_flow(
                            page,
                            username=name,
                            search_time=search_time
                        ),
                        timeout=timeout_seconds
                    )
                    safe_print(f"✅ [{name}] run_domain_flow() completed successfully")
                except asyncio.TimeoutError:
                    safe_print(f"⏱️ [{name}] run_domain_flow() TIMEOUT after {timeout_seconds//60} minutes - moving to next profile")
                except Exception as flow_error:
                    safe_print(f"❌ [{name}] run_domain_flow() error: {flow_error}")
                    import traceback
                    traceback.print_exc()

            else:
                # Tiktok mode - existing behavior flow
                safe_print(f"🎬 [{name}] Running behavior flow with actions: follow={actions.get('follow', False)}, like={actions.get('like_video', False)}, comment={actions.get('comment', False)}, view={actions.get('view_video', False)}")

                # Check if at least one behavior action is selected
                has_any_action = (
                    actions.get("follow", False) or
                    actions.get("like_video", False) or
                    actions.get("comment", False) or
                    actions.get("view_video", False)
                )

                if not has_any_action:
                    safe_print(f"⚠️ [{name}] No behavior actions selected. Skipping behavior flow.")
                else:
                    try:
                        safe_print(f"🚀 [{name}] Calling run_tiktok_flow()...")
                        # Set timeout cho toàn bộ flow để tránh treo vô tận
                        # Increased from 20 to 30 minutes for more reliability
                        timeout_seconds = 1800  # 30 phút
                        safe_print(f"⏱️ [{name}] Flow timeout set to {timeout_seconds//60} minutes")
                        await asyncio.wait_for(
                            run_tiktok_flow(
                                page,
                                username=name,
                                follow=actions.get("follow", False),
                                like_video=actions.get("like_video", False),
                                comment=actions.get("comment", False),
                                view_video=actions.get("view_video", False),
                                view_amount=actions.get("view_amount"),
                                follow_mode=actions.get("follow_mode", "random"),
                                follow_target=actions.get("follow_target"),
                                all_usernames=actions.get("all_usernames"),
                            ),
                            timeout=timeout_seconds
                        )
                        safe_print(f"✅ [{name}] run_tiktok_flow() completed successfully")
                    except asyncio.TimeoutError:
                        safe_print(f"⏱️ [{name}] run_tiktok_flow() TIMEOUT after {timeout_seconds//60} minutes - moving to next profile")
                    except Exception as flow_error:
                        safe_print(f"❌ [{name}] run_tiktok_flow() error: {flow_error}")
                        import traceback
                        traceback.print_exc()

    except Exception as e:
        safe_print(f"❌ [PW] {name}: {e}")
        import traceback
        traceback.print_exc()

async def run_all_playwright(jobs: List[Job], actions: Dict[str, Any]):
    # Nếu follow mode là mutual, tạo danh sách tất cả usernames để follow lẫn nhau
    all_usernames = []
    if actions.get("follow_mode") == "mutual":
        all_usernames = [name for name, _, _ in jobs]
        safe_print(f"🔄 Mutual follow mode: {len(all_usernames)} profiles will follow each other")
        # Pass danh sách usernames vào actions
        actions["all_usernames"] = all_usernames

    async with async_playwright() as p:
        await asyncio.gather(
            *(_run_browser_one(p, name, addr, cookie, actions) for name, addr, cookie in jobs),
            return_exceptions=True
        )