"""Whisper helpers. Times printed are source seconds.
usage:
  asr.py full <project-dir>        transcribe the whole source when it has no subtitles (writes cues.json, cues.txt)
  asr.py words <project-dir> a b   words with times and the quiet gaps between them, to choose cut points
  asr.py check <config.json>       hear each audio piece on its own, next to the captions written for it"""
import json, os, sys
import numpy as np
from faster_whisper import WhisperModel
from common import find_vocals, mmss, read_mono16k


def model():
    return WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8)


def source_audio(project, a, b):
    """Separated voice where it exists, otherwise the original soundtrack."""
    found = find_vocals(project, a, b)
    if found:
        return read_mono16k(found[0], a - found[1], b - a), "voice"
    return read_mono16k(f"{project}/source.mp4", a, b - a), "original soundtrack"


mode = sys.argv[1]
if mode == "full":
    project = sys.argv[2]
    segs, _ = model().transcribe(read_mono16k(f"{project}/source.mp4"), language="ko", vad_filter=True, beam_size=5)
    cues = [dict(id=i, s=round(s.start, 2), e=round(s.end, 2), t=s.text.strip()) for i, s in enumerate(segs)]
    json.dump(cues, open(f"{project}/cues.json", "w", encoding="utf8"), ensure_ascii=False, indent=0)
    with open(f"{project}/cues.txt", "w", encoding="utf8") as f:
        for c in cues:
            f.write(f'{c["id"]} [{mmss(c["s"])}] {c["t"]}\n')
    print(len(cues), "cues -> cues.txt")
elif mode == "words":
    project, a, b = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
    au, what = source_audio(project, a, b)
    print(f"# listening to the {what}")
    segs, _ = model().transcribe(au, language="ko", word_timestamps=True, vad_filter=False, beam_size=5, condition_on_previous_text=False)
    for s in segs:
        print(f"[{a + s.start:.2f}-{a + s.end:.2f}] {s.text.strip()}")
        print("   " + " ".join(f"{w.word.strip()}({a + w.start:.2f}-{a + w.end:.2f})" for w in s.words))
    n = len(au) // 160
    db = 20 * np.log10(np.sqrt((au[:n * 160].reshape(n, 160) ** 2).mean(1)) + 1e-6)  # 10 ms windows
    quiet = db < max(-45, np.percentile(db, 90) - 30)
    gaps, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if j - i >= 3:
                gaps.append((a + i / 100, a + j / 100))
            i = j
        else:
            i += 1
    print("quiet gaps (cut inside one):", " ".join(f"{s:.2f}-{e:.2f}" for s, e in gaps))
elif mode == "check":
    cfg_path = sys.argv[2]; project = os.path.dirname(os.path.abspath(cfg_path)); cfg = json.load(open(cfg_path, encoding="utf8"))
    m = model()
    for i, (a, b) in enumerate(cfg["pieces"]):
        found = find_vocals(project, a, b)
        path, base = found if found else (f"{project}/source.mp4", 0)
        au = read_mono16k(path, a - base, b - a, pad=0.4)
        segs, _ = m.transcribe(au, language="ko", vad_filter=False, beam_size=5, condition_on_previous_text=False)
        print(f"piece {i} {a}-{b}\n  heard:   {' '.join(s.text.strip() for s in segs)}")
        print("  caption: " + " / ".join(c["t"].replace(chr(10), " ") for c in cfg["caps"] if c["p"] == i))
else:
    sys.exit(__doc__)
