import asyncio, requests
from typing import List, Tuple, Dict, Any

from playwright.async_api import async_playwright
from actions.cookie import import_txt_cookie
from utils import safe_print
from actions.behavior import run_tiktok_flow
from actions.search import run_domain_flow

Job = Tuple[str, str, str]  # (profile_name, addr, cookie)

async def _wait_cdp_http_ready(http_base: str, retries: int = 25, delay: float = 0.5) -> bool:
    url = http_base.rstrip("/") + "/json/version"

    def _try_once() -> bool:
        try:
            rr = requests.get(url, timeout=3)
            return rr.status_code == 200
        except Exception:
            return False

    for _ in range(retries):
        ok = await asyncio.to_thread(_try_once)
        if ok:
            return True
        await asyncio.sleep(delay)
    return False

async def _run_browser_one(p, name: str, addr: str, cookie: str, actions: Dict[str, Any]):
    try:
        if not addr:
            safe_print(f"❌ [{name}] Missing addr")
            return

        ok = await _wait_cdp_http_ready(addr)
        if not ok:
            safe_print(f"❌ [{name}] CDP not ready (timeout): {addr}")
            return
        browser = await p.chromium.connect_over_cdp(addr)
        safe_print(f"✅ [{name}] Connected to CDP HTTP: {addr}")

        context = browser.contexts[0] if browser.contexts else await browser.new_context()

        page = context.pages[0] if context.pages else await context.new_page()

        if actions.get("import"):
            try:
                browser = await p.chromium.connect_over_cdp(addr)
                context = browser.contexts[0]
                page = await context.new_page()
                await import_txt_cookie(page, name, cookie)
                safe_print(f"✅ Imported cookie for {name}")
            except Exception as e:
                safe_print(f"❌ Import failed for {name}: {e}")

        # Run behavior actions if pw mode is enabled (CDP mode)
        if actions.get("pw"):
            behavior_mode = actions.get("behavior_mode", "tiktok")

            if behavior_mode == "search":
                # Search mode
                search_time = actions.get("search_time", 5)
                safe_print(f"🔍 [{name}] Running domain visit flow for {search_time} minutes")

                try:
                    safe_print(f"🚀 [{name}] Calling run_domain_flow()...")
                    await asyncio.wait_for(
                        run_domain_flow(
                            page,
                            username=name,
                            search_time=search_time
                        ),
                        timeout=(search_time * 60) + 60  # Search time + 1 minute buffer
                    )
                    safe_print(f"✅ [{name}] run_domain_flow() completed successfully")
                except asyncio.TimeoutError:
                    safe_print(f"⏱️ [{name}] run_domain_flow() TIMEOUT - moving to next profile")
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
                        # Mỗi profile có tối đa 20 phút để hoàn thành tất cả behavior actions
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
                            timeout=1200  # 20 phút timeout
                        )
                        safe_print(f"✅ [{name}] run_tiktok_flow() completed successfully")
                    except asyncio.TimeoutError:
                        safe_print(f"⏱️ [{name}] run_tiktok_flow() TIMEOUT after 20 minutes - moving to next profile")
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