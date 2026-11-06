"""Paths and small helpers shared by the eo-reels scripts."""
import json, os, re, subprocess

HOME = os.environ.get("EO_REELS_HOME", os.path.expanduser("~/.eo-reels"))
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = f"{SKILL}/assets"
FF = f"{HOME}/bin/ffmpeg"
FPS = 30


def run_ff(*args, capture=False):
    return subprocess.run([FF, "-nostdin", "-v", "error", "-y", *args], check=True, capture_output=capture)


def read_mono16k(path, start=None, dur=None, pad=0.0):
    """Decode audio to a 16 kHz mono float array."""
    import numpy as np
    cmd = []
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", path, "-ac", "1", "-ar", "16000"]
    if pad:
        cmd += ["-af", f"apad=pad_dur={pad}"]
    raw = run_ff(*cmd, "-f", "s16le", "-", capture=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def probe(path):
    """Width, height, fps and duration, read from ffmpeg's banner (imageio-ffmpeg ships no ffprobe)."""
    err = subprocess.run([FF, "-nostdin", "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", err)
    fps = re.search(r"([\d.]+) fps", err)
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return dict(
        width=int(size.group(1)) if size else None, height=int(size.group(2)) if size else None,
        fps=float(fps.group(1)) if fps else None,
        duration=int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else None)


def manifest_path(project):
    return f"{project}/audio/manifest.json"


def load_manifest(project):
    p = manifest_path(project)
    return json.load(open(p, encoding="utf8")) if os.path.exists(p) else []


def find_vocals(project, a, b):
    """The separated-voice file covering source range a..b, as (path, its start time), or None."""
    for m in load_manifest(project):
        if m["start"] <= a and b <= m["end"]:
            return os.path.join(project, m["path"]), m["start"]
    return None


def mmss(t):
    t = int(t)
    return f"{t // 60:02d}:{t % 60:02d}"
