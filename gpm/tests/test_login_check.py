"""
Test script để kiểm tra login check logic
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

        print(f"✅ Log written: {log_file}")
    except Exception as e:
        print(f"❌ Error logging: {e}")

def simulate_check_login(has_login_button: bool, username: str):
    """
    Simulate login check
    Returns: True nếu đã login, False nếu chưa login
    """
    if has_login_button:
        # Tìm thấy login button -> chưa đăng nhập
        print(f"⚠️  Found login button for user: {username}")
        if username and username != "":
            _log_action("login.log", username, "https://www.tiktok.com/foryou", "Login status: false")
        return False
    else:
        # Không tìm thấy login button -> đã đăng nhập
        print(f"✅ User logged in: {username}")
        return True

def simulate_like_action(is_logged_in: bool, username: str):
    """Simulate like action with login check"""
    if is_logged_in:
        print(f"   → Like action EXECUTED for {username}")
        if username and username != "":
            _log_action("like.log", username, "https://tiktok.com/@user/video/123", "Liked video")
    else:
        print(f"   → Like action SKIPPED (not logged in)")

def simulate_comment_action(is_logged_in: bool, username: str):
    """Simulate comment action with login check"""
    if is_logged_in:
        print(f"   → Comment action EXECUTED for {username}")
        if username and username != "":
            _log_action("comment.log", username, "https://tiktok.com/@user/video/456", "Commented: Great!")
    else:
        print(f"   → Comment action SKIPPED (not logged in)")

def simulate_other_actions():
    """Simulate other actions (always execute)"""
    print(f"   → Watch video action EXECUTED (always runs)")
    print(f"   → Scroll action EXECUTED (always runs)")

if __name__ == "__main__":
    print("🧪 Testing login check logic:\n")

    # Test case 1: User đã login
    print("=" * 60)
    print("Test 1: User ĐÃ LOGIN (không tìm thấy login button)")
    print("=" * 60)
    username = "[10100 followers] user1"
    is_logged_in = simulate_check_login(has_login_button=False, username=username)
    simulate_like_action(is_logged_in, username)
    simulate_comment_action(is_logged_in, username)
    simulate_other_actions()
    print()

    # Test case 2: User CHƯA login
    print("=" * 60)
    print("Test 2: User CHƯA LOGIN (tìm thấy login button)")
    print("=" * 60)
    username = "[11400 followers] user2"
    is_logged_in = simulate_check_login(has_login_button=True, username=username)
    simulate_like_action(is_logged_in, username)
    simulate_comment_action(is_logged_in, username)
    simulate_other_actions()
    print()

    # Test case 3: User CHƯA login với  username
    print("=" * 60)
    print("Test 3: user CHƯA LOGIN")
    print("=" * 60)
    username = ""
    is_logged_in = simulate_check_login(has_login_button=True, username=username)
    simulate_like_action(is_logged_in, username)
    simulate_comment_action(is_logged_in, username)
    simulate_other_actions()
    print()

    print("✅ All tests completed! Check logs/ folder for output files.")
