"""Build the transcript a person reads to pick lines: transcript.json for the work screen.
usage: build_transcript.py <project-dir>
Reads cues.json and meta.json, plus annotate.json (written by Claude):
{"title": "정샘물 인터뷰 대본", "host": "태용",        # host: optional, leave it out when the interviewer is never heard
 "turns": [[0, "정샘물"], [14, "태용"], ...],        # [first cue id, who speaks from there on]
 "sections": [[0, "오프닝"], [40, "어떤 회사인가"], ...],  # [first cue id, heading]
 "fixes": {"12": "고친 문장"},                       # optional: replace a cue's text
 "drop": [3, 4]}                                     # optional: cue ids to leave out"""
import json, os, sys
from common import mmss

project = sys.argv[1]; out = f"{project}/transcript.json"
PARA = 20  # a new paragraph starts at the next sentence end after this many seconds of one speaker...
PARA_MAX = 40  # ...or here regardless, for tracks without punctuation
cues = json.load(open(f"{project}/cues.json", encoding="utf8"))
meta = json.load(open(f"{project}/meta.json", encoding="utf8"))
ann = json.load(open(f"{project}/annotate.json", encoding="utf8"))
turns = sorted(ann["turns"]); sections = sorted(ann["sections"])
fixes = {int(k): v for k, v in ann.get("fixes", {}).items()}; drop = set(ann.get("drop", []))
who_list = list(dict.fromkeys(w for _, w in turns))
host = ann.get("host")
guests = [w for w in who_list if w != host]
cls = {w: f"g{i % 3}" for i, w in enumerate(guests)}
if host:
    cls[host] = "t"


def at(table, cid):
    cur = table[0][1]
    for start, val in table:
        if start > cid:
            break
        cur = val
    return cur


blocks = []  # [section, [ [who, t, [texts]] ]]
for c in cues:
    if c["id"] in drop:
        continue
    sec, who, text = at(sections, c["id"]), at(turns, c["id"]), fixes.get(c["id"], c["t"])
    if not blocks or blocks[-1][0] != sec:
        blocks.append([sec, []])
    rows = blocks[-1][1]
    if rows and rows[-1][0] == who and (c["s"] - rows[-1][1] < PARA or (
            c["s"] - rows[-1][1] < PARA_MAX and not rows[-1][2][-1].rstrip().endswith((".", "?", "!", "요", "다")))):
        rows[-1][2].append(text)
    else:
        rows.append([who, c["s"], [text]])

video = meta.get("webpage_url") or f'https://www.youtube.com/watch?v={meta["id"]}'
doc = dict(title=ann.get("title") or meta["title"], video=video, sections=[])
for sec, rows in blocks:
    doc["sections"].append(dict(title=sec, time=mmss(rows[0][1]), rows=[dict(
        who=who, cls=cls[who], host=who == host, time=mmss(t), text=" ".join(texts),
        link=f'{video}&t={int(t)}s' if "?" in video else f'{video}?t={int(t)}s') for who, t, texts in rows]))
tmp = out + ".tmp"
json.dump(doc, open(tmp, "w", encoding="utf8"), ensure_ascii=False, indent=1)
os.replace(tmp, out)  # the work screen reads this file while it is open
print("wrote", out, f"({sum(len(r) for _, r in blocks)} paragraphs, {len(blocks)} sections)")
