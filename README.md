# ADAS TSR - Traffic Sign Recognition

Hệ thống nhận diện biển báo giao thông cho ADAS xe máy tại Việt Nam. Repo này tập trung vào inference thực tế bằng pipeline lai giữa Computer Vision truyền thống và Deep Learning YOLOv8/Ultralytics, kèm bộ tài liệu tuyến tính từ narrative, tiêu chuẩn an toàn, implementation đến presentation.

## 1. Tổng Quan Dự Án

`adas-tsr` là baseline inference-only cho bài toán Traffic Sign Recognition trong bối cảnh đường Việt Nam. Runtime chính nằm ở `code/tsr_demo.py`, sử dụng checkpoint `models/best.pt` từ model `star092304/traffic-sign-detection-vietnam-yolo` và có thể bật thêm nhánh heuristic CV truyền thống bằng `--traditional`.

Repo này hỗ trợ:

- chạy inference trên video file hoặc webcam;
- xuất video overlay phục vụ demo và kiểm thử nhanh;
- phân tích thời gian thực trên CPU, NPU/GPU tùy môi trường triển khai;
- thử nghiệm cấu hình degraded mode cho CPU yếu hoặc video 4K;
- nghiên cứu ODD Việt Nam, SOTIF, ISO 26262-12, HMI, diagnostics và V&V cho TSR.

Repo này không hỗ trợ:

- training model từ đầu;
- lưu dataset nặng trong Git;
- quản lý artifact benchmark lớn hoặc output tạm trong release branch;
- thay thế HMI/CAN production thật của phương tiện.

Cấu trúc rút gọn:

```text
adas-tsr/
├── code/
│   └── tsr_demo.py
├── models/
│   └── best.pt
├── videos/
│   └── README.md
├── research/
│   ├── 0.requirements.md
│   ├── 1.narrative/
│   ├── 2.knowledge_base/
│   └── 3.implementation/
├── docs/
│   └── javascripts/mermaid.js
├── scripts/
│   └── prepare_docs.py
├── environment.yml
├── requirements.txt
├── requirements-docs.txt
├── run_demo.sh
├── mkdocs.yml
└── TROUBLESHOOTING.md
```

Các file quan trọng:

| Path | Vai trò |
|---|---|
| `code/tsr_demo.py` | Runtime inference YOLO/Ultralytics, overlay video, giữ detection ngắn hạn và nhánh CV heuristic. |
| `models/best.pt` | Checkpoint baseline cho 82 lớp biển báo giao thông Việt Nam. |
| `videos/` | Input/output video local; không bắt buộc version video mẫu. |
| `run_demo.sh` | Script tiện ích tạo môi trường và chạy inference headless. |
| `research/` | Tài liệu tuyến tính: narrative, knowledge base, implementation và notebook. |
| `mkdocs.yml` | Cấu hình publish tài liệu bằng MkDocs Material. |

## 2. Cài Đặt Và Chuẩn Bị Nhanh

Yêu cầu tối thiểu:

- Linux hoặc WSL khuyến nghị;
- Python `3.11`;
- RAM `>= 4 GB`;
- GPU/NPU là tùy chọn, CPU vẫn chạy được với cấu hình giảm tải.

### Option A: Conda

```bash
cd adas-tsr
conda env create -f environment.yml
conda activate adas-tsr
```

### Option B: Python venv

```bash
cd adas-tsr
python3.11 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### Option C: Auto Script

```bash
cd adas-tsr
chmod +x run_demo.sh
./run_demo.sh /absolute/or/relative/path/to/input.mp4
```

Nếu `.venv` chưa tồn tại, `run_demo.sh` sẽ tạo môi trường Python `3.11`, cài PyTorch CPU và cài các dependency trong `requirements.txt`.

### Model weights

Runtime mặc định tìm checkpoint tại:

```text
models/best.pt
```

Nếu file thiếu, `code/tsr_demo.py` và `run_demo.sh` có thể tải tự động từ Hugging Face. Có thể tải thủ công bằng:

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

### Video input

Không cần commit video mẫu vào Git. Các lựa chọn thực tế:

| Cách dùng | Lệnh |
|---|---|
| Dùng video road/dashcam riêng | `mkdir -p videos && cp /path/to/your/dashcam_or_road_video.mp4 videos/input.mp4` |
| Tải MP4 smoke test để kiểm tra pipeline | `mkdir -p videos && curl -L https://download.samplelib.com/mp4/sample-5s.mp4 -o videos/smoke_test.mp4` |
| Tải demo video Google Drive bằng `gdown` | `gdown --fuzzy "https://drive.google.com/file/d/1jvMYLCpHR8tJc-bLMggJFDf55-uaAcx_/view?usp=drive_link" -O videos/drive_demo_video.mp4` |
| Dùng video public khác | `mkdir -p videos && cp /path/to/front_camera_video.mp4 videos/traffic_sign_test.mp4` |

Để đánh giá TSR có ý nghĩa, nên dùng footage front-facing có biển báo rõ, ánh sáng ổn định và độ phân giải tối thiểu `720p`. Xem thêm [videos/README.md](videos/README.md).

## 3. Vận Hành Và CLI

Các ví dụ dưới đây giả định bạn đang ở repo root và đã kích hoạt môi trường.

### Chạy headless trên video

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output.mp4
```

### Chạy webcam thời gian thực

```bash
.venv/bin/python code/tsr_demo.py --source 0
```

### Tăng recall bằng ngưỡng confidence thấp hơn

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output_low_conf.mp4 \
  --conf 0.10
```

### Tối ưu CPU yếu cho video 4K

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input_4k.mp4 \
  --output videos/output_4k.mp4 \
  --imgsz 512 \
  --max-width 1280 \
  --skip 1
```

### Chạy pipeline lai YOLO và CV truyền thống

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output_hybrid.mp4 \
  --traditional
```

Tham số CLI:

| Tham số | Mặc định | Ý nghĩa |
|---|---:|---|
| `--source` | `videos/traffic_sign_test.mp4` | Đường dẫn video input hoặc camera index như `0`. |
| `--output` | `videos/tsr_demo_output.mp4` | Đường dẫn video đã annotate. |
| `--weights` | `models/best.pt` | File model weights `.pt`. |
| `--conf` | `0.15` | Ngưỡng confidence cho YOLO. |
| `--imgsz` | `640` | Kích thước ảnh inference YOLO. |
| `--max-width` | `1280` | Resize frame nếu frame rộng hơn giá trị này. |
| `--skip` | `0` | Bỏ qua `N` frame giữa các lần inference. |
| `--hold` | `3` | Giữ detection cũ `N` frame khi frame hiện tại không có detection. |
| `--traditional` | `off` | Bật nhánh CV heuristic HSV/contour. |
| `--no-display` | `off` | Chạy headless, không mở cửa sổ GUI. |

Cấu hình runtime khuyến nghị:

| Tình huống | Cấu hình |
|---|---|
| Debug ảnh hoặc video ngắn | `--imgsz 640 --skip 0` |
| Replay lab `720p` | `--imgsz 640 --max-width 1280` |
| Replay `4K` trên CPU | `--imgsz 512 --max-width 1280 --skip 1` |
| Ý tưởng degraded fallback | `--imgsz 512 --skip 2`, cân nhắc tắt `--traditional` |

## 4. Điều Hướng Tài Liệu

`README.md` chỉ là cổng vào vận hành repo. Tài liệu nghiên cứu chi tiết nằm trong `research/` và đi theo luồng tuyến tính một chiều: narrative chỉ nêu bối cảnh/gap, knowledge base chuyển gap thành tiêu chuẩn, implementation hiện thực hóa kỹ thuật.

| Nhóm tài liệu | Link |
|---|---|
| Requirements | [0. Requirements](research/0.requirements.md) |
| Narrative | [1.01. Prototype to Production](research/1.narrative/01.prototype_to_production.md) |
| Knowledge Base | [2.00. Knowledge Base Index](research/2.knowledge_base/00.index.md) |
| Automotive Standards | [2.01. Automotive Standards](research/2.knowledge_base/01.automotive_standards.md) |
| Camera Sensor IEEE 2020 | [2.02. Camera Sensor and IEEE 2020](research/2.knowledge_base/02.camera_sensor_ieee2020.md) |
| Safety HAZOP/FTA | [2.03. Safety Analysis HAZOP and FTA](research/2.knowledge_base/03.safety_analysis_hazop_fta.md) |
| Implementation | [3.00. Implementation Index](research/3.implementation/00.index.md) |
| Hybrid Pipeline | [3.01. Hybrid Pipeline Architecture](research/3.implementation/01.hybrid_pipeline_architecture.md) |
| State Manager & HMI | [3.02. State Manager and HMI](research/3.implementation/02.state_manager_and_hmi.md) |
| Edge Deployment | [3.03. Edge Deployment and Benchmarks](research/3.implementation/03.edge_deployment_and_benchmarks.md) |
| Production-Lite Demo | [3.04. Production-Lite Demo Notebook](research/3.implementation/04.production_lite_demo_notebook.md) |
| Troubleshooting | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |

### Publish docs bằng MkDocs

Repo không dùng symlink vật lý trong `docs/` để tránh lỗi clone trên Windows. Trước khi build hoặc serve, chạy script copy Markdown vào thư mục tạm `.mkdocs_docs/`:

```bash
cd adas-tsr
pip install -r requirements-docs.txt
python scripts/prepare_docs.py
mkdocs serve
```

Local preview:

```text
http://127.0.0.1:8000
```

Build static site:

```bash
cd adas-tsr
python scripts/prepare_docs.py
mkdocs build
```

Output sinh ra tại:

```text
site/
```

`site/` là output sinh tự động, có thể xóa và build lại bằng `mkdocs build`.

Triển khai GitHub Pages thủ công:

```bash
cd adas-tsr
python scripts/prepare_docs.py
mkdocs gh-deploy
```

Workflow `.github/workflows/docs.yml` cũng chạy bước `python scripts/prepare_docs.py` trước `mkdocs build --strict`. URL Pages dự kiến:

```text
https://<github-username>.github.io/adas-tsr/
```

Ghi chú quản lý Git:

- dataset training lớn nên nằm ngoài Git;
- input/output video được quản lý local trong `videos/` trừ khi chủ động version;
- release branch chỉ giữ runtime script, tài liệu nghiên cứu và notebook tái lập nhẹ, không giữ artifact benchmark nặng.

Khi gặp lỗi runtime hoặc lỗi môi trường, xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
