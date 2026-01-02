"""
Test script để kiểm tra logging functionality
"""
from datetime import datetime
from pathlib import Path

def _log_action(log_file: str, username: str, video_url: str, action_details: str = ""):
    """Ghi log action vào file"""
    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] User: {username} | Video: {video_url}"

        if action_details:
            log_entry += f" | {action_details}"

        log_entry += "\n"

        log_path = log_dir / log_file
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry)

        print(f"✅ Log written to {log_path}")
    except Exception as e:
        print(f"❌ Error logging to {log_file}: {e}")

if __name__ == "__main__":
    # Test like log
    _log_action(
        "like.log",
        "test_user_123",
        "https://www.tiktok.com/@username/video/1234567890",
        "Liked video"
    )

    # Test comment log
    _log_action(
        "comment.log",
        "test_user_456",
        "https://www.tiktok.com/@username/video/9876543210",
        "Commented: Great video! 👍"
    )

    print("\n✅ Test completed! Check logs/ folder for output files.")
