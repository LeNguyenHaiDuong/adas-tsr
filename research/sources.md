# Sources & Research Provenance — TSR

> **Thứ tự đọc:** 7 — appendix provenance, không phải narrative chính.  
> **File này trả lời:** các nhận định trong bộ research dựa trên nguồn nào.  
> **Ngoài phạm vi:** giải thích hệ thống TSR hay baseline repo; xem `1.research_tsr_three_part_unified.md`, `2.research_tsr_baseline_analysis.md`, `3.research_tsr_detection_architecture_research.md`, `4.research_tsr_colab_production_lite_demo.md`.

## 1. Nội bộ repo `adas-tsr`

- Script inference chính: `code/tsr_demo.py`
- **(0)** Brief đầu bài: [0.requirements.md](0.requirements.md)
- **(1)** Tài liệu tổng (3 phần): [1.research_tsr_three_part_unified.md](1.research_tsr_three_part_unified.md)
- **(2)** Baseline gắn code: [2.research_tsr_baseline_analysis.md](2.research_tsr_baseline_analysis.md)
- **(3)** Nghiên cứu kiến trúc detector + edge deployment: [3.research_tsr_detection_architecture_research.md](3.research_tsr_detection_architecture_research.md)
- **(4)** Notebook production-lite: [4.research_tsr_colab_production_lite_demo.md](4.research_tsr_colab_production_lite_demo.md)
- Visual appendix: [diagram.md](diagram.md)
- Slide deck dẫn xuất: [slide.md](slide.md)
- Notebook tái lập nhẹ: [notebooks/tsr_research_workflow.ipynb](notebooks/tsr_research_workflow.ipynb)
- Notebook Colab production-lite: [notebooks/tsr_colab_production_lite_demo.ipynb](notebooks/tsr_colab_production_lite_demo.ipynb)

## 2. Model và công cụ chính

- Ultralytics Predict Mode  
  https://docs.ultralytics.com/modes/predict/
- Ultralytics Export Mode  
  https://docs.ultralytics.com/modes/export/
- Ultralytics Benchmark Mode  
  https://docs.ultralytics.com/modes/benchmark/
- Hugging Face model card: `star092304/traffic-sign-detection-vietnam-yolo`  
  https://huggingface.co/star092304/traffic-sign-detection-vietnam-yolo

Ghi chú:

- Model card được dùng để xác nhận: họ model, số class, input size, benchmark tác giả, khả năng export ONNX.
- Ultralytics docs được dùng làm nguồn chính cho CLI/API inference và export runtime.

## 3. Dataset và benchmark công khai

- GTSRB (German Traffic Sign Recognition Benchmark)  
  http://benchmark.ini.rub.de/?section=gtsrb&subsection=dataset
- GTSDB (German Traffic Sign Detection Benchmark)  
  https://benchmark.ini.rub.de/?section=gtsdb&subsection=dataset
- TT100K (Tsinghua-Tencent 100K)  
  https://cg.cs.tsinghua.edu.cn/traffic-sign/
- Mapillary Traffic Sign Dataset  
  https://arxiv.org/abs/1909.04422
- TS-1M: Traffic Sign Recognition in Autonomous Driving  
  https://arxiv.org/abs/2603.23034
- LISA Traffic Sign Dataset  
  https://cvrr.ucsd.edu/LISA/lisa-traffic-sign-dataset.html
- GLARE: A Dataset for Traffic Sign Detection in Sun Glare  
  https://arxiv.org/abs/2209.08716
- CCTSDB-AUG related paper
  https://arxiv.org/abs/2309.06902

## 4. Nguồn cho ODD, state flow, requirements, và validation

- Setting AI in context: A case study on defining the context and operational design domain for automated driving  
  https://arxiv.org/abs/2201.11451
- Managing driving modes in automated driving systems  
  https://arxiv.org/abs/2107.00280
- Requirements Engineering for Automotive Perception Systems: an Interview Study  
  https://arxiv.org/abs/2302.12155
- Navigating Dimensionality through State Machines in Automotive System Validation  
  https://arxiv.org/abs/2408.10569

Ghi chú:

- Các nguồn này được dùng để củng cố phần ODD, driving modes, hệ thống state transition, và verification logic trong [1.research_tsr_three_part_unified.md](1.research_tsr_three_part_unified.md) (Phần I–II).

## 5. Nguồn cho safety, process, cybersecurity, và update governance

- ISO 26262-1:2018 vocabulary entry on ISO OBP  
  https://www.iso.org/obp/ui/#iso:std:iso:26262:-1:ed-2:v1:en
- ISO 26262 package overview  
  https://www.iso.org/publication/PUB200262.html
- Automotive SPICE official overview (VDA QMC)  
  https://vda-qmc.de/en/automotive-spice/
- ISO 21448:2022 official page  
  https://www.iso.org/cms/live/live/en/sites/isoorg/contents/data/standard/07/74/77490.html
- UNECE R155 official regulation document  
  https://unece.org/sites/default/files/2021-03/R155e.docx
- UNECE R156 official regulation document  
  https://unece.org/sites/default/files/2021-03/R156e.docx
- AUTOSAR Classic Platform official overview  
  https://www.autosar.org/standards/classic-platform/
- AUTOSAR organization and governance  
  https://www.autosar.org/about/organization
- NHTSA Driver Distraction Guidelines for In-Vehicle Electronic Devices  
  https://www.federalregister.gov/d/2012-4017
- Regulation (EU) 2019/2144 — General Safety Regulation
  https://eur-lex.europa.eu/eli/reg/2019/2144/oj
- Commission Delegated Regulation (EU) 2021/1958 — Intelligent Speed Assistance
  https://eur-lex.europa.eu/eli/reg_del/2021/1958/oj
- European Transport Safety Council — Intelligent Speed Assistance overview
  https://etsc.eu/intelligent-speed-assistance-isa/

Ghi chú:

- Các nguồn này được dùng như mốc tham chiếu cho các khái niệm: `fault/error/failure`, process capability, cybersecurity management, và software update governance.
- Các link `ISO`, `AUTOSAR`, `UNECE`, và `NHTSA` ở mục này là nguồn chuẩn hoặc nguồn chính thức được ưu tiên khi viết các phần liên quan safety, SOTIF, HMI, update governance.

## 6. Nguồn cho tracking, temporal confirmation, diagnostics, và map-assisted fusion

- SORT: Simple Online and Realtime Tracking  
  https://arxiv.org/abs/1602.00763
- Deep SORT: Simple Online and Realtime Tracking with a Deep Association Metric  
  https://arxiv.org/abs/1703.07402
- UDS overview  
  https://en.wikipedia.org/wiki/Unified_Diagnostic_Services
- MapFusion: A General Framework for 3D Object Detection with HDMaps  
  https://arxiv.org/abs/2103.05929
- Intelligent speed assistance overview  
  https://en.wikipedia.org/wiki/Intelligent_speed_assistance
- The Mapillary Traffic Sign Dataset for Detection and Classification on a Global Scale  
  https://arxiv.org/abs/1909.04422
- Organization of machine learning based product development as per ISO 26262 and ISO/PAS 21448  
  https://arxiv.org/abs/1910.05112

Ghi chú:

- Ở mục này, một số link overview như `UDS` và `Intelligent speed assistance` được dùng để diễn giải bối cảnh triển khai phổ biến trong ngành; chúng không thay thế tiêu chuẩn gốc khi đi vào release/compliance.

## 7. Nguồn cho taxonomy mô hình và xử lý ảnh

- Review. Machine learning techniques for traffic sign detection  
  https://arxiv.org/abs/1712.04391
- YOLO: Unified, Real-Time Object Detection  
  https://arxiv.org/abs/1506.02640
- Faster R-CNN  
  https://arxiv.org/abs/1506.01497
- SSD: Single Shot MultiBox Detector  
  https://arxiv.org/abs/1512.02325
- DETR: End-to-End Object Detection with Transformers  
  https://arxiv.org/abs/2005.12872
- RT-DETR: DETRs Beat YOLOs on Real-time Object Detection  
  https://arxiv.org/abs/2304.08069
- OpenCV Documentation  
  https://docs.opencv.org/
- TensorRT Documentation  
  https://docs.nvidia.com/deeplearning/tensorrt/
- ONNX Runtime Documentation  
  https://onnxruntime.ai/docs/
- OpenVINO Documentation
  https://docs.openvino.ai/

Ghi chú:

- Các nguồn trong mục này hỗ trợ [3.research_tsr_detection_architecture_research.md](3.research_tsr_detection_architecture_research.md) (small-object, edge, dataset) và [1.research_tsr_three_part_unified.md](1.research_tsr_three_part_unified.md) (ISA, SOTIF, fusion).

## 8. Nguồn cho KPI, dataset và ISA (cập nhật 2026-06-20)

- GTSRB official dataset page: http://benchmark.ini.rub.de/gtsrb_dataset.html
- GTSDB official dataset page: https://benchmark.ini.rub.de/gtsdb_dataset.html
- TT100K official page: https://cg.cs.tsinghua.edu.cn/traffic-sign/
- EU General Safety Regulation (EU) 2019/2144: https://eur-lex.europa.eu/eli/reg/2019/2144/oj
- EU ISA Delegated Regulation (EU) 2021/1958: https://eur-lex.europa.eu/eli/reg_del/2021/1958/oj
- InterRegs ISA timeline analysis: https://www.interregs.com/articles/spotlight/236/eu-regulation-on-intelligent-speed-assistance-systems-published-

Ghi chú:

- Số liệu dataset trong [3.research_tsr_detection_architecture_research.md](3.research_tsr_detection_architecture_research.md) §13.2 được đối chiếu với các trang chính thức trên.
- Timeline ISA (6 July 2022 new types; 7 July 2024 all new vehicles) theo phân tích InterRegs trích dẫn EU 2019/2144 — cần đối chiếu consolidated text khi làm compliance document chính thức.

## 9. Ghi chú provenance

- Các video output trong `videos/` là artefact runtime cục bộ phục vụ minh họa và kiểm tra thủ công.
- Repo giữ một notebook tái lập nhẹ cho local replay, nhưng không giữ các benchmark artifact nặng như JSON kết quả tạm hoặc notebook output lớn trong nhánh phát hành.
- Council Review Summary nằm ở [1.research_tsr_three_part_unified.md](1.research_tsr_three_part_unified.md) Phụ lục C.
