from gui.app import run_gui

def main():
    try:
        run_gui()
    except Exception as e:
        print(f"❌ Failed to launch GUI: {e}")

if __name__ == "__main__":
    main()