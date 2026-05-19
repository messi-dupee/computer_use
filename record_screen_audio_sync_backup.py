# this script record screenshot and audio from headphone. 
import subprocess

command = [
    "ffmpeg",

    "-thread_queue_size", "4096", # avoide queue block
    "-f", "x11grab",
    "-framerate", "10", # resonable fps CPU can encode with 4K res
    "-video_size", "3840x2160", # full screen res. Change according to your display
    "-use_wallclock_as_timestamps", "1",
    "-i", ":0",
    "-itsoffset", "0.5", # important: adjust time latency between audio and video
    "-f", "pulse",
    "-i", "alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__hw_sofhdadsp__sink.monitor",
    "-c:v", "libx264",   
    "-preset", "veryfast",
    "-vf", "scale=iw/2:ih/2", # resize the video to half to reduce file size
    "-c:a", "aac",
    "-vsync", "1",
    "-af", "aresample=async=1",

    "output.mp4"
]

subprocess.run(command)