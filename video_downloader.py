from yt_dlp import YoutubeDL

URLS = ['https://www.youtube.com/watch?v=V1hJES_VeDU']
with YoutubeDL() as ydl:
    ydl.download(URLS)