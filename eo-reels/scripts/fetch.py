"""Download an interview and its Korean subtitles into a project folder.
usage: fetch.py <youtube-url> <project-dir>
Writes source.mp4, meta.json, cues.json and cues.txt (one numbered subtitle cue per line)."""
import glob, html, json, os, re, subprocess, sys
from common import FF, HOME, mmss

url, project = sys.argv[1:3]
os.makedirs(project, exist_ok=True)
YT = [f"{HOME}/venv/bin/yt-dlp", "--no-config", "--ffmpeg-location", FF]
CLIENTS = [None, "android", "tv", "mweb", "web_safari", "ios"]  # some clients get blocked from time to time


def ytdlp(*args, client=None):
    extra = ["--extractor-args", f"youtube:player_client={client}"] if client else []
    return subprocess.run([*YT, *extra, *args, url], capture_output=True, text=True)


meta = None
for client in CLIENTS:
    r = ytdlp("-J", "--skip-download", client=client)
    if r.returncode == 0 and r.stdout.strip():
        meta = json.loads(r.stdout)
        break
if not meta:
    sys.exit("Could not read the video page:\n" + r.stderr[-800:])
keep = {k: meta.get(k) for k in ("id", "title", "channel", "uploader", "duration", "description", "chapters", "webpage_url")}
keep["manual_subs"], keep["auto_subs"] = sorted(meta.get("subtitles") or {}), sorted(meta.get("automatic_captions") or {})
json.dump(keep, open(f"{project}/meta.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("title:", keep["title"]); print("channel:", keep["channel"]); print("duration:", mmss(keep["duration"] or 0))

src = f"{project}/source.mp4"
if not os.path.exists(src):
    for client in CLIENTS:
        r = ytdlp("-f", "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080][ext=mp4]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]",
                  "--merge-output-format", "mp4", "-o", src, client=client)
        if r.returncode == 0 and os.path.exists(src):
            break
    else:
        sys.exit("Could not download the video:\n" + r.stderr[-800:])
print("source:", src)

# subtitles: a person's track first, YouTube's automatic one if that is all there is
def vtt_cues(path):
    """Read a VTT line by line, because YouTube's automatic tracks put whitespace-only lines inside a cue."""
    cues, cur, last = [], None, ""
    for raw in open(path, encoding="utf8"):
        m = re.match(r"\s*(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)", raw)
        if m:
            s = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]); e = int(m[4]) * 3600 + int(m[5]) * 60 + float(m[6])
            cur = dict(s=round(s, 2), e=round(e, 2), lines=[])
            cues.append(cur)
        elif cur is not None:
            line = html.unescape(re.sub(r"<[^>]+>", "", raw))
            line = re.sub(r"\[[^\]]*\]", "", line).strip()  # [음악] and the like
            if line and line != last and line not in cur["lines"]:  # automatic tracks repeat each line as it scrolls
                cur["lines"].append(line); last = line
    return [dict(s=c["s"], e=c["e"], t=" ".join(c["lines"])) for c in cues if c["lines"]]


manual = "ko" in keep["manual_subs"] or any(k.startswith("ko") for k in keep["manual_subs"])
kind = None
for client in CLIENTS:
    args = ["--skip-download", "--sub-format", "vtt/best", "--sub-langs", "ko.*,ko", "-o", f"{project}/subs.%(ext)s"]
    r = ytdlp(*args, "--write-subs", *([] if manual else ["--write-auto-subs"]), client=client)
    found = sorted(glob.glob(f"{project}/subs*.vtt"))
    if found:
        kind = "manual" if manual else "automatic"
        break
if kind:
    orig = [f for f in found if ".ko.vtt" in f or ".ko-orig.vtt" in f]
    cues = vtt_cues((orig or found)[0])
    for i, c in enumerate(cues):
        c["id"] = i
    json.dump(cues, open(f"{project}/cues.json", "w", encoding="utf8"), ensure_ascii=False, indent=0)
    with open(f"{project}/cues.txt", "w", encoding="utf8") as f:
        for c in cues:
            f.write(f'{c["id"]} [{mmss(c["s"])}] {c["t"]}\n')
    print(f"subtitles: {kind}, {len(cues)} cues -> cues.txt")
    if kind == "automatic":
        print("Automatic track only. Run: asr.py full <project-dir>")
else:
    print("subtitles: NONE. Run: asr.py full <project-dir>")
