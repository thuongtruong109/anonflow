import threading

print_lock = threading.Lock()

profile_cache = {}
cache_lock = threading.Lock()

started_debug_addrs = []  # list[tuple[str, str]]
started_lock = threading.Lock()

start_sem = None

GPM_API = "http://127.0.0.1:19995"
EXCEL_PATH = "proxies.xlsx"
COOKIES_DIR = "cookies"

GROUP_NAME = "All"
BROWSER_CORE = "chromium"
BROWSER_NAME = "Chrome"

THREADS = 6
START_LIMIT = 3
REQUEST_TIMEOUT = 30

SCREEN_W = 1920
SCREEN_H = 1080
TASKBAR_H = 40
GAP = 3

START_WIN_SCALE = None
START_WIN_SIZE = "640,520"
