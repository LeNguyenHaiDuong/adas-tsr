# TSR — Traffic Sign Recognition for ADAS

Inference-only baseline for Vietnam traffic sign detection using `Ultralytics YOLO` and the model `star092304/traffic-sign-detection-vietnam-yolo`.

This repository is intentionally kept small and deployment-oriented:

- main runtime script: `code/tsr_demo.py`
- report-style research documents: `research/`
- model weights: `models/best.pt`
- local input/output videos: `videos/`

> **Editorial scope:** `README.md` là entrypoint vận hành repo: setup, chạy demo, input/output video và publish docs. Narrative hệ thống TSR, gap production và các deep-dive nghiên cứu nằm trong `research/`.

## 1. What this repo is for

This repo is for:

- running TSR inference on a video file or webcam;
- evaluating the current baseline model on local videos;
- reading the system-level research/design notes for a real automotive TSR feature.

This repo is not for:

- training a new model from scratch;
- storing large datasets in Git;
- keeping temporary benchmark artifacts or heavy generated research outputs in the release branch.

## 2. Repository layout

| Path | Purpose |
|---|---|
| `code/tsr_demo.py` | Main inference script. |
| `models/best.pt` | Baseline model weights for 82 Vietnam traffic sign classes. |
| `research/` | Report-style research and system-design documents. |
| `research/notebooks/` | Lightweight reproducibility notebook for local replay and analysis. |
| `videos/` | Local input and output videos. This folder is user-managed; sample/output videos are not required to be versioned. |
| `run_demo.sh` | Convenience script to set up the environment and run inference. |
| `requirements.txt` | Python package requirements beyond the base PyTorch install. |
| `environment.yml` | Optional Conda environment definition for a CPU setup. |

## 3. Prerequisites

- Linux or WSL recommended
- Python `3.11`
- RAM `>= 4 GB`
- optional NVIDIA GPU for faster runtime

## 4. Environment setup

### Option A — Conda

```bash
cd adas-tsr
conda env create -f environment.yml
conda activate adas-tsr
```

### Option B — Python venv

```bash
cd adas-tsr
python3.11 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Option C — Use the convenience script

```bash
cd adas-tsr
chmod +x run_demo.sh
./run_demo.sh /absolute/or/relative/path/to/input.mp4
```

If `.venv` does not exist, `run_demo.sh` will create it automatically and install the required packages.

## 5. Model download

The repo expects the baseline model at:

```text
models/best.pt
```

If the file is missing, `tsr_demo.py` and `run_demo.sh` can download it from Hugging Face automatically.  
You can also download it manually:

```bash
.venv/bin/python - <<'PY'
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id="star092304/traffic-sign-detection-vietnam-yolo",
    filename="best.pt",
    local_dir="models",
)
print("Downloaded models/best.pt")
PY
```

## 6. Video input setup

No input sample video is required to be committed in Git.  
You have three practical options:

### Option A — Use your own road or dashcam video

```bash
mkdir -p videos
cp /path/to/your/dashcam_or_road_video.mp4 videos/input.mp4
```

### Option B — Download a generic MP4 for smoke testing

This is useful only to verify the pipeline runs end-to-end. It is **not** a meaningful TSR evaluation video.

```bash
mkdir -p videos
curl -L https://download.samplelib.com/mp4/sample-5s.mp4 -o videos/smoke_test.mp4
```

### Option C — Download the shared demo video from Google Drive

Shared demo video:

- https://drive.google.com/file/d/1jvMYLCpHR8tJc-bLMggJFDf55-uaAcx_/view?usp=drive_link

If you use `gdown`:

```bash
mkdir -p videos
gdown --fuzzy "https://drive.google.com/file/d/1jvMYLCpHR8tJc-bLMggJFDf55-uaAcx_/view?usp=drive_link" -O videos/drive_demo_video.mp4
```

### Option D — Download a public road video manually

Use any front-facing driving video and place it under `videos/`, for example:

```bash
mkdir -p videos
cp /path/to/front_camera_video.mp4 videos/traffic_sign_test.mp4
```

For meaningful TSR evaluation, prefer:

- front-facing driving footage;
- visible road signs;
- daylight or stable night lighting;
- resolution `>= 720p`.

See also [videos/README.md](videos/README.md).

## 7. Run commands

All examples below assume you are at the repo root and have already activated the environment.

### Headless inference on a video

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output.mp4
```

### Webcam inference

```bash
.venv/bin/python code/tsr_demo.py --source 0
```

### Lower confidence threshold for more recall

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output_low_conf.mp4 \
  --conf 0.10
```

### CPU-safer 4K processing

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input_4k.mp4 \
  --output videos/output_4k.mp4 \
  --imgsz 512 \
  --max-width 1280 \
  --skip 1
```

### Enable the heuristic branch

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output_hybrid.mp4 \
  --traditional
```

## 8. CLI parameters

| Parameter | Default | Description |
|---|---|---|
| `--source` | `videos/traffic_sign_test.mp4` | Input video path or webcam index such as `0`. |
| `--output` | `videos/tsr_demo_output.mp4` | Annotated output video path. |
| `--weights` | `models/best.pt` | Model weights file. |
| `--conf` | `0.15` | Confidence threshold. |
| `--imgsz` | `640` | YOLO inference image size. |
| `--max-width` | `1280` | Resize frame if wider than this value. |
| `--skip` | `0` | Skip `N` frames between inference calls. |
| `--hold` | `3` | Hold previous detections when the current frame is empty. |
| `--traditional` | `off` | Enable the heuristic CV branch. |
| `--no-display` | `off` | Run without opening a GUI window. |

## 9. Runtime guidance under low-memory CPU setups

| Use case | Recommended configuration |
|---|---|
| image or short video debug | `imgsz=640`, `skip=0` |
| 720p lab replay | `imgsz=640`, `max-width=1280` |
| 4K replay on CPU | `imgsz=512`, `max-width=1280`, `skip=1` |
| degraded fallback idea | `imgsz=512`, `skip=2`, optionally disable `--traditional` |

## 10. Research documents

`README.md` không kể lại toàn bộ câu chuyện production. Thứ tự đọc khuyến nghị trong `research/` là:

| Order | Document | Focus |
|---|---|---|
| **0** | [research/0.requirements.md](research/0.requirements.md) | Brief và yêu cầu gốc của bài tập |
| **1** | [research/1.research_tsr_three_part_unified.md](research/1.research_tsr_three_part_unified.md) | Narrative chính: problem framing, production mindset, gap baseline, roadmap |
| **2** | [research/2.research_tsr_baseline_analysis.md](research/2.research_tsr_baseline_analysis.md) | Annex gắn repo: `tsr_demo.py`, `best.pt`, runtime, gap implementation |
| **3** | [research/3.research_tsr_detection_architecture_research.md](research/3.research_tsr_detection_architecture_research.md) | Deep-dive detector: anchor, neck, NMS, small-object, dataset, edge deploy |
| **4** | [research/4.research_tsr_colab_production_lite_demo.md](research/4.research_tsr_colab_production_lite_demo.md) | Production-lite Colab notebook: stateful replay, JSONL, quality/ODD gate |
| **5** | [research/diagram.md](research/diagram.md) | Visual appendix và glossary ngắn cho architecture blocks |
| **6** | [research/slide.md](research/slide.md) | Slide deck dẫn xuất cho thuyết trình, không phải source-of-truth |
| **7** | [research/sources.md](research/sources.md) | References và provenance |
| — | [research/assets/diagrams/tsr_production_ecu_architecture.html](research/assets/diagrams/tsr_production_ecu_architecture.html) | Interactive ECU architecture diagram (Part II) |

## 11. Publish docs with MkDocs + GitHub Pages

This repo is set up so the existing Markdown can be published as a documentation website with `MkDocs Material`.

### Docs source layout

- `docs/index.md` is a symlink to `README.md`
- `docs/research/` is a symlink to `research/`
- `docs/code/tsr_demo.py` is a symlink to `code/tsr_demo.py`
- `docs/videos/README.md` is a symlink to `videos/README.md`
- `mkdocs.yml` defines the navigation, theme, and Mermaid rendering

Edit the original files as usual under `README.md`, `research/`, `code/`, and `videos/`. The docs site will reuse them directly.

### Install docs dependencies

```bash
cd adas-tsr
pip install -r requirements-docs.txt
```

### Serve locally

```bash
cd adas-tsr
mkdocs serve
```

Local preview:

```text
http://127.0.0.1:8000
```

### Build static site

```bash
cd adas-tsr
mkdocs build
```

Generated output goes to:

```text
site/
```

### Deploy to GitHub Pages

Manual deployment:

```bash
cd adas-tsr
mkdocs gh-deploy
```

This repo also includes `.github/workflows/docs.yml` so pushes to `main` or `master` can publish the docs automatically via GitHub Pages Actions.

Expected Pages URL pattern:

```text
https://<github-username>.github.io/adas-tsr/
```

## 12. Troubleshooting

| Issue | What to check |
|---|---|
| `Bus error` or import failures | Use Python `3.11`, rebuild `.venv`, install CPU PyTorch explicitly. |
| No detections | Lower `--conf`, increase `--imgsz`, use a clearer road-sign video. |
| 4K video too slow | Use `--imgsz 512`, `--max-width 1280`, `--skip 1` or `--skip 2`. |
| Missing model file | Download `models/best.pt` manually or let the script fetch it. |
| GUI does not open in WSL | Use `--no-display` and inspect the output video file instead. |

## 13. Notes for Git and large files

- large training datasets should stay outside Git;
- input/output videos are managed locally unless you explicitly choose to version them;
- the release branch keeps the runtime script, report documents, and a lightweight reproducibility notebook, but not heavy generated benchmark artifacts.
