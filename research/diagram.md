# TSR System Architecture

## Tổng quan kiến trúc

Kiến trúc TSR (Traffic Sign Recognition) trong hệ thống ADAS production thường được chia thành 3 lớp chính:

1. **Perception Layer**
   - Chịu trách nhiệm nhận biết biển báo từ dữ liệu cảm biến.
   - Bao gồm detection, classification, tracking và temporal confirmation.

2. **Feature Logic Layer**
   - Quyết định biển báo nào thực sự áp dụng cho xe.
   - Bao gồm context filtering, lane association, map fusion và state management.

3. **Vehicle Integration Layer**
   - Tích hợp với các ECU khác trên xe.
   - Cung cấp thông tin cho HMI, ISA, Diagnostics và Data Logging.

## Legend màu Mermaid

> Legend này áp dụng cho sơ đồ Mermaid trong file này.

| Màu | Vai trò | Ý nghĩa |
|---|---|---|
| <span style="display:inline-block;width:14px;height:14px;border:1px solid #2F66D0;background:#EDF3FF;"></span> | `feature` | Perception, context, fusion, hoặc processing core của TSR |
| <span style="display:inline-block;width:14px;height:14px;border:1px solid #7C3AED;background:#F4ECFF;"></span> | `temporal` | Tracking, temporal confirmation, hoặc state-oriented block |
| <span style="display:inline-block;width:14px;height:14px;border:1px solid #14866D;background:#EAF7F2;"></span> | `source` | Sensor hoặc input source đi vào kiến trúc |
| <span style="display:inline-block;width:14px;height:14px;border:1px solid #1E8E5A;background:#E8F7EE;"></span> | `integration` | Output HMI, ISA, diagnostics, logging, hoặc đầu ra hệ thống |

---

## TSR Architecture Diagram

```mermaid
flowchart TD

%% =====================================================
%% INPUT SOURCES
%% =====================================================

CAM["Front Camera Module"]
MAP["Navigation / HD Map"]
SAS["Steering Angle Sensor"]
ESC["ESC / Vehicle Dynamics"]
CFG["Vehicle Configuration"]

%% =====================================================
%% TSR ECU
%% =====================================================

subgraph TSR["TSR ADAS Architecture"]

    direction TD

    %% ---------------------------------
    %% PERCEPTION
    %% ---------------------------------

    subgraph PERCEPTION["Perception Layer"]

        direction LR

        PRE["Image Preprocessing"]
        DET["Traffic Sign Detection"]
        CLS["Traffic Sign Classification"]
        TRK["Traffic Sign Tracking"]
        TMP["Temporal Confirmation"]

        PRE --> DET
        DET --> CLS
        CLS --> TRK
        TRK --> TMP

    end

    %% ---------------------------------
    %% FEATURE LOGIC
    %% ---------------------------------

    subgraph FEATURE["Feature Logic Layer"]

        direction LR

        CTX["Context Filtering"]
        LANE["Lane Association"]
        FUSION["Camera + Map Fusion"]
        STATE["TSR State Manager"]

        CTX --> LANE
        LANE --> FUSION
        FUSION --> STATE

    end

    %% ---------------------------------
    %% VEHICLE INTEGRATION
    %% ---------------------------------

    subgraph INTEGRATION["Vehicle Integration Layer"]

        direction LR

        HMI["Cluster / HUD Output"]
        ISA["Intelligent Speed Assistance"]
        DIAG["Diagnostics"]
        LOG["Data Logging"]

    end

end

%% =====================================================
%% CROSS-LAYER CONNECTIONS
%% =====================================================

TMP --> CTX

STATE --> HMI
STATE --> ISA
STATE --> DIAG
STATE --> LOG

%% =====================================================
%% INPUT CONNECTIONS
%% =====================================================

CAM --> PRE

MAP --> FUSION

SAS --> LANE

ESC --> LANE

CFG --> CTX

%% =====================================================
%% OUTPUT CONNECTIONS
%% =====================================================

HMI --> CLUSTER["Instrument Cluster / HUD"]

ISA --> POWERTRAIN["Vehicle Control Functions"]

DIAG --> SERVICE["Service Tool"]

LOG --> CLOUD["Telematics / OTA Backend"]

classDef source fill:#EAF7F2,stroke:#14866D,color:#0F4C3F,stroke-width:2px;
classDef feature fill:#EDF3FF,stroke:#2F66D0,color:#173B7A,stroke-width:2px;
classDef temporal fill:#F4ECFF,stroke:#7C3AED,color:#4C1D95,stroke-width:2px;
classDef integration fill:#E8F7EE,stroke:#1E8E5A,color:#14532D,stroke-width:2px;
class CAM,MAP,SAS,ESC,CFG source;
class PRE,DET,CLS,CTX,LANE,FUSION feature;
class TRK,TMP,STATE temporal;
class HMI,ISA,DIAG,LOG,CLUSTER,POWERTRAIN,SERVICE,CLOUD integration;
```

---

# Component Description

| Component | Chức năng | Input | Output | Ví dụ |
|------------|------------|------------|------------|------------|
| Front Camera Module | Thu nhận hình ảnh phía trước xe | Road scene | Raw image frames | 1920×1080 RGB image |
| Navigation / HD Map | Cung cấp dữ liệu bản đồ và giới hạn tốc độ | GPS position | Map speed limit | 60 km/h |
| Steering Angle Sensor | Cung cấp góc đánh lái | Steering wheel movement | Steering angle | +12° |
| ESC / Vehicle Dynamics | Cung cấp trạng thái chuyển động xe | Wheel sensors | Vehicle speed, yaw rate | 58 km/h, 0.02 rad/s |
| Vehicle Configuration | Cấu hình thị trường và tính năng | Calibration data | Feature configuration | VN market profile |

---

# Perception Layer

## 1. Image Preprocessing

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Chuẩn hóa ảnh trước khi inference |
| Input | Raw camera image |
| Output | Processed image |
| Chức năng | Resize, normalize, color conversion, contrast enhancement |
| Ví dụ | RGB → BGR, CLAHE, resize 1280×720 |

### Giải thích

Đây là bước đầu tiên của pipeline TSR.

Mục tiêu là giảm ảnh hưởng của:
- Ánh sáng yếu
- Nhiễu cảm biến
- Chênh lệch độ tương phản

---

## 2. Traffic Sign Detection

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Tìm vị trí biển báo trong ảnh |
| Input | Processed image |
| Output | Bounding boxes |
| Chức năng | Object detection |
| Ví dụ | Speed Limit Sign tại (x=420,y=160,w=58,h=58) |

### Giải thích

Detection chỉ trả lời:

> Có biển báo ở đâu?

Chưa trả lời:

> Đó là biển báo gì?

---

## 3. Traffic Sign Classification

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Xác định loại biển báo |
| Input | ROI từ detector |
| Output | Sign class + confidence |
| Chức năng | Classification |
| Ví dụ | Speed Limit 60, confidence 0.94 |

### Giải thích

Classifier xác định:

- Stop
- Speed Limit 60
- Speed Limit 80
- No Entry
- Yield

---

## 4. Traffic Sign Tracking

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Theo dõi biển báo qua nhiều frame |
| Input | Detection results |
| Output | Track ID |
| Chức năng | Multi-frame association |
| Ví dụ | Track #25 tồn tại qua 15 frame |

### Giải thích

Tracking giúp:

- Giảm flicker
- Tăng stability
- Duy trì identity của biển báo

---

## 5. Temporal Confirmation

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Xác nhận biển báo theo thời gian |
| Input | Tracking history |
| Output | Confirmed sign |
| Chức năng | Temporal voting |
| Ví dụ | 8/10 frame đều nhận dạng Speed Limit 60 |

### Giải thích

Một detection duy nhất chưa đủ đáng tin.

Production TSR thường yêu cầu biển báo được quan sát trong nhiều frame liên tiếp trước khi kích hoạt.

---

# Feature Logic Layer

## 6. Context Filtering

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Loại bỏ biển báo không áp dụng |
| Input | Confirmed sign |
| Output | Relevant sign |
| Chức năng | Context reasoning |
| Ví dụ | Biển dành cho xe tải bị loại bỏ |

### Giải thích

Không phải mọi biển báo nhìn thấy đều áp dụng cho xe hiện tại.

Ví dụ:

- Truck Only
- Bus Lane
- Exit Ramp Speed Limit

---

## 7. Lane Association

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Xác định biển báo thuộc làn nào |
| Input | Sign position + lane geometry |
| Output | Lane-valid sign |
| Chức năng | Lane relevance evaluation |
| Ví dụ | Speed Limit chỉ áp dụng làn bên trái |

### Giải thích

Một biển báo có thể áp dụng cho:

- Làn hiện tại
- Làn kế bên
- Đường nhánh

TSR phải xác định chính xác phạm vi áp dụng.

---

## 8. Camera + Map Fusion

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Hợp nhất perception và map |
| Input | Camera sign + Map sign |
| Output | Fused sign |
| Chức năng | Sensor fusion |
| Ví dụ | Camera=60, Map=60 |

### Giải thích

Camera:

- Chính xác với thay đổi tạm thời

Map:

- Ổn định
- Có phạm vi phủ lớn

Fusion tận dụng ưu điểm của cả hai.

---

## 9. TSR State Manager

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Quản lý vòng đời biển báo |
| Input | Fused sign |
| Output | Active sign |
| Chức năng | State machine |
| Ví dụ | Speed Limit 60 vẫn còn hiệu lực |

### Giải thích

State Manager tránh hiện tượng:

- Sign xuất hiện rồi biến mất ngay
- Thay đổi liên tục giữa các giá trị tốc độ

---

# Vehicle Integration Layer

## 10. Cluster / HUD Output

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Hiển thị thông tin cho người lái |
| Input | Active sign |
| Output | HMI signal |
| Ví dụ | Hiển thị biển 60 km/h |

---

## 11. Intelligent Speed Assistance (ISA)

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Hỗ trợ tuân thủ giới hạn tốc độ |
| Input | Active speed limit |
| Output | Warning / control request |
| Ví dụ | Xe chạy 72 km/h trong vùng 60 km/h |

### Giải thích

ISA có thể:

- Cảnh báo
- Rung vô lăng
- Giới hạn ga
- Hỗ trợ giảm tốc

Tùy OEM và regulation.

---

## 12. Diagnostics

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Giám sát sức khỏe hệ thống |
| Input | Internal status |
| Output | DTC |
| Ví dụ | Camera timeout |

---

## 13. Data Logging

| Thuộc tính | Nội dung |
|------------|------------|
| Mục tiêu | Thu thập dữ liệu debug |
| Input | Runtime data |
| Output | Log package |
| Ví dụ | Video clip + metadata |

---

# End-to-End Signal Flow

```mermaid
sequenceDiagram

participant Camera
participant Detection
participant Tracking
participant Fusion
participant StateManager
participant Cluster
participant ISA

Camera->>Detection: Raw Image Frame

Detection->>Tracking: Sign Candidate

Tracking->>Fusion: Confirmed Sign

Fusion->>StateManager: Fused Speed Limit

StateManager->>Cluster: Display Active Sign

StateManager->>ISA: Active Speed Limit

ISA->>ISA: Compare Vehicle Speed

ISA-->>Driver: Warning if exceeded
```

---

# Ví dụ thực tế

| Bước | Giá trị |
|--------|--------|
| Camera phát hiện biển | Speed Limit 60 |
| Tracking xác nhận | 12 frame liên tiếp |
| Context Filtering | Hợp lệ với xe con |
| Lane Association | Thuộc làn hiện tại |
| Map Fusion | Map cũng báo 60 |
| State Manager | Active Speed Limit = 60 |
| Cluster | Hiển thị 60 km/h |
| ISA | Cảnh báo nếu vượt tốc độ |

Kết quả cuối cùng:

Người lái nhìn thấy biển giới hạn tốc độ 60 km/h trên HUD hoặc Instrument Cluster, đồng thời ISA có thể phát cảnh báo khi tốc độ xe vượt quá ngưỡng cho phép.
