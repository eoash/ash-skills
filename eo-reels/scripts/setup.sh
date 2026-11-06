#!/bin/bash
# Installs everything the eo-reels skill needs into one folder. Safe to run again.
# usage: setup.sh          install what is missing, then check
#        setup.sh --check  only check
set -euo pipefail
HOME_DIR="${EO_REELS_HOME:-$HOME/.eo-reels}"
PY="$HOME_DIR/venv/bin/python"

check() {
  local ok=1
  [ -x "$PY" ] || { echo "MISSING python env"; return 1; }
  "$PY" - <<'PY' || ok=0
import importlib.util as u
missing = [m for m in ("yt_dlp", "imageio_ffmpeg", "faster_whisper", "PIL", "numpy", "demucs", "soundfile", "torch") if not u.find_spec(m)]
if missing:
    raise SystemExit("MISSING python packages: " + ", ".join(missing))
PY
  [ -x "$HOME_DIR/bin/ffmpeg" ] || { echo "MISSING ffmpeg"; return 1; }
  local filters; filters="$("$HOME_DIR/bin/ffmpeg" -nostdin -hide_banner -filters 2>/dev/null)"
  for f in subtitles delogo loudnorm; do
    grep -q " $f " <<<"$filters" || { echo "MISSING ffmpeg filter: $f"; ok=0; }
  done
  [ "$ok" = 1 ] && echo "OK: ready in $HOME_DIR"
  [ "$ok" = 1 ]
}

if [ "${1:-}" = "--check" ]; then check; exit $?; fi

if [ "$(uname -s)" != "Darwin" ] || [ "$(sysctl -n hw.optional.arm64 2>/dev/null || echo 0)" != "1" ]; then
  echo "This skill supports Apple Silicon Macs only (voice separation needs a recent PyTorch)." >&2
  exit 1
fi
mkdir -p "$HOME_DIR/bin"

# uv manages Python, so the machine needs no Python of its own
if command -v uv >/dev/null 2>&1; then UV="$(command -v uv)"
else
  [ -x "$HOME_DIR/uv/uv" ] || curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$HOME_DIR/uv" UV_NO_MODIFY_PATH=1 sh
  UV="$HOME_DIR/uv/uv"
fi

# ask for the arm64 build by name: an Intel uv would otherwise pick an Intel Python and run under Rosetta
[ -x "$PY" ] || "$UV" venv -q --python cpython-3.12-macos-aarch64-none "$HOME_DIR/venv"
"$UV" pip install -q --python "$PY" -U \
  yt-dlp imageio-ffmpeg faster-whisper pillow numpy demucs soundfile
ln -sf "$("$PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')" "$HOME_DIR/bin/ffmpeg"

echo "Downloading the speech and voice-separation models (about 2 GB, first run only)..."
"$PY" -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"
"$PY" -c "from demucs.pretrained import get_model; get_model('htdemucs_ft')"
check
