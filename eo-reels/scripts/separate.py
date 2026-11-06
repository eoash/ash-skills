"""Separate the voice from the BGM for a source range and record it in audio/manifest.json.
usage: separate.py <project-dir> <a> <b>
Ranges are padded by 3 s. Run once per stretch of the interview the script draws on."""
import json, os, sys
import numpy as np, soundfile as sf, torch
from demucs.apply import apply_model
from demucs.pretrained import get_model
from common import load_manifest, manifest_path, run_ff

project, a, b = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
a = max(a - 3, 0); b += 3
rel = f"audio/{a:.0f}-{b:.0f}"; d = f"{project}/{rel}"; os.makedirs(d, exist_ok=True)
run_ff("-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", f"{project}/source.mp4", "-vn", "-ac", "2", "-ar", "44100", f"{d}/clip.wav")
model = get_model("htdemucs_ft"); model.eval()
wav, sr = sf.read(f"{d}/clip.wav", dtype="float32")
assert sr == model.samplerate, sr
x = torch.from_numpy(wav.T.copy())
ref = x.mean(0); x = (x - ref.mean()) / ref.std()
dev = "mps" if torch.backends.mps.is_available() else "cpu"
with torch.no_grad():
    stems = apply_model(model, x[None], device=dev, shifts=1, split=True, overlap=0.25, progress=False)[0]
stems = stems * ref.std() + ref.mean()
voc = stems[model.sources.index("vocals")].cpu().numpy().T
sf.write(f"{d}/vocals.wav", voc, sr)
os.remove(f"{d}/clip.wav")
end = a + len(voc) / sr
items = [m for m in load_manifest(project) if m["path"] != f"{rel}/vocals.wav"] + [dict(path=f"{rel}/vocals.wav", start=a, end=end)]
json.dump(items, open(manifest_path(project), "w", encoding="utf8"), indent=1)
print(f"voice {a:.2f}-{end:.2f} -> {rel}/vocals.wav, rms {20 * np.log10(np.sqrt((voc ** 2).mean()) + 1e-9):.1f} dB")
