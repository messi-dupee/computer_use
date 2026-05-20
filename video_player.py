import json
import os
import re
import shutil
import subprocess
import time
import threading
import urllib.request
import pyautogui
pyautogui.FAILSAFE = False
import websocket
from record_screen_audio_sync import start_recording


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

def url_to_slug(url):
    url = url[url.find('www'):]
    slug = url.replace('?', 'qmark').replace('=', 'equalto').replace('&', 'ampersand').replace('/', 'slash').replace('.', 'ddott')
    return re.sub(r'[^a-zA-Z0-9_-]', '_', slug).strip('_')


def play(url, max_videos, topic="output"):
    # ========================
    # STEP 0: Create output folder
    # ========================
    if os.path.exists(topic):
        shutil.rmtree(topic)
    os.makedirs(topic)

    # ========================
    # STEP 1: Launch browser
    # ========================
    browser_proc = subprocess.Popen([
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

    # allow some time to load video
    time.sleep(8)
    screen_w, screen_h = pyautogui.size()

    # click the center to ensure video player has focus, then press 'f' for fullscreen
    pyautogui.click(screen_w // 2, screen_h // 2)
    time.sleep(1)
    pyautogui.press('f')
    time.sleep(4)

    # move mouse to top-right corner to hide cursor and controls, then press '0' to reset to the beginning of the video
    pyautogui.moveTo(screen_w - 1, 0)
    time.sleep(1)
    pyautogui.press('0')
    time.sleep(1)
    pyautogui.click(screen_w - 1, 0)

    # ========================
    # STEP 2: Keep session alive (anti "still watching")
    # ========================
    done_event = threading.Event()

    def keep_alive():
        while not done_event.wait(30):
            pyautogui.press('shift')

    threading.Thread(target=keep_alive, daemon=True).start()

    # ========================
    # STEP 3: Detect video transitions via CDP video currentTime
    # ========================
    def detect_video_transition():
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

        # Get URL of first video and start first recording
        video_url = cdp_eval(ws, "location.href", msg_id)
        msg_id += 1
        filename = os.path.join(topic, f"{topic}_1_{url_to_slug(video_url or 'video')}.mp4")
        recording_proc = [start_recording(filename)]
        print(f"[Video 1] {video_url} -> {filename}")

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
                if video_count > max_videos:
                    print(f"[Done] Reached max {max_videos} videos. Shutting down.")
                    recording_proc[0].terminate()
                    recording_proc[0].wait()
                    ws.close()
                    browser_proc.terminate()
                    done_event.set()
                    return

                video_url = cdp_eval(ws, "location.href", msg_id)
                msg_id += 1
                filename = os.path.join(topic, f"{topic}_{video_count}_{url_to_slug(video_url or f'video_{video_count}')}.mp4")
                old_proc = recording_proc[0]
                recording_proc[0] = start_recording(filename)
                threading.Thread(target=lambda p: (p.terminate(), p.wait()), args=(old_proc,), daemon=True).start()
                print(f"[Video {video_count}] Transition at t={current_time:.2f}s (was {prev_time:.2f}s)")
                print(f"[Video {video_count}] {video_url} -> {filename}")

            prev_time = current_time

    threading.Thread(target=detect_video_transition, daemon=True).start()
    done_event.wait()
    print(f"[Done] Playlist finished: {url}")


if __name__ == "__main__":
    play(
        url="https://www.youtube.com/watch?v=MgwHN9wFTZs&list=PLVxBmyedTVhTRQRYeZJfVBpz_12zwHc6Z&index=1",
        max_videos=2,
    )
