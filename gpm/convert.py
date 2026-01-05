import os, json
from concurrent.futures import ThreadPoolExecutor
from utils import safe_print
from config import COOKIES_DIR

ENCODINGS_TO_TRY = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]

def read_lines_with_fallback(path):
    for enc in ENCODINGS_TO_TRY:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.readlines(), enc
        except UnicodeDecodeError:
            pass
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.readlines(), "utf-8(ignore)"

def convert_file(filename):
    txt_path = os.path.join(COOKIES_DIR, filename)
    processing_path = txt_path + ".processing"
    json_path = txt_path[:-4] + ".json"

    if os.path.exists(json_path):
        return

    try:
        os.rename(txt_path, processing_path)
        lines, used_enc = read_lines_with_fallback(processing_path)

        cookies = []
        bad = 0

        for line in lines:
            if not line.strip():
                continue
            if line.startswith("#") and not line.startswith("#HttpOnly_"):
                continue

            raw = line.strip()
            if raw.startswith("#HttpOnly_"):
                raw = raw[len("#HttpOnly_"):]

            parts = raw.split("\t")
            if len(parts) != 7:
                bad += 1
                continue

            domain, flag, path, secure, expiry, name, value = parts

            # cookieconverter schema:
            cookies.append({
                "domain": domain,
                "hostOnly": False,
                "path": path,
                "secure": True,
                "expirationDate": str(expiry),
                "name": name,
                "value": value,
                "httpOnly": True   # <-- DÒNG QUYẾT ĐỊNH
            })

        if not cookies:
            raise ValueError(f"Không parse được cookie nào (encoding: {used_enc}, bad_lines: {bad})")

        with open(json_path, "w", encoding="utf-8") as f:
            # cookieconverter cũng thường output 1-line json, nên separators để gọn
            json.dump(cookies, f, ensure_ascii=False, separators=(",", ":"))

        os.remove(processing_path)
        safe_print(f"✅ {filename} → {os.path.basename(json_path)} (read: {used_enc}, cookies: {len(cookies)}, bad_lines: {bad})")

    except Exception as e:
        print(f"❌ Lỗi {filename}: {e}")
        if os.path.exists(processing_path):
            os.rename(processing_path, txt_path)

def convert_cookies_format():
    files = [f for f in os.listdir(COOKIES_DIR) if f.endswith(".txt")]
    if not files:
        print("⚠️ Không có file cần convert")
        return

    workers = min(8, len(files))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(convert_file, files))
if __name__ == "__main__":
    convert_cookies_format()