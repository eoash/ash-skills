"""Shot list and contact sheet of a source range, to choose shots and crops.
usage: shots.py <source.mp4> <a> <b> <out.jpg>
Ask for a few seconds more than you need: shots are cut off at the ends of the range.
Prints each boundary as ANGLE (a new camera angle) or JUMP? (a small picture change: often the source's own
jump cut inside one angle, sometimes just a gesture, so look at the tiles). Each tile is a source frame at 1/4
scale with a yellow line every 192 source pixels, so x can be read off."""
import subprocess, sys
import numpy as np
from common import FF, probe

src, a, b, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
ANGLE, JUMP = 20, 3.5  # mean grey-level change between two frames
fps = probe(src)["fps"]
# the top 860 px only, so the source's burned-in captions don't count as picture changes
raw = subprocess.run([FF, "-nostdin", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", src, "-vf",
                      "crop=1920:860:0:0,scale=192:86", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, 86, 192).astype(np.int16)
d = np.abs(fr[1:] - fr[:-1]).mean((1, 2))
marks = []
for i, v in enumerate(d):
    near = np.concatenate([d[max(i - 6, 0):i], d[i + 1:i + 7]])
    if v >= ANGLE and v == d[max(i - 2, 0):i + 3].max():
        marks.append((round(a + (i + 1) / fps, 2), "ANGLE", v))
    elif v >= JUMP and len(near) and v > 5 * np.median(near) and v == d[max(i - 2, 0):i + 3].max():
        marks.append((round(a + (i + 1) / fps, 2), "JUMP?", v))
cuts = [a] + [m[0] for m in marks] + [b]
shots = list(zip(cuts, cuts[1:]))
print("shots:", [(round(s, 2), round(e, 2)) for s, e in shots])
print("boundaries:", " ".join(f"{t}:{kind}" for t, kind, _ in marks))
times = []
for s, e in shots:
    times += [s + 0.15, (s + e) / 2, e - 0.15] if e - s > 1.2 else [(s + e) / 2]
print("tiles, left to right:", [round(t, 2) for t in times])
inputs, fc = [], ""
for i, t in enumerate(times):
    inputs += ["-ss", f"{t:.3f}", "-i", src]
    fc += (f"[{i}:v]trim=end_frame=1,crop=1920:900:0:0,scale=480:-1,"
           + ",".join(f"drawbox=x={x * 48}:y=0:w=1:h=225:color=yellow@0.6" for x in range(1, 10))
           + f"[f{i}];")
n, cols = len(times), 3
if n > 1:
    fc += "".join(f"[f{i}]" for i in range(n)) + f"xstack=inputs={n}:layout=" + "|".join(
        f"{(i % cols) * 480}_{(i // cols) * 225}" for i in range(n)) + ":fill=black[o]"
else:
    fc += "[f0]null[o]"
subprocess.run([FF, "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[o]",
                "-frames:v", "1", out], check=True)
