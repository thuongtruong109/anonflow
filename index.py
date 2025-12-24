import asyncio
from playwright.async_api import async_playwright, TimeoutError

MAX_CONCURRENT = 5
HEADLESS = False
TARGET_URL = "https://google.com"

sem = asyncio.Semaphore(MAX_CONCURRENT)

def load_proxies():
    with open("proxies.txt", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def parse_proxy(proxy_str):
    parts = proxy_str.split(":")
    if len(parts) != 4:
        print(f"[WARN] Proxy sai định dạng: {proxy_str}")
        return None
    ip, port, user, pwd = parts
    return {
        "server": f"http://{ip}:{port}",
        "username": user,
        "password": pwd
    }

async def run_proxy(playwright, proxy, index):
    async with sem:
        try:
            browser = await playwright.chromium.launch(
                headless=HEADLESS,
                proxy=proxy
            )
            context = await browser.new_context()
            page = await context.new_page()

            # Interact with the page

            await page.goto(TARGET_URL, timeout=120000)
            print(f"[PROXY {index}] OPENED | {proxy['server']}")

            await page.wait_for_timeout(20000)

            await browser.close()

        except TimeoutError:
            print(f"[PROXY {index}] TIMEOUT")
        except Exception as e:
            print(f"[PROXY {index}] ERROR: {e}")


async def main():
    proxies_raw = load_proxies()
    proxies = [parse_proxy(p) for p in proxies_raw if parse_proxy(p)]

    async with async_playwright() as p:
        tasks = [
            asyncio.create_task(run_proxy(p, proxy, i+1))
            for i, proxy in enumerate(proxies)
        ]
        await asyncio.gather(*tasks)

    print("DONE ALL PROXIES")

if __name__ == "__main__":
    asyncio.run(main())
