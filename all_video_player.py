import json
import sys
from video_player import play

if len(sys.argv) < 2:
    print("Usage: python all_video_player.py <playlists.json>")
    sys.exit(1)

with open(sys.argv[1]) as f:
    items = json.load(f)

for item in items:
    playlist = item["playlist"]
    play(url=playlist["url"], max_videos=playlist["max_num_video"], topic=playlist["topic"])
