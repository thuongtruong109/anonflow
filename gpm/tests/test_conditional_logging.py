"""
Test script để kiểm tra logging logic
Chỉ log khi username != ""
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

        print(f"✅ Log written: {username} -> {log_file}")
    except Exception as e:
        print(f"❌ Error logging: {e}")

def test_like_logging(username: str):
    """Simulate like action với logging conditional"""
    like_success = True

    if like_success:
        # Chỉ log khi có username thực sự
        if username and username != "":
            _log_action("like.log", username, "https://tiktok.com/@user/video/123", "Liked video")
            return True
        else:
            print(f"⚠️  Like successful but NOT logged (username={username})")
            return False

def test_comment_logging(username: str, comment_text: str):
    """Simulate comment action với logging conditional"""
    comment_success = True

    if comment_success:
        # Chỉ log khi có username thực sự
        if username and username != "":
            _log_action("comment.log", username, "https://tiktok.com/@user/video/456", f"Commented: {comment_text}")
            return True
        else:
            print(f"⚠️  Comment successful but NOT logged (username={username})")
            return False

if __name__ == "__main__":
    print("🧪 Testing conditional logging:\n")

    # Test case 1: Username thực sự - SẼ LOG
    print("1. Testing with real username:")
    test_like_logging("[10100 followers] [101 videos] user1")
    test_comment_logging("[10100 followers] [101 videos] user1", "Great video! 👍")
    print()

    # Test case 2: Username = "" - KHÔNG LOG
    print("2. Testing with '' :")
    test_like_logging("")
    test_comment_logging("", "Nice content!")
    print()

    # Test case 3: Username empty - KHÔNG LOG
    print("3. Testing with empty username:")
    test_like_logging("")
    test_comment_logging("", "Awesome!")
    print()

    # Test case 4: Username None - KHÔNG LOG
    print("4. Testing with None username:")
    test_like_logging(None)
    test_comment_logging(None, "Cool!")
    print()

    print("✅ All tests completed! Check logs/ folder for output.")
