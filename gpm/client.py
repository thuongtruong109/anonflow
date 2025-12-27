import threading, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import GPM_API, REQUEST_TIMEOUT

def build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(pool_connections=50, pool_maxsize=50, max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

thread_local = threading.local()

def get_session() -> requests.Session:
    if not hasattr(thread_local, "session"):
        thread_local.session = build_session()
    return thread_local.session

def api_get(path: str, params=None):
    r = get_session().get(f"{GPM_API}{path}", params=params or {}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()

def api_post(path: str, payload):
    r = get_session().post(f"{GPM_API}{path}", json=payload, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()
