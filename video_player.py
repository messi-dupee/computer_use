import json
import subprocess
import time
import threading
import urllib.request
import pyautogui
import websocket
from record_screen_audio_sync import start_recording

# ========================
# CONFIG
# ========================
url = "https://www.youtube.com/watch?v=MgwHN9wFTZs&list=PLVxBmyedTVhTRQRYeZJfVBpz_12zwHc6Z&index=1"

# ========================
# STEP 1: Launch Firefox kiosk with remote debugging
# ========================
subprocess.Popen([
    "google-chrome",
    "--kiosk",
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    "--user-data-dir=/tmp/chrome-kiosk",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-infobars",
    "--autoplay-policy=no-user-gesture-required",
    url
])
time.sleep(5)
pyautogui.click()
pyautogui.press('f')

# ========================
# STEP 2: Keep session alive (anti "still watching")
# ========================
def keep_alive():
    while True:
        time.sleep(30)
        pyautogui.press('shift')

threading.Thread(target=keep_alive, daemon=True).start()

# ========================
# STEP 3: Detect video transitions via CDP video currentTime
# ========================
def get_cdp_ws_url():
    with urllib.request.urlopen("http://localhost:9222/json/list", timeout=2) as resp:
        tabs = json.loads(resp.read())
    for tab in tabs:
        if "youtube.com" in tab.get("url", ""):
            return tab["webSocketDebuggerUrl"]
    return None

def cdp_eval(ws, expression, msg_id):
    ws.send(json.dumps({
        "id": msg_id,
        "method": "Runtime.evaluate",
        "params": {"expression": expression}
    }))
    return json.loads(ws.recv()).get("result", {}).get("result", {}).get("value")

recording_proc = start_recording("output_1.mp4")
print("[Video 1] Recording started: output_1.mp4")

def detect_video_transition():
    global recording_proc

    ws_url = None
    while not ws_url:
        try:
            ws_url = get_cdp_ws_url()
            print(f"[CDP] Connected to: {ws_url}")
        except Exception as e:
            print(f"[CDP] Waiting for browser... ({e})")
            time.sleep(1)

    ws = websocket.create_connection(ws_url)
    msg_id = 1
    prev_time = 0
    video_count = 1

    while True:
        time.sleep(0.1)
        try:
            current_time = cdp_eval(ws, "document.querySelector('video')?.currentTime", msg_id)
            msg_id += 1
        except Exception as e:
            print(f"[CDP] Error: {e}")
            continue

        if current_time is None:
            continue

        # Transition: time was > 5s then dropped back to < 2s
        if prev_time > 5 and current_time < 2:
            video_count += 1
            filename = f"output_{video_count}.mp4"
            old_proc = recording_proc
            recording_proc = start_recording(filename)
            threading.Thread(target=lambda p: (p.terminate(), p.wait()), args=(old_proc,), daemon=True).start()
            print(f"[Video {video_count}] Transition at t={current_time:.2f}s (was {prev_time:.2f}s)")
            print(f"[Video {video_count}] Recording started: {filename}")

        prev_time = current_time

threading.Thread(target=detect_video_transition, daemon=True).start()

# ========================
# KEEP SCRIPT RUNNING
# ========================
input("Running... Press ENTER to quit\n")
