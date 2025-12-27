import os
import json
from concurrent.futures import ThreadPoolExecutor

COOKIE_DIR = "cookies"

def convert_file(filename):
    txt_path = os.path.join(COOKIE_DIR, filename)
    processing_path = txt_path + ".processing"
    json_path = txt_path.replace(".txt", ".json")

    # Nếu đã có json → bỏ qua
    if os.path.exists(json_path):
        return

    try:
        # Đánh dấu đang xử lý (atomic)
        os.rename(txt_path, processing_path)

        cookies = []

        with open(processing_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue

                parts = line.strip().split("\t")
                if len(parts) != 7:
                    continue

                domain, flag, path, secure, expiry, name, value = parts

                cookies.append({
                    "domain": domain,
                    "path": path,
                    "secure": secure.upper() == "TRUE",
                    "httpOnly": False,
                    "name": name,
                    "value": value,
                    "expirationDate": int(expiry)
                })

        if not cookies:
            raise ValueError("Không có cookie hợp lệ")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

        # Xóa file đang xử lý sau khi thành công
        os.remove(processing_path)
        print(f"✅ {filename} → {os.path.basename(json_path)}")

    except Exception as e:
        print(f"❌ Lỗi {filename}: {e}")

        # rollback nếu lỗi
        if os.path.exists(processing_path):
            os.rename(processing_path, txt_path)

def main():
    files = [
        f for f in os.listdir(COOKIE_DIR)
        if f.endswith(".txt")
    ]

    if not files:
        print("⚠️ Không có file cần convert")
        return

    workers = min(8, len(files))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        executor.map(convert_file, files)

    print("🎉 Done")

if __name__ == "__main__":
    main()
