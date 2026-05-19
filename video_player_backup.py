import subprocess
import time
import threading
import pyautogui

# ========================
# CONFIG
# ========================
url = f"https://www.youtube.com/watch?v=MgwHN9wFTZs&list=PLVxBmyedTVhTRQRYeZJfVBpz_12zwHc6Z&index=1"

# ========================
# STEP 1: Launch Firefox kiosk
# ========================
subprocess.Popen([
    "firefox",
    "--kiosk",
    url
])
time.sleep(5)

# Press "f" for YouTube fullscreen
pyautogui.press('f')

# ========================
# STEP 2: Keep session alive (anti "still watching")
# ========================
def keep_alive():
    while True:
        pyautogui.moveRel(1, 0, duration=0.1)
        pyautogui.moveRel(-1, 0, duration=0.1)
        time.sleep(5)  # simulate activity every 5s

threading.Thread(target=keep_alive, daemon=True).start()

# ========================
# STEP 3: Detect video transitions via window title
# ========================
def get_window_title():
    try:
        win_id = subprocess.check_output(["xdotool", "search", "--name", "Mozilla Firefox"], text=True).strip().splitlines()[0]
        return subprocess.check_output(["xdotool", "getwindowname", win_id], text=True).strip()
    except subprocess.CalledProcessError:
        return ""

def detect_video_transition():
    current_title = get_window_title()
    video_count = 1
    print(f"[Video 1] Now playing: {current_title}")
    while True:
        time.sleep(3)
        new_title = get_window_title()
        if new_title and new_title != current_title:
            video_count += 1
            print(f"[Video {video_count}] Transitioned to: {new_title}")
            current_title = new_title

threading.Thread(target=detect_video_transition, daemon=True).start()

# ========================
# KEEP SCRIPT RUNNING
# ========================
input("Running... Press ENTER to quit\n")