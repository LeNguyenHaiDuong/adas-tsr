#!/usr/bin/env python3
"""
Model Export & Edge Optimization Tool for ADAS TSR
===================================================
Hỗ trợ chuyển đổi model Ultralytics YOLO (.pt) sang các định dạng Edge Engine tối ưu:
- ONNX (CPU / DirectML / ONNX Runtime)
- TensorRT (.engine) cho NVIDIA GPU / Jetson Edge ECU
- Tùy chọn lượng tử hóa FP16 / Half precision
- Tùy chọn Dynamic shape hoặc Fixed batch/size

Cách sử dụng:
    # Export sang ONNX (FP32)
    python scripts/export_model.py --weights models/best.pt --format onnx

    # Export sang ONNX (FP16 / Half)
    python scripts/export_model.py --weights models/best.pt --format onnx --half

    # Export sang TensorRT (nếu có NVIDIA GPU)
    python scripts/export_model.py --weights models/best.pt --format engine --half

    # Benchmark so sánh hiệu năng giữa PyTorch và model vừa xuất
    python scripts/export_model.py --weights models/best.pt --format onnx --benchmark
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEIGHTS = ROOT / "models" / "best.pt"


def export_model(
    weights_path: Path,
    target_format: str = "onnx",
    imgsz: int = 640,
    half: bool = False,
    dynamic: bool = False,
    opset: int = 17,
) -> Path:
    """Chuyển đổi model Ultralytics YOLO sang format mong muốn."""
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] Cần cài đặt ultralytics: pip install ultralytics")
        sys.exit(1)

    if not weights_path.is_file():
        print(f"[ERROR] Không tìm thấy file trọng số: {weights_path}")
        sys.exit(1)

    print(f"[INFO] Bắt đầu tải model: {weights_path}")
    model = YOLO(str(weights_path))

    print(f"[INFO] Bắt đầu export sang định dạng '{target_format}'...")
    print(f"       imgsz={imgsz} | half={half} | dynamic={dynamic} | opset={opset}")

    t0 = time.time()
    export_args = {
        "format": target_format,
        "imgsz": imgsz,
        "half": half,
        "dynamic": dynamic,
    }
    if target_format == "onnx":
        export_args["opset"] = opset

    exported_path_str = model.export(**export_args)
    export_time = time.time() - t0

    exported_path = Path(exported_path_str)
    print(f"[SUCCESS] Export hoàn tất trong {export_time:.2f}s!")
    print(f"[OUTPUT] File xuất: {exported_path}")
    if exported_path.is_file():
        file_size_mb = exported_path.stat().st_size / (1024 * 1024)
        print(f"[INFO] Kích thước file: {file_size_mb:.2f} MB")

    return exported_path


def benchmark_comparison(pt_path: Path, exported_path: Path, imgsz: int = 640, warmup: int = 10, iterations: int = 50):
    """Benchmark so sánh độ trễ (latency) và FPS giữa PyTorch và Model đã xuất."""
    from ultralytics import YOLO

    dummy_image = np.random.randint(0, 255, (imgsz, imgsz, 3), dtype=np.uint8)

    print("\n" + "=" * 60)
    print(" BENCHMARK HIỆU NĂNG: PYTORCH (.PT) VS EXPORTED MODEL")
    print("=" * 60)

    # 1. Đo PyTorch Model
    print(f"\n[1] Đang đo PyTorch model: {pt_path.name}...")
    model_pt = YOLO(str(pt_path))
    for _ in range(warmup):
        _ = model_pt(dummy_image, imgsz=imgsz, verbose=False)

    times_pt = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = model_pt(dummy_image, imgsz=imgsz, verbose=False)
        times_pt.append((time.perf_counter() - t0) * 1000)

    avg_pt = np.mean(times_pt)
    std_pt = np.std(times_pt)
    fps_pt = 1000.0 / avg_pt

    # 2. Đo Exported Model
    print(f"[2] Đang đo Exported model: {exported_path.name}...")
    model_exp = YOLO(str(exported_path), task="detect")
    for _ in range(warmup):
        _ = model_exp(dummy_image, imgsz=imgsz, verbose=False)

    times_exp = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        _ = model_exp(dummy_image, imgsz=imgsz, verbose=False)
        times_exp.append((time.perf_counter() - t0) * 1000)

    avg_exp = np.mean(times_exp)
    std_exp = np.std(times_exp)
    fps_exp = 1000.0 / avg_exp

    speedup = avg_pt / avg_exp if avg_exp > 0 else 1.0

    print("\n" + "-" * 60)
    print(f"KẾT QUẢ SO SÁNH (imgsz={imgsz}, iterations={iterations}):")
    print(f"  * PyTorch (.pt):     {avg_pt:6.2f} ms ± {std_pt:4.2f} ms  (~{fps_pt:5.1f} FPS)")
    print(f"  * Exported ({exported_path.suffix}): {avg_exp:6.2f} ms ± {std_exp:4.2f} ms  (~{fps_exp:5.1f} FPS)")
    print(f"  * Tăng tốc (Speedup): {speedup:.2f}x")
    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="TSR Model Exporter (ONNX / TensorRT)")
    parser.add_argument("--weights", type=str, default=str(DEFAULT_WEIGHTS), help="File .pt nguồn")
    parser.add_argument("--format", type=str, default="onnx", choices=["onnx", "engine", "openvino"], help="Format đích")
    parser.add_argument("--imgsz", type=int, default=640, help="Kích thước inference (640, 512, ...)")
    parser.add_argument("--half", action="store_true", help="Bật lượng tử hóa FP16 / Half precision")
    parser.add_argument("--dynamic", action="store_true", help="Kích hoạt dynamic batch và resolution")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset version")
    parser.add_argument("--benchmark", action="store_true", help="Chạy benchmark so sánh sau khi xuất")
    args = parser.parse_args()

    weights_path = Path(args.weights)
    exported_path = export_model(
        weights_path=weights_path,
        target_format=args.format,
        imgsz=args.imgsz,
        half=args.half,
        dynamic=args.dynamic,
        opset=args.opset,
    )

    if args.benchmark:
        benchmark_comparison(weights_path, exported_path, imgsz=args.imgsz)


if __name__ == "__main__":
    main()
