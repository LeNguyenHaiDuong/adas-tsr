# Spec & Prompt Tái Cấu Trúc và Nâng Cấp Hệ Thống ADAS TSR (Traffic Sign Recognition) - Phiên bản v2

Tài liệu này được thiết kế như một **Prompt Đặc Tả Kỹ Thuật Tuyến Tính (Linear Engineering Specification & Prompt)** có độ chi tiết cao. Tài liệu giải quyết triệt để vấn đề "vòng lặp nội dung" (circular references) từ bản thảo trước, phân định rõ ràng ranh giới giữa **Bối cảnh phát triển (Narrative)**, **Yêu cầu & Tiêu chuẩn An toàn Thiết kế (Knowledge Base)**, và **Hiện thực hóa Kỹ thuật (Implementation)**.

Bạn có thể cung cấp file này cho các mô hình AI nâng cao (như Claude 3.5 Sonnet, GPT-4o) để tự động hóa việc tái cấu trúc mã nguồn, viết lại tài liệu hoặc dùng làm cẩm nang hướng dẫn trực tiếp cho đội ngũ phát triển dự án `adas-tsr`.

---

## 📌 PHẦN 1: PHÂN TÍCH LUỒNG TÀI LIỆU TUYẾN TÍNH (LINEAR FLOW ARCHITECTURE)

Để loại bỏ cảm giác đọc bị "nhảy ngược lại nội dung cũ", cấu trúc thư mục tài liệu `research/` được chuẩn hóa theo mô hình **Luồng Tuyến Tính Một Chiều (One-way Progressive Flow)**:

```
[1. NARRATIVE: Bối cảnh & Lỗ hổng] 
       │ (Phát hiện các thiếu hụt khi đưa mô hình AI lên xe máy thực tế)
       ▼
[2. KNOWLEDGE BASE: Tiêu chuẩn & Đặc tả An toàn Thiết kế]
       │ (Chuyển hóa lỗ hổng thành yêu cầu đạt chuẩn ISO 26262-12, SOTIF, IEEE 2020, Euro NCAP)
       ▼
[3. IMPLEMENTATION: Hiện thực hóa & Tối ưu hóa mã nguồn]
       │ (Viết code Python, thiết kế thuật toán lai YOLO+CV, State Manager, CLI để đáp ứng tiêu chuẩn)
       ▼
[4. PRESENTATION: Trình diễn & Báo cáo]
```

### Chi tiết Phân mục và Thứ tự các File trong thư mục `research/`:

#### 📁 Thư mục `research/1.narrative/` (The Story & Context)
*Mục tiêu:* Đóng vai trò là điểm xuất phát, kể lại câu chuyện phát triển dự án và chỉ ra các ranh giới vận hành cùng lỗ hổng thực tế. **Tuyệt đối không đưa code hoặc phân tích tiêu chuẩn chi tiết vào đây.**
*   **`01.prototype_to_production.md`**: Hành trình đưa mô hình YOLOv8 từ môi trường nghiên cứu lý thuyết (Google Colab) lên môi trường chạy thực tế trên xe máy tại Việt Nam [55, 56]. Nhận diện các "khoảng trống sản xuất" (Production Gaps): thời tiết khắc nghiệt (mưa mờ), lóa sáng, phần cứng yếu, hiện tượng chớp tắt màn hình hiển thị HMI, và sự cần thiết của các tiêu chuẩn công nghiệp [56].

#### 📁 Thư mục `research/2.knowledge_base/` (Theoretical & Safety Specs)
*Mục tiêu:* Tiếp nhận các lỗ hổng từ Narrative để chuyển hóa thành các yêu cầu, tiêu chuẩn kỹ thuật và phân tích an toàn hệ thống ở mức thiết kế khái niệm (concept level). **Tuyệt đối không đưa code cụ thể hay tham số CLI vào đây.**
*   **`01.automotive_standards.md`**: Nghiên cứu sâu về các tiêu chuẩn quốc tế bắt buộc phải tuân thủ:
    *   **ISO 26262-12**: Đặc tả an toàn chức năng thích ứng cho xe hai bánh, định nghĩa mức rủi ro MSIL (A đến D) và ánh xạ MSIL D sang ASIL C của ô tô để áp dụng quy trình kiểm soát lỗi nghiêm ngặt [2, 6].
    *   **ISO 21448 (SOTIF)**: Đặc tả an toàn tính năng thiết kế, phân tích 3 nhóm rủi ro: Functional Insufficiencies (thiếu hụt thuật toán), Performance Limitations (giới hạn cảm biến camera khi mưa mờ), và Foreseeable Misuse (người lái lạm dụng tính năng) [3, 38, 39].
    *   **Euro NCAP Speed Assistance (SAS)**: Quy trình kiểm thử hệ thống cảnh báo tốc độ thông minh (ISA) và nhận diện biển báo (SLIF), cơ chế chấm điểm (Hệ thống kết hợp Camera + Bản đồ đạt tối đa 1.5 điểm) [4, 75, 98].
*   **`02.camera_sensor_ieee2020.md`**: Tiêu chuẩn chất lượng hình ảnh **IEEE 2020-2024**:
    *   Định nghĩa 7 chỉ số KPIs cốt lõi để đánh giá camera (Flare, Noise, Dynamic Range CNR, SFR, Flicker MMP, Contrast Performance CTA/CSNR, Distortion) [e-con Systems, Imatest].
    *   Yêu cầu phần cứng cảm biến CMOS: Dải tương phản động HDR > 120dB, Công nghệ giảm thiểu nhấp nháy đèn LED (LED Flicker Mitigation - LFM) để đọc biển báo điện tử ban ngày.
    *   Đặc tả hiệu chỉnh ISP (ISP Tuning): Auto Exposure phân vùng Upper-Third, Local Tone Mapping khôi phục chữ số bị chói sáng.
*   **`03.safety_analysis_hazop_fta.md`**: Tài liệu phân tích an toàn hệ thống:
    *   Bảng HAZOP chi tiết cho cụm camera (Node 1: Hệ thống quang học & Kính chắn gió, Node 2: Cảm biến CMOS & ISP, Node 3: Thuật toán) đối phó với hiện tượng mưa mờ, lóa sáng [HAZOP].
    *   Sơ đồ cây phân tích lỗi (Fault Tree Analysis - FTA) truy vết nguyên nhân từ sự kiện đỉnh "TSR không cảnh báo giới hạn tốc độ" xuống các sự kiện cơ bản ở phần cứng, mô hình AI, và đường truyền CAN.

#### 📁 Thư mục `research/3.implementation/` (Technical Engineering)
*Mục tiêu:* Hiện thực hóa tất cả các giải pháp kỹ thuật, thuật toán và mã nguồn cụ thể để đáp ứng trực tiếp các tiêu chuẩn an toàn tại Knowledge Base. **Đây là nơi tập trung mã nguồn, cấu hình tham số CLI, và số liệu Benchmark thực tế.**
*   **`01.hybrid_pipeline_architecture.md`**: Đặc tả thuật toán lai (YOLOv8 + Traditional CV):
    *   Kiến trúc đường ống xử lý luồng video đa luồng (Multi-threading).
    *   Hiện thực hóa nhánh **Traditional CV (Hough Circle & Color Thresholding)** hoạt động như một lớp kiểm chứng chéo độc lập (Verification Layer) nhằm giải quyết rủi ro SOTIF về giới hạn thuật toán YOLO [7, 11].
*   **`02.state_manager_and_hmi.md`**: Giải thuật lọc nhiễu và thiết kế giao diện HMI:
    *   Mã nguồn giải thuật **State Manager** sử dụng bộ lọc giữ trạng thái thông qua tham số `--hold 3` để duy trì hiển thị biển báo khi gạt mưa đi qua hoặc camera bị mờ tạm thời [13, 63].
    *   Cơ chế gửi bản tin cảnh báo qua mạng CAN Bus [12].
    *   Thiết kế giao diện hiển thị trạng thái suy giảm (Degraded Mode) và thông báo tạm ngưng tính năng (Unavailable State) khi chất lượng ảnh dưới chuẩn IEEE 2020 nhằm ngăn chặn hành vi lạm dụng tính năng [3].
*   **`03.edge_deployment_and_benchmarks.md`**: Tối ưu hóa và kiểm định trên phần cứng nhúng biên (Edge ECU như Jetson Nano):
    *   Cấu hình tối ưu tài nguyên: Giảm kích thước ảnh đầu vào (`--imgsz 512`), nhảy khung hình (`--skip 1` hoặc `--skip 2`) để duy trì độ trễ ổn định (deterministic latency) [8, 12].
    *   Cơ chế tự động chuyển đổi cấu hình tiết kiệm năng lượng (CPU-safer degraded mode) khi ECU phát hiện trạng thái quá nhiệt.
*   **`04.production_lite_demo_notebook.md`**: Hướng dẫn chạy thử nghiệm thực tế:
    *   Cách sử dụng file `run_demo.sh` để kích hoạt nhanh đường ống xử lý [58].
    *   Colab production-lite notebook hướng dẫn mô phỏng các bộ lọc nhiễu thời tiết và đánh giá độ chính xác (mAP) cùng hiệu năng (FPS) của hệ thống [56, 57].

---

## 🛠️ PHẦN 2: HƯỚNG DẪN TÁI CẤU TRÚC KHO LƯU TRỮ GITHUB (REPOSITORY RESTRUCTURING)

### 2.1 Cấu trúc file `README.md` mới ở gốc (Root Entrypoint)
File `README.md` mới phải đóng vai trò là cổng điều hướng cấp cao, không nhồi nhét quá nhiều chi tiết khắc phục sự cố hay tài liệu nghiên cứu sâu [56]. Cấu trúc chuẩn hóa gồm 4 phần:
1.  **Tổng quan dự án (Project Overview):** Giới thiệu hệ thống TSR xe máy Việt Nam sử dụng đường ống lai [5, 7]. Sơ đồ cấu trúc thư mục rút gọn.
2.  **Cài đặt & Chuẩn bị nhanh (Quick Start):** Yêu cầu hệ thống và 3 tùy chọn thiết lập môi trường (Conda, Venv, Auto Script) [58]. Hướng dẫn tải Model weights `models/best.pt` tự động [59].
3.  **Hướng dẫn vận hành & Các lệnh CLI (Usage & CLI Options):** Bảng tham số CLI và các kịch bản chạy demo thực tế (headless, webcam, tối ưu CPU, chạy nhánh lai) [62, 63].
4.  **Điều hướng tài liệu nghiên cứu (Documentation Index):** Bảng liên kết đến các file index trong thư mục `research/` theo thứ tự tuyến tính [64].

### 2.2 Tách biệt phần Khắc phục sự cố thành `TROUBLESHOOTING.md`
Chuyển toàn bộ bảng khắc phục sự cố hiện tại ra khỏi `README.md` để tạo thành file `TROUBLESHOOTING.md` ở thư mục gốc [67]. Hướng dẫn chi tiết cách xử lý lỗi Bus error, lỗi không phát hiện được biển báo, lỗi video 4K chạy chậm, lỗi thiếu model, và lỗi hiển thị GUI trên WSL [67].

### 2.3 Xử lý lỗi Symlinks trên Windows
Loại bỏ các symlinks vật lý trong thư mục `docs/`. Cập nhật file cấu hình `mkdocs.yml` để sử dụng các plugin hỗ trợ đọc tài liệu ngoài thư mục (như `mkdocs-multirepo-plugin`) hoặc sử dụng một script build Python trung gian tự động copy các file Markdown từ `research/` và `README.md` vào thư mục tạm `docs/` trước khi chạy `mkdocs build` [65].

---

## 🛡️ PHẦN 3: ĐẶC TẢ CHI TIẾT CÁC TÀI LIỆU AN TOÀN VÀ TIÊU CHUẨN (KNOWLEDGE BASE)

### 3.1 Phân tích HAZOP cụm camera khi trời mưa mờ
Bảng HAZOP phải được hiện thực hóa đầy đủ trong `research/2.knowledge_base/03.safety_analysis_hazop_fta.md` với các nút phân tích sau:
*   **Node 1: Hệ thống quang học & Kính chắn gió (Optical Lens & Windshield):**
    *   *Sai lệch:* Độ truyền quang bằng Không (No/Loss) do mưa lớn, bụi bẩn, sương muối [3]. Hậu quả là YOLOv8 bỏ sót biển báo (False Negative) [3]. Biện pháp: Tích hợp gạt mưa tự động, sưởi kính, và phát hiện trạng thái Degraded Mode [7].
    *   *Sai lệch:* Độ sắc nét giảm (Less/Low) do nước mưa chảy loang hoặc rung động mạnh của động cơ xe máy. Hậu quả là lỗi định vị (localization errors) hoặc phân loại nhầm (False Positive) [5, 6]. Biện pháp: Chống rung vật lý theo chuẩn ISO 26262-12, bật DIS trên ISP, và cấu hình `--hold 3` [6, 13].
*   **Node 2: Cảm biến CMOS & Bộ ISP (Image Sensor & ISP):**
    *   *Sai lệch:* Độ phơi sáng quá cao (More/High) do chói sáng mặt trời hoặc đèn pha ban đêm. Hậu quả là cháy sáng pixel bão hòa vùng biển báo [3]. Biện pháp: Cảm biến HDR > 120dB, Auto Exposure vùng Upper-third, và chuẩn hóa histogram thích ứng [7].
*   **Node 3: Thuật toán YOLO & CV Pipeline (YOLOv8 & CV Pipeline):**
    *   *Sai lệch:* Tần suất xử lý giảm (Less/Low) do ECU nhúng bị quá nhiệt hoặc luồng dữ liệu video 4K vượt quá băng thông [8]. Hậu quả là cảnh báo trễ sau khi phương tiện đã đi qua biển báo [4, 8]. Biện pháp: Chuyển sang CPU-safer Degraded Mode (`--imgsz 512`, `--skip 1` hoặc `--skip 2`), cơ chế tự ngắt quá nhiệt [8].

### 3.2 Phân tích Cây Lỗi (Fault Tree Analysis - FTA)
Sơ đồ cây lỗi (FTA) phải được vẽ bằng định dạng Markdown Mermaid hoặc văn bản cấu trúc trong `research/2.knowledge_base/03.safety_analysis_hazop_fta.md` với sự kiện đỉnh: **"TSR không hiển thị cảnh báo giới hạn tốc độ nguy hiểm"**.
*   **Cổng OR cấp 1:** Phân nhánh thành 3 nhóm nguyên nhân lớn:
    1.  *Lỗi nhận diện từ Camera:* Do sự kiện cơ bản mưa mờ/bụi bẩn bám (A1), lóa sáng CMOS (A2), hoặc thuật toán YOLOv8 bỏ sót (A3) [3, 5].
    2.  *Lỗi xử lý phần cứng ECU:* Do sự kiện cơ bản tụt xung nhịp vì quá nhiệt (B1) hoặc tràn bộ nhớ OOM (B2) [8, 12].
    3.  *Lỗi truyền thông và hiển thị HMI:* Do sự kiện cơ bản cáp kết nối vật lý bị lỏng/đứt vì xe máy rung lắc (B3) hoặc nghẽn mạng CAN Bus phương tiện (B4) [6, 12].

### 3.3 Đặc tả Phần cứng CMOS và Hiệu chỉnh ISP (ISP Tuning)
Tài liệu `research/2.knowledge_base/02.camera_sensor_ieee2020.md` phải đặc tả các yêu cầu kỹ thuật:
*   **HDR > 120dB:** Sử dụng Multi-exposure HDR hoặc Split-diode pixel để thu ảnh không bị nhòe chuyển động (motion artifacts) ở tốc độ cao.
*   **LED Flicker Mitigation (LFM):** Kéo dài thời gian phơi sáng của sub-pixel vượt qua chu kỳ nhấp nháy 90Hz - 1000Hz của biển báo điện tử LED để thu được hình ảnh trọn vẹn, tránh sọc ảnh khiến AI không đọc được chữ số.
*   **ISP Tuning:** Cấu hình đo sáng AE tập trung 1/3 phía trên khung hình (Upper-Third), bật tính năng Local Tone Mapping (LTM) để khử lóa sáng cục bộ ban đêm.

### 3.4 Chuẩn hóa Đánh giá Chất lượng Ảnh theo IEEE 2020-2024
Tài liệu `research/2.knowledge_base/02.camera_sensor_ieee2020.md` phải trình bày rõ cách áp dụng tiêu chuẩn này:
*   **Định nghĩa 7 KPIs:** Flare (Ánh sáng đi lạc), Noise (Nhiễu hạt), Dynamic Range (đo bằng Contrast-to-Noise Ratio - CNR), Spatial Frequency Response (SFR - độ sắc nét MTF), Flicker (đo bằng Modulated Light Mitigation Probability - MMP), Contrast Performance Indicator (đo bằng Contrast Transfer Accuracy - CTA và Contrast Signal-to-Noise Ratio - CSNR), và Geometric Calibration Validation (hiệu chuẩn hình học chống méo ống kính góc rộng).
*   **Cách thức áp dụng thực tế:**
    1.  *Kiểm thử phòng Lab:* Sử dụng phần mềm **Imatest** hoặc **iQ-Analyzer-X** phân tích ảnh chụp từ test charts chuẩn để tính toán các trị số SFR, CNR, và CTA.
    2.  *Giám sát Trực tuyến (In-line Monitor):* Viết module Python tính toán nhanh chỉ số tương phản cục bộ (CTA) hoặc CNR trực tiếp trên luồng video đầu vào. Nếu chỉ số giảm xuống dưới ngưỡng an toàn do trời mưa quá mờ, hệ thống lập tức kích hoạt trạng thái an toàn suy giảm (Degraded Mode), phát cảnh báo tạm ngưng tính năng TSR trên màn hình HMI để bảo vệ người lái khỏi rủi ro lạm dụng tính năng [3].
    3.  *Lựa chọn linh kiện:* Yêu cầu Tier 1 cung cấp datasheet camera cam kết các chỉ số đạt chuẩn IEEE 2020 (đặc biệt là MMP chống nhấp nháy LED và CNR ổn định ở nhiệt độ cao).

---

## 🤖 PHẦN 4: PROMPT GIAO VIỆC CHO AI ĐỂ THỰC THI (AI EXECUTION PROMPT)

*Hãy copy đoạn prompt dưới đây để giao việc cho AI thực hiện toàn bộ quy trình tái cấu trúc này:*

> **PROMPT THIẾT KẾ & THỰC THI KIẾN TRÚC TUYẾN TÍNH:**
> "Chào bạn, hãy đóng vai trò là một Chuyên gia Kiến trúc Phần mềm Automotive ADAS và Chuyên gia An toàn Hệ thống (Functional Safety & SOTIF Engineer). Dựa trên đặc tả kiến trúc tuyến tính trong `prompt.md`, hãy thực thi các nhiệm vụ tái cấu trúc và viết lại tài liệu cho kho lưu trữ `adas-tsr` như sau:
> 
> 1. **Viết lại file `README.md` mới tại thư mục gốc:** Phải tuân thủ cấu trúc 4 phần trực quan tại Mục 2.1, lược bỏ hoàn toàn các hướng dẫn gỡ lỗi sâu hay lý thuyết an toàn, chỉ giữ vai trò điều hướng vận hành. Đưa bảng liên kết tài liệu `research/` theo đúng thứ tự tuyến tính mới.
> 2. **Tạo file `TROUBLESHOOTING.md` độc lập tại thư mục gốc:** Chứa bảng hướng dẫn khắc phục sự cố chi tiết đã tách từ README.md cũ.
> 3. **Viết lại tài liệu `research/1.narrative/01.prototype_to_production.md`:** Tập trung vào câu chuyện dịch chuyển từ Colab lên sản phẩm thực tế, nêu bật các khoảng trống sản xuất (mưa mờ, phần cứng yếu, lóa sáng) mà không lạm dụng code hay phân tích tiêu chuẩn sâu.
> 4. **Tạo tài liệu `research/2.knowledge_base/01.automotive_standards.md`:** Phân tích chi tiết các tiêu chuẩn ISO 26262-12 (MSIL xe hai bánh), ISO 21448 (SOTIF ODD, các dạng lỗi), và Euro NCAP Speed Assist (quy trình chấm điểm camera + bản đồ).
> 5. **Tạo tài liệu `research/2.knowledge_base/02.camera_sensor_ieee2020.md`:** Đặc tả chi tiết dải động HDR > 120dB, bộ giảm nhấp nháy LED LFM, hiệu chỉnh ISP (Auto Exposure Upper-Third, Local Tone Mapping), và bộ 7 KPIs tiêu chuẩn IEEE 2020-2024 kèm hướng dẫn áp dụng thực tế (kiểm thử Lab bằng Imatest, viết module giám sát trực tuyến độ tương phản cục bộ CTA).
> 6. **Tạo tài liệu `research/2.knowledge_base/03.safety_analysis_hazop_fta.md`:** Hiện thực hóa bảng phân tích HAZOP cho camera (Node 1: Quang học, Node 2: CMOS/ISP, Node 3: Thuật toán) và Sơ đồ Cây phân tích lỗi (FTA) dưới dạng văn bản cấu trúc/Mermaid bám sát các sự kiện từ phần cứng đến CAN Bus.
> 7. **Tạo tài liệu `research/3.implementation/01.hybrid_pipeline_architecture.md`:** Đặc tả kỹ thuật đường ống xử lý đa luồng của `tsr_demo.py` và cách tích hợp nhánh lai YOLOv8 + Traditional CV để làm lớp xác thực độc lập giải quyết yêu cầu an toàn SOTIF.
> 8. **Tạo tài liệu `research/3.implementation/02.state_manager_and_hmi.md`:** Trình bày giải thuật State Manager xử lý chống chớp tắt biển báo (`--hold 3`), cơ chế bản tin CAN Bus và cách HMI hiển thị cảnh báo Degraded Mode / Unavailable State khi chất lượng ảnh dưới chuẩn chất lượng IEEE 2020.
> 9. **Tạo tài liệu `research/3.implementation/03.edge_deployment_and_benchmarks.md`:** Hướng dẫn cấu hình tối ưu tài nguyên (`--imgsz 512`, `--skip 1/2`) để duy trì độ trễ ổn định trên Jetson Nano và cơ chế tự động hạ tần suất chạy khi quá nhiệt.
> 10. **Tạo tài liệu `research/3.implementation/04.production_lite_demo_notebook.md`:** Hướng dẫn chạy `run_demo.sh` và cách sử dụng Colab notebook mô phỏng thời tiết và đánh giá mAP/FPS.
> 
> Đảm bảo tất cả nội dung được viết hoàn toàn bằng tiếng Việt chuyên nghiệp, bám sát các thuật ngữ chuyên ngành automotive kỹ thuật cao, tạo nên một luồng đọc tuyến tính mượt mà, tiếp nối chặt chẽ và không lặp lại thông tin."
