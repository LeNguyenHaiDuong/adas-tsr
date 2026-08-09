# Troubleshooting - ADAS TSR

Tài liệu này gom các lỗi vận hành thường gặp khi chạy `adas-tsr`. README chỉ giữ hướng dẫn nhanh; khi lỗi runtime, kiểm tra bảng dưới đây trước.

| Lỗi | Dấu hiệu | Cách xử lý |
|---|---|---|
| `Bus error` hoặc lỗi import PyTorch/OpenCV/Ultralytics | Python crash ngay khi import hoặc khi load model. | Dùng Python `3.11`, rebuild `.venv`, cài PyTorch CPU rõ ràng rồi cài lại dependency. |
| Không phát hiện được biển báo | Video chạy nhưng `Signs: 0`, output không có bbox. | Giảm `--conf` xuống `0.10`, tăng `--imgsz` lên `640` hoặc cao hơn nếu máy đủ mạnh, dùng video có biển báo rõ hơn. |
| Video 4K xử lý quá chậm | FPS thấp, máy nóng, output lâu hoặc có cảm giác treo. | Dùng `--imgsz 512 --max-width 1280 --skip 1`; nếu vẫn chậm, tăng `--skip 2`. |
| Thiếu model `best.pt` | Báo không tìm thấy `models/best.pt` hoặc tải Hugging Face thất bại. | Tải thủ công bằng `huggingface_hub` và đặt file đúng tại `models/best.pt`. |
| GUI không mở trên WSL/headless server | `cv2.imshow` lỗi hoặc không có cửa sổ hiển thị. | Thêm `--no-display` và xem file output trong `videos/`. |

## Rebuild môi trường khi gặp `Bus error` hoặc lỗi import

```bash
cd adas-tsr
rm -rf .venv
python3.11 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Nếu bạn dùng Conda:

```bash
cd adas-tsr
conda env remove -n adas-tsr
conda env create -f environment.yml
conda activate adas-tsr
```

## Tải model thủ công

```bash
cd adas-tsr
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

## Lệnh kiểm tra nhanh

Headless:

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output.mp4
```

CPU yếu hoặc video 4K:

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input_4k.mp4 \
  --output videos/output_4k.mp4 \
  --imgsz 512 \
  --max-width 1280 \
  --skip 1
```

Nhánh lai YOLO và CV truyền thống:

```bash
.venv/bin/python code/tsr_demo.py \
  --no-display \
  --source videos/input.mp4 \
  --output videos/output_hybrid.mp4 \
  --traditional
```
