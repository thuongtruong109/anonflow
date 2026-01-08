import subprocess

subprocess.Popen(
    [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    creationflags=subprocess.CREATE_NO_WINDOW,
    close_fds=True
)
