import threading, sys, logging

print_lock = threading.Lock()

profile_cache = {}
cache_lock = threading.Lock()

started_debug_addrs = []  # list[tuple[str, str]]
started_lock = threading.Lock()

pw_jobs = []  # list[tuple[str, str, str]] - (profile_name, addr, cookie)
pw_jobs_lock = threading.Lock()

start_sem = None

EXCEL_PATH = "data/proxies.xlsx"
COOKIES_DIR = "data/cookies"
EXTENSIONS_DIR = "data/extensions"
GPM_EXTENSION_LOCATE = "C:\\Users\\admin\\Documents\\GPMLogin\\GlobalExt"

THREADS = 6
START_LIMIT = 5
REQUEST_TIMEOUT = 30

GPM_API = "http://127.0.0.1:19995"
GROUP_NAME = "All"
BROWSER_CORE = "chromium"
BROWSER_NAME = "Chrome"

SCREEN_W = 1920
SCREEN_H = 1080
TASKBAR_H = 30
GAP = 1
ROWS = 3
COLS = 4

START_WIN_SCALE = None
START_WIN_SIZE = "470,347"

def setup_logger():
    logger = logging.getLogger("my_app")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # file_handler = logging.FileHandler("app.log", encoding="utf-8")
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    # file_handler = logging.FileHandler("like.log", encoding="utf-8")
    # file_handler.setLevel(logging.INFO)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    # file_handler = logging.FileHandler("comment.log", encoding="utf-8")
    # file_handler.setLevel(logging.INFO)
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    logger.propagate = False

    return logger
