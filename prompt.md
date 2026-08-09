# Spec & Prompt Tái Cấu Trúc Toàn Diện Hệ Thống ADAS TSR (Phiên bản Tuyến tính Tuần tự - v3)

Tài liệu này được thiết kế như một **Prompt Đặc Tả Kỹ Thuật Tuyến Tính (Linear progressive Engineering Specification Prompt)**. Toàn bộ cấu trúc thư mục, các file tài liệu nghiên cứu trong `research/` và luồng logic của hệ thống được tổ chức lại theo **Luồng Tiến trình Một Chiều (One-Way Progressive Flow)**. Điều này giải quyết triệt để vấn đề "nhảy lại nội dung cũ" (circularity) bằng cách phân định rõ ràng: **Narrative (Đặt vấn đề) -> Knowledge Base (Tiêu chuẩn & Phân tích rủi ro) -> Implementation (Hiện thực hóa bằng Mã nguồn & Kỹ thuật)**.

---

## 📌 PHẦN 1: TƯ DUY THIẾT KẾ & LUỒNG TUYẾN TÍNH MỘT CHIỀU (PROGRESSIVE FLOW RULE)

Để người đọc không bị lặp nội dung hoặc phải đọc nhảy cóc, toàn bộ kho tài liệu được cấu trúc theo một chuỗi giá trị tăng dần, trong đó **file phía sau luôn kế thừa và hiện thực hóa các yêu cầu được định nghĩa ở file phía trước**:

```
[0. Requirements] -> Xác định đề bài tổng thể và mục tiêu dự án
       │
[1. Narrative]    -> Phản ánh khoảng cách giữa mô hình mẫu (YOLOv8) và thực tế Việt Nam
       │
[2. Knowledge]    -> Chuyển hóa các thách thức thực tế thành Tiêu chuẩn & Phân tích An toàn
       │             (ISO 26262-12, SOTIF ISO 21448, IEEE 2020-2024, HAZOP, FTA)
       ▼
[3. Implementation]-> Lập trình giải thuật nhúng (Hybrid Pipeline, State Manager, HMI)
                     để đáp ứng chính xác các quy chuẩn an toàn đã đề ra
```

---

## 📂 PHẦN 2: CHI TIẾT THỨ TỰ VÀ NỘI DUNG CÁC FILE TRONG THƯ MỤC `research/`

### 2.1 Requirements & Narrative (Đặt vấn đề & Bối cảnh thực tế)

#### 📂 File `research/0.requirements.md` (Đề bài & Mục tiêu Baseline)
*   **Mục tiêu:** Định hình yêu cầu tổng quan từ phía sản xuất (Product Requirements Document - PRD).
*   **Nội dung cốt lõi:**
    *   Tốc độ xử lý yêu cầu tối thiểu trên phần cứng biên (Target FPS >= 15-30 FPS).
    *   Độ chính xác nhận diện biển báo giới hạn tốc độ tại Việt Nam (mAP50 >= 85%).
    *   Môi trường vận hành ODD: Đường bộ đô thị và quốc lộ Việt Nam, hỗ trợ cả ngày lẫn đêm.

#### 📂 File `research/1.narrative/01.prototype_to_production.md` (Hành trình thực tế)
*   **Mục tiêu:** Kể câu chuyện đưa mô hình lý thuyết vào thực tế và chỉ ra các **khoảng cách sản xuất (Production Gaps)**.
*   **Nội dung cốt lõi:**
    *   *Giai đoạn Prototype:* Huấn luyện mô hình YOLOv8 đạt mAP cao trên máy chủ GPU mạnh mẽ.
    *   *Thử thách thực tế (The Reality Shock):* Khi chạy thử trên xe máy ở Việt Nam, hệ thống gặp hàng loạt vấn đề:
        *   Thời tiết mưa lớn làm camera bị nhòe nước, sương mù che khuất biển báo.
        *   Đèn pha xe ngược chiều chói lóa vào ban đêm làm điểm ảnh bị cháy sáng.
        *   Màn hình giao diện hiển thị (HMI) liên tục bị chớp tắt hoặc mất cảnh báo do thuật toán bỏ sót biển báo trong một vài khung hình ngắn hạn.
        *   Phần cứng nhúng của xe máy (ECU công suất thấp) bị quá nhiệt, quá tải bộ nhớ và giảm xung nhịp xử lý (throttling) khiến độ trễ tăng vọt.
    *   *Kết luận:* Các khoảng cách này không thể giải quyết đơn thuần bằng cách "huấn luyện thêm dữ liệu", mà bắt buộc phải có một giải pháp thiết kế an toàn hệ thống và tối ưu mã nguồn nhúng.

---

### 2.2 Knowledge Base (Quy chuẩn kỹ thuật & Thiết kế an toàn khái niệm)

#### 📂 File `research/2.knowledge_base/01.automotive_standards.md` (Tiêu chuẩn An toàn quốc tế)
*   **Mục tiêu:** Chuyển hóa các bài toán từ Narrative thành các yêu cầu an toàn định lượng theo tiêu chuẩn quốc tế.
*   **Nội dung cốt lõi:**
    *   **ISO 26262-12 (An toàn chức năng xe hai bánh):** Phân tích rủi ro động học của xe máy khi vào cua, rung lắc mạnh. Thiết lập cấp độ an toàn **MSIL B** hoặc **MSIL C** (tương đương ASIL A/B của ô tô). Quy định kiểm thử thông qua Hội đồng CCP (Controllability Classification Panel) để đánh giá khả năng kiểm soát của người lái [6].
    *   **SOTIF (ISO 21448 - An toàn tính năng thiết kế):** Xác định miền ODD Việt Nam và các giới hạn kích hoạt (triggering conditions). Phân tích rủi ro ngay cả khi không có lỗi phần cứng/phần mềm:
        *   *Functional Insufficiencies:* YOLOv8 bỏ sót biển báo phụ nhỏ hoặc bị che khuất [3, 5].
        *   *Performance Limitations:* Camera bị hạt mưa phủ mờ, bám bùn đất [3].
        *   *Foreseeable Misuse:* Người lái quá chủ quan vào hệ thống hiển thị dẫn đến chạy quá tốc độ khi camera bị mờ [3].
    *   **Euro NCAP (Speed Assistance Systems - SAS):** Tiêu chuẩn kiểm thử tính năng hỗ trợ tốc độ thông minh (ISA). Yêu cầu nhận diện chính xác biển giới hạn tốc độ cục bộ và biển phụ (sub-signs), duy trì độ sai sót hiển thị dưới 5 km/h và phối hợp dữ liệu camera với bản đồ số (Camera-Map Fusion) để đạt điểm đánh giá tối đa [4, 9].

#### 📂 File `research/2.knowledge_base/02.camera_sensor_ieee2020.md` (Đặc tả CMOS, ISP & Chuẩn IEEE 2020-2024)
*   **Mục tiêu:** Định nghĩa các thông số kỹ thuật tối thiểu của hệ thống cảm biến ảnh để đáp ứng các tiêu chuẩn an toàn trên.
*   **Nội dung cốt lõi:**
    *   **Đặc tả CMOS & ISP phần cứng:**
        *   Dải tương phản động rộng **HDR > 120dB** để chống chói sáng ban đêm và ngược sáng bình minh/hoàng hôn.
        *   Công nghệ **LED Flicker Mitigation (LFM)**: Tăng thời gian phơi sáng của sub-pixel để chống sọc/mất nét khi camera thu hình biển báo LED điện tử nhấp nháy tần số cao.
        *   *ISP Tuning:* Thiết lập vùng đo sáng tự động AE tập trung vào khu vực 1/3 phía trên khung hình (Upper-Third), áp dụng Adaptive Histogram Equalization cục bộ để khôi phục chi tiết ảnh mưa mờ [7].
    *   **Tích hợp tiêu chuẩn IEEE Std 2020™-2024 (Automotive System Image Quality):**
        *   *Khái niệm:* Tiêu chuẩn quốc tế chuẩn hóa việc đo lường chất lượng hình ảnh cho các thuật toán thị giác máy tính ADAS.
        *   *7 KPIs đánh giá chất lượng camera:*
            1.  *Flare (Stray Light):* Đo lượng sáng đi lạc qua thấu kính làm suy giảm tương phản biển báo.
            2.  *Noise (Nhiễu):* Đo mức nhiễu hạt ban đêm.
            3.  *Dynamic Range (Dải tương phản):* Đo bằng tỷ số **CNR (Contrast-to-Noise Ratio)** đặc thù thay vì SNR truyền thống nhằm tính đến ảnh hưởng của flare và HDR artifacts.
            4.  *Spatial Frequency Response (SFR):* Đo độ sắc nét và hàm truyền điều chế MTF dưới tác động của rung động xe máy.
            5.  *Flicker:* Đo chỉ số **MMP (Modulated Light Mitigation Probability)** để đánh giá hiệu quả chống nhấp nháy LED.
            6.  *Contrast Performance:* Đo độ phân biệt tương phản thông qua **CTA (Contrast Transfer Accuracy)** và **CSNR (Contrast Signal-to-Noise Ratio)** hoặc **CDP (Contrast Detection Probability)** để đảm bảo nhận diện tốt biển báo trên các nền hậu cảnh phức tạp.
            7.  *Geometric Calibration Validation:* Đo độ méo hình học của ống kính góc rộng.
        *   *Ứng dụng thực tế:* Thiết kế một bộ giám sát trực tuyến độ tương phản cục bộ (In-line Contrast Monitor) dựa trên chỉ số **CTA/CSNR** của IEEE 2020. Khi chất lượng hình ảnh giảm sút vượt ngưỡng an toàn do mưa mờ, hệ thống sẽ tự động kích hoạt cơ chế fallback.

#### 📂 File `research/2.knowledge_base/03.safety_analysis_hazop_fta.md` (Phân tích An toàn HAZOP & FTA)
*   **Mục tiêu:** Nhận diện và truy vết chi tiết mọi kịch bản lỗi từ vật lý cảm biến lên đến thuật toán.
*   **Nội dung cốt lõi:**
    *   **Bảng HAZOP chi tiết cho Camera:** (Bao gồm 3 Nodes: Hệ quang học & Kính chắn gió, Cảm biến CMOS & ISP, Thuật toán YOLOv8 & CV Pipeline) phân tích rõ các sai lệch (No Light, Less Sharpness, Over-exposure, Latency spikes), nguyên nhân, hậu quả và biện pháp khắc phục.
    *   **Cây Phân tích Lỗi (Fault Tree Analysis - FTA):**
        *   *Sự kiện đỉnh:* Hệ thống TSR không đưa ra cảnh báo giới hạn tốc độ nguy hiểm cho người lái.
        *   *Cây lỗi phân rã qua các cổng logic OR/AND:*
            *   Nhánh 1: Lỗi từ Camera (Mưa mờ bám thấu kính [A1], Lóa sáng CMOS [A2]).
            *   Nhánh 2: Lỗi thuật toán (YOLOv8 bỏ sót biển nhỏ [A3], Nhánh CV truyền thống báo giả [A4]).
            *   Nhánh 3: Lỗi phần cứng nhúng (ECU bị giảm xung throttling do quá nhiệt [B1], tràn bộ nhớ rò rỉ RAM [B2]).
            *   Nhánh 4: Lỗi đường truyền (Đứt cáp vật lý do rung lắc [B3], tắc nghẽn CAN Bus do các ECU an toàn ABS chiếm dụng [B4]).

---

### 2.3 Implementation (Hiện thực hóa bằng Mã nguồn & Giải thuật kỹ thuật)

#### 📂 File `research/3.implementation/01.hybrid_pipeline_architecture.md` (Kiến trúc đường ống lai)
*   **Mục tiêu:** Lập trình giải pháp lai YOLOv8 + Traditional CV để giải quyết các rủi ro bỏ sót biển báo (SOTIF) và duy trì độ trễ ổn định.
*   **Nội dung cốt lõi:**
    *   *Cấu trúc đa luồng (Multi-threaded Pipeline):* Tách biệt luồng đọc khung hình OpenCV, luồng suy luận YOLOv8, và luồng vẽ overlay đồ họa lên màn hình nhằm tối ưu hóa FPS.
    *   *Tích hợp lớp kiểm chứng lai (Hybrid Verification Layer):*
        *   Khi YOLOv8 phát hiện một vùng nghi ngờ biển báo nhưng có độ tự tin thấp (confidence < 0.25) do trời mưa mờ hoặc ngược sáng.
        *   Kích hoạt nhánh **Traditional CV** (sử dụng Hough Circle Transform để tìm khối hình tròn và Color Segmentation trong không gian màu HSV để lọc màu đỏ/xanh) chạy song song trên CPU.
        *   Nếu nhánh CV truyền thống xác nhận có hình dạng và màu sắc biển báo tại tọa độ đó, hệ thống sẽ nâng độ tự tin để giữ nhận diện, ngăn ngừa việc bỏ sót thông tin nguy hiểm.

#### 📂 File `research/3.implementation/02.state_manager_and_hmi.md` (Bộ quản lý trạng thái, CAN Bus & HMI Thích ứng)
*   **Mục tiêu:** Khắc phục triệt để hiện tượng chớp tắt hiển thị và lập trình giao diện cảnh báo an toàn thích ứng khi camera bị mưa mờ.
*   **Nội dung cốt lõi:**
    *   **Mã giải thuật Bộ quản lý trạng thái (State Manager):**
        *   Sử dụng cơ chế hàng đợi lưu giữ biển báo đã nhận diện.
        *   Khi camera bị hạt nước mưa hoặc gạt mưa che khuất biển báo tạm thời, tham số `--hold 3` sẽ ra lệnh cho State Manager tiếp tục hiển thị biển giới hạn tốc độ cũ trong vòng 3 khung hình tiếp theo, tránh việc biến mất đột ngột gây phiền toái cho người lái [9].
    *   **Cơ chế truyền thông tin qua CAN Bus:** Định nghĩa cấu trúc bản tin CAN (ID, DLC, các byte biểu diễn giá trị giới hạn tốc độ và trạng thái hệ thống) gửi đến cụm đồng hồ xe máy.
    *   **Lập trình trạng thái HMI thích ứng dựa trên IEEE 2020:**
        *   Nếu module đo đạc trực tuyến phát hiện chỉ số tương phản cục bộ **CTA / CNR** giảm xuống dưới ngưỡng tối thiểu do mưa quá dày.
        *   Hệ thống tự động kích hoạt **Trạng thái suy giảm hiệu năng (Degraded Mode)**: tắt bớt nhánh Traditional CV để giảm tải cho CPU, chuyển cấu hình YOLO về siêu nhẹ (`--imgsz 512 --skip 2`).
        *   Nếu camera hoàn toàn bị phủ nước không thể quan sát, hệ thống phát bản tin CAN báo trạng thái **Unavailable (Không khả dụng do thời tiết)** lên màn hình HMI để người lái chủ động kiểm soát tốc độ bằng mắt thường, triệt tiêu rủi ro lạm dụng tính năng (Foreseeable Misuse).

#### 📂 File `research/3.implementation/03.edge_deployment_and_benchmarks.md` (Tối ưu hóa nhúng & Quản lý quá nhiệt)
*   **Mục tiêu:** Hiện thực hóa các giải pháp kiểm soát lỗi dòng dữ liệu, quá nhiệt phần cứng biên theo tiêu chuẩn ISO 26262-12.
*   **Nội dung cốt lõi:**
    *   *Hướng dẫn tối ưu hóa phần cứng biên (Jetson Nano / Low-cost ECU):*
        *   Cơ chế nhảy khung hình (`--skip 1` hoặc `--skip 2`) giúp giảm tải tính năng suy luận AI xuống 50% hoặc 66% khi xử lý video độ phân giải cao (4K) [8].
        *   Giới hạn chiều rộng ảnh đầu vào (`--max-width 1280`) trước khi đưa vào luồng ISP để bảo vệ bộ nhớ đệm [8].
    *   *Quản lý quá nhiệt và rò rỉ bộ nhớ:*
        *   Đo nhiệt độ CPU/GPU nhúng định kỳ thông qua sysfs. Nếu nhiệt độ vượt quá 80°C, State Manager sẽ tự động tăng số lượng `--skip` lên tối đa để hạ nhiệt hệ thống (CPU-safer mode).
        *   Thiết lập cơ chế giải phóng bộ nhớ PyTorch cache tuần hoàn để tránh lỗi tràn bộ nhớ (Out-of-Memory).

#### 📂 File `research/3.implementation/04.production_lite_demo_notebook.md` (Thử nghiệm & Đánh giá)
*   **Mục tiêu:** Cung cấp công cụ chạy kiểm chứng thực nghiệm và Colab Notebook có khả năng mô phỏng các hiệu ứng thời tiết.
*   **Nội dung cốt lõi:**
    *   Mã nguồn Jupyter Notebook kết nối Google Drive tải video road test thực tế của Việt Nam [61].
    *   Tích hợp các bộ lọc mô phỏng mưa (Rain effect overlay), sương mù (Fog overlay) và lóa sáng (Gaussian Glare) trực tiếp lên video đầu vào bằng thư viện OpenCV.
    *   Chạy đánh giá benchmark mAP và FPS của mô hình YOLOv8 dưới các mức độ nhiễu mô phỏng khác nhau để chứng minh một cách khoa học tính thuyết phục của kiến trúc lai và bộ lọc State Manager.

---

## 📌 PHẦN 3: ĐẶC TẢ TÁI CẤU TRÚC README.md VÀ TRÁNH LỖI SYMLINKS

### 3.1 Cấu trúc README.md ở Root (Sạch sẽ & Độc lập)
*   README.md tuyệt đối không chứa các phân tích HAZOP, FTA dài dòng hay định nghĩa IEEE 2020. Nó chỉ đóng vai trò là sách hướng dẫn vận hành nhanh (Quick Start).
*   Chuyển toàn bộ các bảng xử lý lỗi phần cứng và phần mềm ra file `TROUBLESHOOTING.md` độc lập ở Root. README chỉ để lại liên kết hướng dẫn.

### 3.2 Giải quyết triệt để lỗi Symlinks vật lý trên Windows
*   *Lý do lỗi:* Thư mục `docs/` sử dụng liên kết tượng trưng (symlinks) trỏ sang `research/` và `README.md`, gây lỗi biên dịch MkDocs trên Windows khi không bật Developer Mode [65].
*   *Giải pháp thiết kế mới:*
    *   Xóa bỏ toàn bộ các file symlink vật lý trong thư mục `docs/`.
    *   Cấu hình file `mkdocs.yml` sử dụng plugin **`mkdocs-multirepo-plugin`** để tự động import các file Markdown từ các thư mục khác nhau khi build trang web tài liệu.
    *   Hoặc viết một script Python trung gian (`code/build_docs.py`) thực hiện copy tự động các file Markdown từ `research/` và `README.md` vào thư mục tạm thời `docs/` trước khi gọi lệnh `mkdocs build`, đảm bảo dự án chạy mượt mà trên cả Windows, Linux và macOS.

---

## 🤖 PHẦN 4: PROMPT GIAO VIỆC CHI TIẾT CHO AI (AI ACTIONABLE PROMPT)

*Nếu bạn đưa file này cho một AI để thực hiện công việc, hãy copy đoạn prompt dưới đây để bắt đầu:*

> **PROMPT GIAO VIỆC CHO AI:**
> "Chào bạn, hãy đóng vai trò là một chuyên gia kiến trúc phần mềm Automotive ADAS cao cấp, chuyên gia An toàn Hệ thống (SOTIF & Functional Safety Engineer) và chuyên gia Xử lý Ảnh. Dựa trên tài liệu đặc tả kỹ thuật tuyến tính `prompt.md` trên, hãy thực hiện các nhiệm vụ sau cho kho lưu trữ `adas-tsr`:
>
> 1. **Tái cấu trúc Root:**
>    - Viết lại file `README.md` mới hoàn toàn sạch sẽ theo đúng cấu trúc 4 phần (Tổng quan dự án lai DL+CV, Cài đặt môi trường nhanh, Hướng dẫn chạy CLI, và Bản đồ điều hướng tài liệu).
>    - Trích xuất toàn bộ bảng xử lý sự cố ra file `TROUBLESHOOTING.md` độc lập.
>    - Cập nhật cấu hình `mkdocs.yml` loại bỏ các symlink vật lý, thay thế bằng giải pháp tương thích đa nền tảng (sử dụng plugin multirepo hoặc mô tả giải pháp script build tự động).
>
> 2. **Xây dựng hệ thống tài liệu nghiên cứu theo luồng tuyến tính một chiều:**
>    - Tạo file `research/0.requirements.md` định vị rõ đề bài PRD của dự án.
>    - Tạo file `research/1.narrative/01.prototype_to_production.md` mô tả sinh động hành trình đưa YOLOv8 vào thực tế và chỉ rõ các khoảng trống sản xuất (mưa mờ, chói sáng, quá nhiệt phần cứng biên, chớp tắt HMI).
>    - Tạo file `research/2.knowledge_base/01.automotive_standards.md` đặc tả chi tiết về cách tuân thủ ISO 26262-12 (MSIL xe hai bánh, vai trò CCP), SOTIF ISO 21448 (ODD Việt Nam, triggering conditions), và Euro NCAP SAS (SLIF/ISA, Camera-Map Fusion).
>    - Tạo file `research/2.knowledge_base/02.camera_sensor_ieee2020.md` làm rõ cấu hình CMOS (HDR > 120dB, LFM chống nhấp nháy đèn LED), ISP Tuning, và giải thích chi tiết 7 KPIs cốt lõi của tiêu chuẩn chất lượng hình ảnh IEEE 2020-2024 (bao gồm chỉ số CNR, MMP, CTA/CSNR) cùng ứng dụng thiết kế bộ giám sát chất lượng ảnh trực tuyến.
>    - Tạo file `research/2.knowledge_base/03.safety_analysis_hazop_fta.md` chứa bảng phân tích HAZOP camera hoàn chỉnh và sơ đồ Cây phân tích lỗi (FTA) phân rã logic từ Sự kiện đỉnh xuống các sự kiện cơ bản về thời tiết, thuật toán, phần cứng và dòng truyền mạng CAN.
>    - Tạo file `research/3.implementation/01.hybrid_pipeline_architecture.md` mô tả cấu trúc lập trình đường ống đa luồng và thuật toán của nhánh kiểm chứng lai YOLOv8 + Traditional CV.
>    - Tạo file `research/3.implementation/02.state_manager_and_hmi.md` mô tả thuật toán mã nguồn State Manager (`--hold 3`), ánh xạ bản tin CAN Bus và cách lập trình HMI hiển thị thích ứng (Degraded/Unavailable Mode) dựa trên chất lượng ảnh IEEE 2020.
>    - Tạo file `research/3.implementation/03.edge_deployment_and_benchmarks.md` hướng dẫn tối ưu Jetson Nano (`--imgsz 512`, nhảy khung hình `--skip`) và giải thuật giám sát nhiệt độ, giải phóng bộ nhớ đệm phòng ngừa crash.
>    - Tạo file `research/3.implementation/04.production_lite_demo_notebook.md` hướng dẫn chạy thử nghiệm, mô phỏng hiệu ứng thời tiết bằng OpenCV và đánh giá mAP/FPS.
>
> Hãy viết tất cả các tài liệu này bằng tiếng Việt cực kỳ chuyên nghiệp, bám sát thuật ngữ chuyên ngành kỹ thuật ô tô và sử dụng các tiêu chuẩn an toàn quốc tế làm nền tảng vững chắc cho mọi quyết định thiết kế."
