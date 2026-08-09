# HƯỚNG DẪN BỔ SUNG CÁC NỘI DUNG NÂNG CAO CHO HỆ THỐNG TSR

Tài liệu này tập trung **100% vào mã nguồn và nội dung kỹ thuật chuyên sâu** cần cập nhật vào repository `adas-tsr`. Hãy copy trực tiếp các phần dưới đây vào các file tương ứng trong thư mục `research/` và file notebook `.ipynb`.

---

## 📂 1. CẬP NHẬT FILE `research/2.knowledge_base/03.safety_analysis_hazop_fta.md`

### 1.1 Bảng Phân Tích HAZOP Camera Chi Tiết (3 Nodes)

| Phân đoạn hệ thống (Node) | Tham số đo lường (Parameter) | Từ dẫn hướng (Guide Word) | Sai lệch tiêu chuẩn (Deviation) | Nguyên nhân tiềm ẩn (Potential Causes) | Hậu quả an toàn (Safety Consequences) | Biện pháp giảm thiểu rủi ro (Mitigations) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Node 1: Hệ thống quang học & Kính chắn gió** | **Độ truyền quang (Light Transmission)** | **Không / Mất (No/Loss)** | Hình ảnh bị mờ hoàn toàn hoặc bị che khuất | - Mưa lớn bám hạt nước trên kính chắn gió.<br>- Bùn đất, bụi bẩn hoặc sương muối tích tụ.<br>- Đọng hơi sương phía trong mặt kính camera. | YOLOv8 bỏ sót hoàn toàn biển báo (False Negative), hệ thống TSR im lặng khi phương tiện quá tốc độ. | 1. Tích hợp cảm biến mưa kích hoạt gạt mưa tự động.<br>2. Thiết kế module sưởi kính chắn gió tại hốc camera.<br>3. Sử dụng bộ giám sát chất lượng ảnh trực tuyến để báo trạng thái không khả dụng (Unavailable State). |
| **Node 1: Hệ thống quang học & Kính chắn gió** | **Độ sắc nét (Image Sharpness)** | **Giảm / Ít (Less/Low)** | Hình ảnh bị nhòe cục bộ hoặc mất tiêu cự | - Hạt mưa chảy loang trên kính chắn gió gây tán xạ ánh sáng.<br>- Rung động cơ học cường độ cao từ động cơ xe hai bánh. | YOLOv8 định vị sai vùng biên (localization errors) hoặc phân loại nhầm biển báo (False Positive). | 1. Tăng cường giá đỡ chống rung vật lý cho xe hai bánh theo **ISO 26262-12**.<br>2. Chạy tính năng ổn định hình ảnh kỹ thuật số (DIS) trong ISP.<br>3. Sử dụng cơ chế giữ trạng thái (**State Manager --hold 3**) để tránh chớp tắt HMI. |
| **Node 2: Cảm biến CMOS & Bộ ISP** | **Độ phơi sáng (Exposure)** | **Quá nhiều / Cao (More/High)** | Cảm biến bị lóa sáng / Quá phơi sáng | - Camera hướng thẳng về phía mặt trời lúc bình minh/hoàng hôn.<br>- Đèn pha cường độ cao của xe ngược chiều chiếu thẳng ban đêm. | Điểm ảnh vùng biển báo bị bão hòa (cháy sáng), thuật toán mất khả năng trích xuất đặc trưng màu sắc/hình dáng. | 1. Sử dụng cảm biến ảnh automotive hỗ trợ dải tương phản động cao (HDR > 120dB).<br>2. Auto-Exposure (AE) ưu tiên đo sáng vùng 1/3 phía trên khung hình (Upper-Third).<br>3. Nhánh CV truyền thống áp dụng Local Tone Mapping (LTM) để khôi phục chi tiết. |
| **Node 3: Thuật toán nhận diện (YOLO & CV)** | **Tần suất xử lý (Inference Frequency)** | **Giảm / Ít (Less/Low)** | Độ trễ xử lý tăng cao, bỏ sót khung hình | - Nhiệt độ ECU tăng cao gây giảm xung nhịp (thermal throttling).<br>- Luồng dữ liệu video 4K vượt quá băng thông xử lý của CPU/GPU nhúng. | Cảnh báo hiển thị quá muộn khi xe đã đi qua biển báo, không đảm bảo thời gian phản ứng an toàn cho người lái theo chuẩn Euro NCAP SAS. | 1. Chuyển sang cấu hình an toàn suy giảm (CPU-safer degraded mode): giảm kích thước ảnh (`--imgsz 512`), tăng khung hình bỏ qua (`--skip 1` hoặc `--skip 2`).<br>2. Tích hợp bộ quản lý luồng dữ liệu deterministic latency cho nhánh CV truyền thống. |

### 1.2 Sơ Đồ Cây Phân Tích Lỗi (Fault Tree Analysis - FTA)

```
                           [SỰ KIỆN ĐỈNH: TSR không cảnh báo giới hạn tốc độ]
                                                   |
                                            +------+------+
                                            |   CỔNG OR   |
                                            +------+------+
                                                   |
         +-----------------------------------------+-----------------------------------------+
         |                                         |                                         |
[1. Lỗi nhận diện từ Camera]             [2. Lỗi xử lý phần cứng ECU]            [3. Lỗi hiển thị HMI/CAN]
         |                                         |                                         |
     +---+---+                                 +---+---+                                 +---+---+
     | CỔNG  |                                 | CỔNG  |                                 | CỔNG  |
     |  OR   |                                 |  OR   |                                 |  OR   |
     +---+---+                                 +---+---+                                 +---+---+
         |                                         |                                         |
  +------+------+                           +------+------+                           +------+------+
  |             |                           |             |                           |             |
[1.1 Lỗi      [1.2 Lỗi                    [2.1 Quá      [2.2 Lỗi                    [3.1 Lỗi      [3.2 Trễ dòng
Vật lý        Thuật toán                  nhiệt ECU     Bộ nhớ /                    Đường truyền  truyền CAN
Camera]       Nhận diện]                  nhúng]        Crash Luồng]                CAN Bus]      quá ngưỡng]
  |             |                           |             |                           |             |
+-+-+         +-+-+                       (B1)          (B2)                        (B3)          (B4)
|   |         |   |
|   +----+    |   +----+
|        |    |        |
(A1)    (A2) (A3)     (A4)
```

**Các sự kiện cơ bản (Basic Events):**
*   **(A1) - Mưa mờ / Bụi bẩn bám:** Camera bị che khuất hoặc mất nét (SOTIF Performance Limitation).
*   **(A2) - Lóa sáng CMOS:** Điểm ảnh bị cháy sáng do đèn pha ban đêm hoặc mặt trời chiếu trực diện.
*   **(A3) - YOLOv8 bỏ sót:** Không phát hiện được biển báo nhỏ hoặc bị che khuất một phần (SOTIF Functional Insufficiency).
*   **(A4) - Nhánh CV truyền thống báo giả:** Nhận diện nhầm các vật thể tròn màu đỏ khác trong môi trường.
*   **(B1) - Throttling do quá nhiệt:** ECU bị giảm xung nhịp do nhiệt độ cao trên xe máy, gây chậm luồng xử lý.
*   **(B2) - Tràn bộ nhớ (OOM):** Crash luồng OpenCV/PyTorch do rò rỉ RAM khi đọc video thời gian thực.
*   **(B3) - Đứt/Lỏng cáp tín hiệu:** Rung xóc xe hai bánh làm lỏng giắc cắm camera (Vi phạm yêu cầu cơ khí ISO 26262-12).
*   **(B4) - CAN Bus quá tải:** Bản tin cảnh báo TSR bị trễ trên mạng điều khiển trung tâm của xe.

---

## 📂 2. CẬP NHẬT FILE `research/2.knowledge_base/02.camera_sensor_ieee2020.md`

### 2.1 Đặc Tả Phần Cứng Camera & ISP Tuning
*   **Dải tương phản động (HDR):** Bắt buộc cảm biến CMOS đạt tối thiểu **120dB** (khuyến nghị **140dB**) sử dụng phơi sáng đa khung hình hoặc split-diode để triệt tiêu vùng cháy sáng và khôi phục chi tiết biển báo ban đêm.
*   **LED Flicker Mitigation (LFM - Chống nhấp nháy LED):** Biển báo giới hạn tốc độ điện tử LED nhấp nháy ở tần số cao. Cảm biến bắt buộc hỗ trợ công nghệ LFM (kéo dài thời gian phơi sáng của sub-pixel) để tránh hiện tượng sọc ảnh, đứt nét biển báo khi chụp.
*   **Phân vùng đo sáng tự động (AE):** Cấu hình trọng số đo sáng ISP tập trung vào phân khu **Upper-Third (1/3 phía trên khung hình)** để duy trì độ phơi sáng ổn định cho biển báo, không bị đánh lừa bởi mặt đường tối hoặc nắp capo.

### 2.2 Ứng Dụng Bộ 7 Chỉ Số Hiệu Năng IEEE Std 2020™-2024
Tiêu chuẩn **IEEE 2020** cung cấp các phép đo lường khách quan cho camera ADAS thay vì đánh giá cảm tính:
1.  **Flare (Stray Light):** Đo lượng ánh sáng phản xạ không mong muốn qua thấu kính làm mờ ảnh.
2.  **Noise:** Đo mức độ nhiễu hạt trong điều kiện thiếu sáng.
3.  **Dynamic Range:** Xác định dải sáng tối đa/tối thiểu mà camera hoạt động tin cậy thông qua chỉ số **Contrast-to-Noise Ratio (CNR)**.
4.  **Spatial Frequency Response (SFR/MTF):** Đánh giá độ sắc nét thấu kính dưới rung động cơ học.
5.  **Flicker:** Đo chỉ số **MMP (Modulated Light Mitigation Probability)** - xác suất giảm thiểu nhấp nháy LED.
6.  **Contrast Performance:** Đo đạc khả năng tách biệt biển báo khỏi nền thông qua độ tương phản thích ứng (**CTA - Contrast Transfer Accuracy**) và tỷ số tương phản trên nhiễu (**CSNR**).
7.  **Geometric Calibration:** Đánh giá độ méo hình học thấu kính góc rộng.

---

## 📂 3. CẬP NHẬT CELL MÃ NGUỒN CHO FILE NOTEBOOK `.ipynb` HOẶC FILE THƯ VIỆN `code/cta_monitor.py`

*Đoạn mã dưới đây hiện thực hóa thuật toán đo đạc trực tuyến đạt chuẩn IEEE 2020 (Michelson Contrast cho CTA, Foreground/Background Ring cho CSNR, và Normal CDF cho CDP) phục vụ ra quyết định an toàn SOTIF.*

```python
import cv2
import numpy as np
import math

class IEEE2020CTAMonitorV2:
    """
    Bộ giám sát chất lượng ảnh trực tuyến (In-line Quality Monitor) đạt chuẩn IEEE Std 2020-2024.
    Tính toán CTA, CSNR, CDP và Sharpness phục vụ thiết kế an toàn SOTIF (ISO 21448) cho hệ thống TSR.
    """
    def __init__(self, cta_threshold=0.35, csnr_threshold=4.0, sharpness_threshold=50.0):
        self.cta_threshold = cta_threshold          # Ngưỡng tương phản Michelson tối thiểu
        self.csnr_threshold = csnr_threshold        # Ngưỡng Contrast-to-Noise Ratio (CSNR) tối thiểu
        self.sharpness_threshold = sharpness_threshold  # Ngưỡng sắc nét (Laplacian variance) tránh mưa mờ
        
    def _get_luminance(self, bgr_img):
        """Chuyển đổi ảnh sang kênh Y (Luminance) sử dụng trọng số chuẩn ITU-R BT.601"""
        gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        return gray.astype(np.float32)

    def _normal_cdf(self, x):
        """Hàm phân phối tích lũy chuẩn (Normal CDF) viết bằng toán học thuần để chạy nhanh trên CPU nhúng"""
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

    def analyze_roi(self, frame, bbox):
        """
        Phân tích vùng biển báo (ROI Bounding Box) để tính toán chất lượng ảnh cục bộ.
        bbox format: (x1, y1, x2, y2)
        """
        x1, y1, x2, y2 = map(int, bbox)
        h, w, _ = frame.shape
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        if (x2 - x1) < 10 or (y2 - y1) < 10:
            return {
                "status": "INVALID_ROI", 
                "cta": 0.0, 
                "csnr": 0.0, 
                "cdp": 0.0, 
                "sharpness": 0.0,
                "sotif_action": "IGNORE"
            }
            
        roi = frame[y1:y2, x1:x2]
        roi_y = self._get_luminance(roi)
        
        # 1. Tính Contrast Transfer Accuracy (CTA) qua công thức Michelson Contrast
        l_min, l_max, _, _ = cv2.minMaxLoc(roi_y)
        denom = (l_max + l_min)
        michelson_contrast = (l_max - l_min) / denom if denom > 0 else 0.0
        
        # 2. Tính Contrast Signal-to-Noise Ratio (CSNR) bằng phương pháp phân vùng Ring (FG 50% ở trong, BG ở rìa)
        rh, rw = roi_y.shape
        cy, cx = rh // 2, rw // 2
        dy, dx = int(rh * 0.25), int(rw * 0.25)
        
        fg_mask = np.zeros_like(roi_y, dtype=np.uint8)
        cv2.rectangle(fg_mask, (cx - dx, cy - dy), (cx + dx, cy + dy), 255, -1)
        bg_mask = cv2.bitwise_not(fg_mask)
        
        fg_pixels = roi_y[fg_mask == 255]
        bg_pixels = roi_y[bg_mask == 255]
        
        if len(fg_pixels) > 0 and len(bg_pixels) > 0:
            mean_fg = np.mean(fg_pixels)
            mean_bg = np.mean(bg_pixels)
            
            # Ước lượng nhiễu cảm biến tại góc 5x5 phẳng để tránh nhiễu do cạnh sắc chữ số
            corner_block = roi_y[:5, :5]
            std_noise = np.std(corner_block)
            std_noise = max(std_noise, 0.5) # Tránh lỗi chia cho 0
            
            contrast_diff = abs(mean_fg - mean_bg)
            csnr = contrast_diff / std_noise
            
            # 3. Tính Contrast Detection Probability (CDP) - Ngưỡng phân biệt T = 5.0 độ sáng
            T = 5.0
            cdp = self._normal_cdf((contrast_diff - T) / std_noise)
        else:
            csnr, cdp = 0.0, 0.0
            
        # 4. Tính độ sắc nét (Sharpness Proxy) qua phương sai toán tử Laplacian
        sharpness = cv2.Laplacian(roi_y, cv2.CV_32F).var()
        
        # Logic ra quyết định SOTIF dựa trên các KPIs chất lượng ảnh
        is_cta_ok = michelson_contrast >= self.cta_threshold
        is_csnr_ok = csnr >= self.cnr_threshold
        is_sharp_ok = sharpness >= self.sharpness_threshold
        
        if is_cta_ok and is_csnr_ok and is_sharp_ok:
            status = "SAFE"
            sotif_action = "DISPLAY_CONFIRMED"
        elif not is_cta_ok or not is_csnr_ok:
            status = "UNSAFE_RAIN_OR_GLARE"
            sotif_action = "DEGRADED_VERIFICATION_REQUIRED"
        else:
            status = "DEGRADED_BLUR"
            sotif_action = "HOLD_PREVIOUS_DECISION"
            
        return {
            "status": status,
            "cta": float(michelson_contrast),
            "csnr": float(csnr),
            "cdp": float(cdp),
            "sharpness": float(sharpness),
            "sotif_action": sotif_action
        }
```

### 2.3 Cách Hoạt Động của Giao Diện HMI và Mạng CAN Thích Ứng Thời Tiết

ECU xử lý camera TSR sẽ truyền bản tin trạng thái an toàn qua **CAN Bus** lên cụm màn hình hiển thị HMI của xe máy/ô tô:
1.  **Nếu trạng thái trả về là `SAFE`:** HMI hiển thị biển báo giới hạn tốc độ bình thường với viền đỏ nổi bật.
2.  **Nếu trạng thái là `DEGRADED_BLUR`:** HMI kích hoạt thuật toán giữ trạng thái hiển thị (`--hold 3`). Nếu biển báo bị mất tiêu cự hoặc bị che khuất trong 1-2 khung hình (như khi gạt mưa quét qua), biển báo cũ vẫn được ghim giữ hiển thị, tránh chớp nháy màn hình.
3.  **Nếu trạng thái là `UNSAFE_RAIN_OR_GLARE`:** Hệ thống lập tức vô hiệu hóa hiển thị biển báo và chuyển màn hình sang màu xám thông báo **"TSR Unavailable"** để cảnh báo người lái tự động tập trung, loại bỏ rủi ro ỷ lại vào camera đang bị mờ (Foreseeable Misuse).
