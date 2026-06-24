#!/usr/bin/env bash
# TSR Demo — chạy inference trên video mẫu
# Usage: ./run_demo.sh [video_input] [video_output]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv/bin/python"
SOURCE="${1:-$ROOT/videos/traffic_sign_test.mp4}"
OUTPUT="${2:-$ROOT/videos/tsr_demo_output.mp4}"

if [[ ! -x "$VENV" ]]; then
  echo "[SETUP] Tạo môi trường .venv (Python 3.11)..."
  conda create -y -p "$ROOT/.venv" python=3.11 pip
  "$ROOT/.venv/bin/pip" install torch torchvision --index-url https://download.pytorch.org/whl/cpu
  "$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"
fi

if [[ ! -f "$ROOT/models/best.pt" ]]; then
  echo "[SETUP] Tải model best.pt từ HuggingFace..."
  "$VENV" -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='star092304/traffic-sign-detection-vietnam-yolo',
    filename='best.pt',
    local_dir='$ROOT/models',
)
"
fi

if [[ ! -f "$SOURCE" && "$SOURCE" != "0" ]]; then
  echo "[ERROR] Input video not found: $SOURCE"
  echo "[HINT] Put a road video under videos/ or pass it as the first argument."
  echo "[HINT] See README.md and videos/README.md for download examples."
  exit 1
fi

echo "[RUN] source=$SOURCE"
echo "[RUN] output=$OUTPUT"

cd "$ROOT/code"
"$VENV" tsr_demo.py --no-display --source "$SOURCE" --output "$OUTPUT"

echo "[DONE] Output: $OUTPUT"
