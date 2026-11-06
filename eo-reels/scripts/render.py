"""Render one EO reel from a config file. See references/render-config.md for the format.
usage: render.py <config.json> --check             validate only
       render.py <config.json> --preview out.jpg   fast silent render, then a sheet with one frame per shot
       render.py <config.json> out.mp4             final render
Audio pieces and picture entries are independent, so a cutaway can run across an audio splice and no
splice shows as a jump inside one shot. All times in the config are source seconds."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont
from common import ASSETS, FF, FPS as F, load_manifest, probe, run_ff
from svgmark import render as render_mark

W, H = 1080, 1920
VID_Y, VH, CAP_Y, LOGO_Y, LOGO_H, HEAD_Y = 400, 900, 1340, 1720, 72, 170
HEAD_SIZE, CAP_SIZE, CAP_MAX_W = 84, 62, 960
EPS = 2 / F  # stay this far inside a shot, so a neighbouring shot's frame never leaks in
TEXT = (252, 251, 245)
FONTS = f"{ASSETS}/fonts"
BAND, LOGO_BOX = [1344, 653, 288, 162], [1660, 30, 240, 120]  # defaults for the current EO interview format

cfg_path = sys.argv[1]; mode = sys.argv[2]
cfg_path = os.path.abspath(cfg_path); project = os.path.dirname(cfg_path)
c = json.load(open(cfg_path, encoding="utf8"))
slug = os.path.splitext(os.path.basename(cfg_path))[0]
work = f"{project}/build/{slug}"; os.makedirs(work, exist_ok=True)
SRC = os.path.join(project, c.get("source", "source.mp4"))
band = c.get("band_crop", BAND); logo_box = c.get("logo_box", LOGO_BOX)

# timeline
pieces = c["pieces"]
frames = [round((b - a) * F) for a, b in pieces]
off = [sum(frames[:i]) for i in range(len(frames))]
total = sum(frames)
to_f = lambda p, t: off[p] + round((t - pieces[p][0]) * F)
def to_src(fr):
    for i, (a, _) in enumerate(pieces):
        if off[i] <= fr < off[i] + frames[i]:
            return a + (fr - off[i]) / F
    raise ValueError(fr)

# checks: errors stop the render, warnings are for Claude to judge and report
errors, warnings = [], []
cap_font = ImageFont.truetype(f"{FONTS}/Pretendard-Bold.otf", CAP_SIZE)
measure = ImageDraw.Draw(Image.new("RGB", (8, 8)))
secs = total / F
if secs > 40:
    warnings.append(f"length {secs:.1f}s is over the 40s limit")
elif secs > 30:
    warnings.append(f"length {secs:.1f}s is over the 30s target")
for i, (a, b) in enumerate(pieces):
    if b <= a:
        errors.append(f"piece {i} is empty: {a}-{b}")
for i, cap in enumerate(c["caps"]):
    p, s, e = cap["p"], cap["s"], cap["e"]
    if e <= s or s < pieces[p][0] - 0.01 or e > pieces[p][1] + 0.01:
        errors.append(f'caption {i} "{cap["t"]}" {s}-{e} is outside piece {p} {pieces[p]}')
    lines = cap["t"].split("\n")
    if len(lines) > 2:
        warnings.append(f'caption {i} has {len(lines)} lines: "{cap["t"]}"')
    for line in lines:
        if measure.textlength(line, font=cap_font) > CAP_MAX_W:
            errors.append(f'caption {i} line is too wide for the frame: "{line}"')
    if cap.get("who", "main") not in ("main", "host"):
        errors.append(f'caption {i}: who must be main or host')
    if i and (p, s) < (c["caps"][i - 1]["p"], c["caps"][i - 1]["s"]):
        errors.append(f'caption {i} is out of order')
if len(c["headline"]) > 2:
    warnings.append("headline has more than two lines")

# picture edit list
edl, cur = [], 0
for i, pic in enumerate(c["pics"]):
    end = total if pic.get("until") is None else to_f(*pic["until"])
    if end <= cur:
        errors.append(f"pic {i} ends at frame {end}, not after frame {cur}"); continue
    n = end - cur
    start, (sa, sb) = pic.get("start"), pic["shot"]
    s0 = to_src(cur) if start is None else start
    vs, ve = max(s0, sa + EPS), min(s0 + n / F, sb - EPS)
    if ve <= vs:
        errors.append(f"pic {i} shows nothing: source {s0:.2f} is outside its shot {sa}-{sb}"); continue
    lead, nv = round((vs - s0) * F), max(round((ve - vs) * F), 1)
    if n - nv > 6:  # the shot-edge margin alone accounts for a few held frames
        warnings.append(f"pic {i} holds a frozen frame for {(n - nv) / F:.2f}s: shot {sa}-{sb} is shorter than the {n / F:.2f}s it must fill")
    if start is None and any(cur < o < end for o in off):
        warnings.append(f"pic {i} runs in sync across an audio splice, so the lips drift; use a cutaway with its own start")
    edl.append(dict(start=cur, end=end, src=round(s0, 2), vs=vs, nv=nv, lead=lead, pic=pic))
    cur = end
if cur != total and not errors:
    errors.append(f"pictures end at frame {cur}, audio at frame {total}: make the last pic's until null")
for prev, nxt in zip(edl, edl[1:]):
    same_shot = prev["pic"]["shot"] == nxt["pic"]["shot"]
    continuous = abs(prev["src"] + (prev["end"] - prev["start"]) / F - nxt["src"]) < 2 / F
    if same_shot and not continuous and prev["pic"].get("x") == nxt["pic"].get("x"):
        warnings.append(f"jump cut at {nxt['start'] / F:.2f}s: the same shot and framing continue from a different moment")

for w in warnings:
    print("WARNING:", w)
if errors:
    print("\n".join("ERROR: " + e for e in errors)); sys.exit(1)
print("length", round(secs, 2), "cuts at", [round(e["start"] / F, 2) for e in edl[1:]], "splices at", [round(o / F, 2) for o in off[1:]])
if mode == "--check":
    sys.exit(0)

# still layer: headline and logo on black
img = Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(img)
logo = render_mark(f"{ASSETS}/eo-mark-white.svg", LOGO_H, TEXT); img.paste(logo, ((W - logo.width) // 2, LOGO_Y), logo)
hs = HEAD_SIZE; hf = ImageFont.truetype(f"{FONTS}/Pretendard-Black.otf", hs)
while max(d.textlength(l, font=hf) for l in c["headline"]) > W - 120:
    hs -= 2; hf = ImageFont.truetype(f"{FONTS}/Pretendard-Black.otf", hs)
y = HEAD_Y
for l in c["headline"]:
    d.text(((W - d.textlength(l, font=hf)) / 2, y), l, font=hf, fill=TEXT); y += int(hs * 1.25)
fp = f"{work}/frame.png"; img.save(fp)

# captions
def ts(t):
    t = int(max(t, 0) * 100 + 1e-6) / 100  # floor to the ASS grid, so a caption never starts a frame after its cut
    h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h)}:{int(m):02d}:{s:05.2f}"
merged = []
for cap in c["caps"]:
    x = [to_f(cap["p"], cap["s"]) / F, to_f(cap["p"], cap["e"]) / F, cap["t"], cap.get("who", "main")]
    if merged and merged[-1][2:] == x[2:]:  # the same line split by a splice shows as one caption
        merged[-1][1] = x[1]
    else:
        merged.append(x)
cut_frames = [e["start"] for e in edl[1:]]
for x in merged:  # a caption that changes just before or after a cut changes on the cut
    near = min(cut_frames, key=lambda c: abs(c - x[0] * F), default=None)
    if near is not None and abs(near - x[0] * F) <= 4:
        x[0] = near / F
for i, x in enumerate(merged):
    if i + 1 < len(merged) and merged[i + 1][0] - x[1] < 0.6:  # no caption flicker across a short pause
        x[1] = merged[i + 1][0]
style = lambda name, colour: (f"Style: {name},Pretendard,{CAP_SIZE},{colour},{colour},&H50000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,8,60,60,{CAP_Y},1\n")
ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style("main", "&H00F5FBFC")}{style("host", "&H003AEEF9")}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
for s, e, t, who in merged:
    ass += f"Dialogue: 0,{ts(s)},{ts(e)},{who},,0,0,0,,{{\\blur3}}{t.replace(chr(10), chr(92) + 'N')}\n"
ap = f"{work}/caps.ass"; open(ap, "w", encoding="utf8").write(ass)
json.dump(dict(total=total, edl=[[e["start"], e["end"], e["src"], e["pic"]["x"]] for e in edl], caps=[x[:3] for x in merged], splices=off[1:]),
          open(f"{work}/timeline.json", "w", encoding="utf8"), ensure_ascii=False)

# audio sources: one input per separated range
preview = mode == "--preview"
sources = []
if not preview:
    manifest = c.get("audio") or load_manifest(project)
    for i, (a, b) in enumerate(pieces):
        hit = next((m for m in manifest if m["start"] <= a and b <= m["end"]), None)
        if not hit:
            sys.exit(f"ERROR: no separated voice covers piece {i} {a}-{b}. Run: separate.py {project} {a} {b}")
        if hit not in sources:
            sources.append(hit)
inputs = ["-loop", "1", "-framerate", str(F), "-t", f"{total / F:.3f}", "-i", fp]
for m in sources:
    inputs += ["-i", os.path.join(project, m["path"])]
first_pic = 1 + len(sources)

# picture chains
need_scale = (probe(SRC)["width"], probe(SRC)["height"]) != (1920, 1080)
vf = ""
for i, e in enumerate(edl):
    n = e["end"] - e["start"]; pic = e["pic"]; cx = pic["x"]
    inputs += ["-ss", f'{e["vs"]:.4f}', "-t", f'{e["nv"] / F + 0.5:.3f}', "-i", SRC]
    chain = (f'[{i + first_pic}:v]fps={F},trim=end_frame={e["nv"]},setpts=PTS-STARTPTS,tpad=start={e["lead"]}:start_mode=clone:'
             f'stop={n - e["nv"] - e["lead"] + 1}:stop_mode=clone,trim=end_frame={n},setpts=N/{F}/TB,')
    if need_scale:
        chain += "scale=1920:1080,"
    if cx == "band":
        bw, bh, bx, by = band
        sh = round(bh * W / bw / 2) * 2
        chain += f"crop={bw}:{bh}:{bx}:{by},scale={W}:{sh}:flags=lanczos,pad={W}:{VH}:0:{(VH - sh) // 2}:black,setsar=1[p{i}];"
    else:
        h = pic.get("h", VH)
        w = round(h * W / VH / 2) * 2
        x = min(max(round(cx - w / 2), 0), 1920 - w)
        if logo_box:
            chain += "delogo=x={}:y={}:w={}:h={},".format(*logo_box)
        chain += f"crop={w}:{h}:{x}:0,scale={W}:{VH}:flags=lanczos,setsar=1[p{i}];"
    vf += chain
fc = vf + "".join(f"[p{i}]" for i in range(len(edl))) + f"concat=n={len(edl)}:v=1:a=0[cat];"

# audio chain
if not preview:
    uses = [sum(1 for (a, b) in pieces if m["start"] <= a and b <= m["end"] and next(s for s in sources if s["start"] <= a and b <= s["end"]) is m) for m in sources]
    labels = {}
    for si, m in enumerate(sources):
        fc += f"[{si + 1}:a]asplit={uses[si]}" + "".join(f"[s{si}_{k}]" for k in range(uses[si])) + ";"
        labels[si] = 0
    for i, ((a, b), k) in enumerate(zip(pieces, frames)):
        si = next(j for j, s in enumerate(sources) if s["start"] <= a and b <= s["end"])
        a0 = a - sources[si]["start"]
        fc += (f"[s{si}_{labels[si]}]atrim=start={a0:.4f}:end={a0 + k / F:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.008,"
               f"afade=t=out:st={k / F - 0.008:.4f}:d=0.008[a{i}];")
        labels[si] += 1
    N = len(frames)
    fc += "".join(f"[a{i}]" for i in range(N)) + f"concat=n={N}:v=0:a=1,afade=t=out:st={total / F - 0.02:.3f}:d=0.02,loudnorm=I=-14:TP=-1.5:LRA=11[a];"
esc = lambda p: p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
fc += f"[0:v][cat]overlay=0:{VID_Y}[b];[b]subtitles='{esc(ap)}':fontsdir='{esc(FONTS)}',format=yuv420p[v]"

if preview:
    tmp = f"{work}/preview.mp4"
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-r", str(F),
                    "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-t", f"{total / F:.3f}", tmp], check=True)
    # one frame from the middle of each shot
    mids = [(e["start"] + e["end"]) // 2 for e in edl]
    sel = "+".join(f"eq(n\\,{m})" for m in mids)
    cols = min(len(mids), 6); rows = (len(mids) + cols - 1) // cols
    run_ff("-i", tmp, "-vf", f"select='{sel}',scale=360:-1,tile={cols}x{rows}", "-frames:v", "1", "-fps_mode", "vfr", "-q:v", "3", sys.argv[3])
    stills = f"{work}/stills"; os.makedirs(stills, exist_ok=True)
    run_ff("-i", tmp, "-vf", f"select='{sel}'", "-fps_mode", "vfr", "-q:v", "2", f"{stills}/shot-%02d.jpg")
    print("preview", sys.argv[3], "full-size frames in", stills)
else:
    out = mode
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    subprocess.run([FF, "-nostdin", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                    "-r", str(F), "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-profile:v", "high",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total / F:.3f}", "-movflags", "+faststart", out], check=True)
    print("wrote", out)
