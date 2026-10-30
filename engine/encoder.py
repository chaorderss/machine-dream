"""FFmpeg writer on a background thread so GPU rendering and x264 encoding overlap."""
import queue
import subprocess
import threading

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


class FFmpegWriter:
    def __init__(self, path, size, fps, audio=None, t0=0.0, dur=None, crf=16, preset="slow"):
        w, h = size
        cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
        if audio:
            cmd += ["-ss", f"{t0:.4f}", "-t", f"{dur:.4f}", "-i", str(audio), "-map", "0:v", "-map", "1:a",
                    "-c:a", "aac", "-b:a", "320k"]
        # rgb → BT.709 limited range (what YouTube assumes for HD/4K), tagged explicitly
        cmd += ["-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
                "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-profile:v", "high",
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                "-movflags", "+faststart", "-shortest", str(path)]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        self.q = queue.Queue(maxsize=8)
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while True:
            buf = self.q.get()
            if buf is None:
                break
            self.proc.stdin.write(buf)

    def write(self, frame):
        self.q.put(frame)

    def close(self):
        self.q.put(None)
        self.thread.join()
        self.proc.stdin.close()
        return self.proc.wait()
