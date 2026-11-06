"""Check a rendered reel against its config.
usage: qa.py <config.json> <out.mp4> [sheet.jpg]
Finds picture changes that should not be there, compares what Whisper hears with each caption, lists every
splice for a person to listen to, and writes a sheet of the frames around each cut."""
import difflib, json, os, re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from common import FF, FPS as F, probe, read_mono16k

cfg_path, out = os.path.abspath(sys.argv[1]), sys.argv[2]
project = os.path.dirname(cfg_path); slug = os.path.splitext(os.path.basename(cfg_path))[0]
tl = json.load(open(f"{project}/build/{slug}/timeline.json", encoding="utf8"))
sheet = sys.argv[3] if len(sys.argv) > 3 else f"{project}/build/{slug}/qa.jpg"
total, problems = tl["total"], []

info = probe(out)
print(f'file: {info["width"]}x{info["height"]} {info["fps"]} fps {info["duration"]:.2f}s, expected {total / F:.2f}s')
if (info["width"], info["height"]) != (1080, 1920):
    problems.append("frame size is not 1080x1920")

# picture: compare only the video box, so captions changing don't count as cuts
SW, SH = 216, 180
raw = subprocess.run([FF, "-nostdin", "-v", "error", "-i", out, "-vf", f"crop=1080:900:0:400,scale={SW}:{SH}", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, SH, SW).astype(np.int16)
if len(fr) != total:
    problems.append(f"{len(fr)} frames, expected {total}")
diff = np.abs(fr[1:] - fr[:-1]).mean((1, 2))
ANGLE, JUMP = 20, 4  # mean grey-level change between two frames
peaks = []
for i, v in enumerate(diff):
    near = np.concatenate([diff[max(i - 6, 0):i], diff[i + 1:i + 7]])
    if v >= JUMP and len(near) and v > 5 * np.median(near) and v == diff[max(i - 2, 0):i + 3].max():
        peaks.append(i + 1)
cuts = {s for s, *_ in tl["edl"][1:]}
look = []
for p in peaks:
    if p in cuts:
        continue
    x = next(e[3] for e in tl["edl"] if e[0] <= p < e[1])
    if x == "band":  # a B-roll inset is a montage, so cuts inside it are the source's own
        print(f"  note: B-roll cut at {p / F:.2f}s")
    else:
        look.append(p)
for a, b in zip(peaks, peaks[1:]):
    if b - a <= 3:
        problems.append(f"blip: picture changes at frames {a} and {b}, {b - a} frame(s) apart")
small = [c for c in sorted(cuts) if 0 < c <= len(diff) and diff[c - 1] < ANGLE]
print("planned cuts:", len(cuts), "| detected changes:", len(peaks))
print("picture changes inside a shot, so look at the frames (a jump cut in the source, or a large gesture):", ", ".join(f"{p / F:.2f}s (frame {p})" for p in look) or "none")
print("planned cuts with a small picture change, so check them for a jump inside one angle:", ", ".join(f"{c / F:.2f}s" for c in small) or "none")

# sheet: two frames either side of each cut, plus the last frames
col = sorted({max(min(f, len(fr) - 1), 0) for c in [*cuts, *look] for f in (c - 2, c - 1, c, c + 1)} | {len(fr) - 2, len(fr) - 1})
W, H = 216, 384
big = subprocess.run([FF, "-nostdin", "-v", "error", "-i", out, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
bf = np.frombuffer(big, np.uint8).reshape(-1, H, W, 3)
cols = 12; rows = (len(col) + cols - 1) // cols
im = Image.new("RGB", (cols * W, rows * H))
for i, f in enumerate(col):
    im.paste(Image.fromarray(bf[f]), ((i % cols) * W, (i // cols) * H))
    ImageDraw.Draw(im).text(((i % cols) * W + 3, (i // cols) * H + 3), str(f), fill=(255, 255, 0))
im.save(sheet, quality=80)
print("sheet:", sheet)

# captions against what is heard
from faster_whisper import WhisperModel
au = read_mono16k(out)
segs, _ = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4).transcribe(
    au, language="ko", word_timestamps=True, vad_filter=False, beam_size=5, condition_on_previous_text=False)
words = [w for s in segs for w in s.words]
norm = lambda t: re.sub(r"[^\w]", "", t)
print("captions vs what Whisper heard:")
for s, e, t in tl["caps"]:
    heard = " ".join(w.word.strip() for w in words if s - 0.05 <= (w.start + w.end) / 2 < e + 0.05)
    score = difflib.SequenceMatcher(None, norm(t), norm(heard)).ratio()
    mark = "same " if score == 1 else "diff " if score >= 0.8 else "CHECK"
    print(f'  {mark} {s:5.1f}s  caption: {t.replace(chr(10), " ")}  |  heard: {heard}')

print("splices for a person to listen to:", ", ".join(f"{o / F:.1f}s" for o in tl["splices"]) or "none")
print("PROBLEMS:" if problems else "No picture problems found.")
for p in problems:
    print(" -", p)
sys.exit(1 if problems else 0)
