import threading, sys, logging, os, time
from logging.handlers import RotatingFileHandler

print_lock = threading.Lock()

profile_cache = {}
cache_lock = threading.Lock()

started_debug_addrs = []  # list[tuple[str, str]]
started_lock = threading.Lock()

pw_jobs = []  # list[tuple[str, str, str]] - (profile_name, addr, cookie)
pw_jobs_lock = threading.Lock()

start_sem = None

EXCEL_PATH = "data/profiles.xlsx"
COOKIES_DIR = "data/cookies"
EXTENSIONS_DIR = "data/extensions"
COOKIE_IMPORTER_EXTENSION_ID = "kndjfojeoamnpbehojpbflmnleahimkb"
GPM_EXTENSION_LOCATE = "C://Users/admin/Documents/GPMLogin/GlobalExt"

THREADS = 6
START_LIMIT = 10  # Increased from 3 to 10 to allow more profiles to start simultaneously
REQUEST_TIMEOUT = 60

GPM_API = "http://127.0.0.1:19995"
GROUP_NAME = "All"
BROWSER_CORE = 1
BROWSER_NAME = 1

SCREEN_W = 1920
SCREEN_H = 1080
TASKBAR_H = 30
ROWS = 3
COLS = 4

START_WIN_SCALE = None
START_WIN_SIZE = "468,350"

FULL_SCREEN = False

def _safe_reconfigure_stdout_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def _cleanup_old_logs(log_dir: str, max_days: int, prefix: str | None = None):
    if max_days is None or max_days <= 0:
        return

    now = time.time()
    cutoff = now - (max_days * 86400)

    try:
        for filename in os.listdir(log_dir):
            if prefix and not filename.startswith(prefix):
                continue

            file_path = os.path.join(log_dir, filename)
            try:
                if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
                    os.remove(file_path)
            except Exception:
                pass
    except FileNotFoundError:
        pass

def setup_logger(
    module_name: str,
    log_dir: str = "./logs",
    max_bytes: int = 1 * 1024 * 1024,
    backup_count: int = 20,
    max_age_days: int = 3,
    console: bool = True,
) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    _safe_reconfigure_stdout_utf8()

    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    file_path = os.path.join(log_dir, f"{module_name}.log")
    file_handler = RotatingFileHandler(
        file_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _cleanup_old_logs(log_dir, max_age_days, prefix=f"{module_name}.log")

    logger.propagate = False
    return logger