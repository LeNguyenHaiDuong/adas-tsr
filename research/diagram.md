# TSR System Architecture

> **Thứ tự đọc:** 5 — visual appendix sau `research/1...`.  
> **File này trả lời:** các block kiến trúc TSR nối với nhau như thế nào ở mức nhìn nhanh.  
> **Ngoài phạm vi:** giải thích dài về production mindset, gap baseline hay roadmap; các phần đó nằm ở `1.research_tsr_three_part_unified.md`.

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

Phần narrative đầy đủ của 3 lớp này đã nằm trong `research/1...`; file này chỉ giữ sơ đồ và glossary ngắn để tra nhanh.

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

## Glossary nhanh theo block

### Input sources

| Block | Vai trò ngắn | Xem chi tiết ở đâu |
|---|---|---|
| `Front Camera Module` | Nguồn ảnh chính cho perception | `research/1...` Phần I–II |
| `Navigation / HD Map` | Nguồn speed limit/map context bổ sung | `research/1...` Phần II |
| `Steering Angle Sensor` + `ESC / Vehicle Dynamics` | Hỗ trợ lane/context/applicability | `research/1...` Phần II |
| `Vehicle Configuration` | Profile thị trường, policy, cấu hình feature | `research/1...` Phần I |

### Perception Layer

| Block | Vai trò ngắn | Repo hiện tại |
|---|---|---|
| `Image Preprocessing` | Chuẩn hóa ảnh đầu vào trước inference | Có bản tối giản trong `tsr_demo.py` |
| `Traffic Sign Detection` | Tìm bbox biển báo | Có YOLO baseline `best.pt` |
| `Traffic Sign Classification` | Gán class và confidence | Đi kèm detector baseline |
| `Traffic Sign Tracking` | Nối cùng một biển qua nhiều frame | **Chưa có thật**; repo mới có `hold` |
| `Temporal Confirmation` | Chỉ confirm khi bằng chứng theo thời gian đủ mạnh | **Chưa có thật** trong runtime chính |

### Feature Logic Layer

| Block | Vai trò ngắn | Repo hiện tại |
|---|---|---|
| `Context Filtering` | Loại sign không phù hợp bối cảnh ego | Chưa có |
| `Lane Association` | Quyết định sign áp cho làn nào | Chưa có |
| `Camera + Map Fusion` | Hòa giải camera với map/route context | Chưa có |
| `TSR State Manager` | Quản lý lifecycle `CANDIDATE -> ACTIVE -> STALE -> EXPIRED` | Chưa có |

### Vehicle Integration Layer

| Block | Vai trò ngắn | Repo hiện tại |
|---|---|---|
| `Cluster / HUD Output` | Chính sách hiển thị cho người lái | Repo chỉ có video overlay |
| `Intelligent Speed Assistance (ISA)` | Client dùng speed limit đã canonicalize | Chưa có |
| `Diagnostics` | DTC, health monitoring, fault handling | Chưa có |
| `Data Logging` | Event log để replay, RCA, regression | Chưa có machine-readable output |

## Luồng tín hiệu tối giản

```mermaid
sequenceDiagram
participant Camera
participant Detection
participant Tracking
participant Fusion
participant StateManager
participant Cluster
participant ISA

Camera->>Detection: Raw image frame
Detection->>Tracking: Sign candidate
Tracking->>Fusion: Confirmed sign
Fusion->>StateManager: Fused/applicable sign
StateManager->>Cluster: Display policy
StateManager->>ISA: Active speed limit
ISA-->>Driver: Warning or assist
```

## Ví dụ 1 dòng signal flow

| Bước | Ví dụ |
|---|---|
| Camera | Nhìn thấy biển `Speed Limit 60` |
| Tracking + confirmation | Xác nhận cùng sign qua nhiều frame |
| Context + lane | Kết luận biển áp cho ego lane |
| Map fusion | Đối chiếu với map speed limit |
| State manager | Giữ `Active speed limit = 60` |
| HMI / ISA | Hiển thị `60` và cảnh báo nếu ego vượt ngưỡng |

## Khi nào nên mở file khác?

| Nếu bạn cần... | Hãy mở |
|---|---|
| Câu chuyện hệ thống đầy đủ và roadmap production | [1.research_tsr_three_part_unified.md](1.research_tsr_three_part_unified.md) |
| Gap implementation của repo hiện tại | [2.research_tsr_baseline_analysis.md](2.research_tsr_baseline_analysis.md) |
| Trade-off detector, small-object, edge deploy | [3.research_tsr_detection_architecture_research.md](3.research_tsr_detection_architecture_research.md) |
| Demo stateful replay trên Colab | [4.research_tsr_colab_production_lite_demo.md](4.research_tsr_colab_production_lite_demo.md) |
