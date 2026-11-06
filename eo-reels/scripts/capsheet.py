"""Sheet of the source video's burned-in captions, to check spelling and names.
usage: capsheet.py <source.mp4> <a> <b> <step-seconds> <out.jpg>"""
import io, subprocess, sys
from PIL import Image, ImageDraw
from common import FF

src, a, b, step, out = sys.argv[1], *map(float, sys.argv[2:5]), sys.argv[5]
ts, t = [], a
while t < b:
    ts.append(t); t += step
rows = []
for t in ts:
    raw = subprocess.run([FF, "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", "-vf",
                          "crop=1440:190:240:890,scale=720:-1", "-f", "image2pipe", "-c:v", "png", "-"], capture_output=True).stdout
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    ImageDraw.Draw(im).text((4, 4), f"{t:.1f}", fill=(255, 255, 0))
    rows.append(im)
h = rows[0].height
sheet = Image.new("RGB", (1440, h * ((len(rows) + 1) // 2)))
for i, im in enumerate(rows):
    sheet.paste(im, ((i % 2) * 720, (i // 2) * h))
sheet.save(out, quality=85)
