import cv2
from ultralytics import YOLO

model = YOLO("models/best.pt")
cap = cv2.VideoCapture("videos/test.mp4")

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    
    # Run YOLO inference
    results = model(frame, conf=0.01, verbose=False)[0] # Set confidence low to see what it predicts
    
    dets = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        cls_name = model.names[cls_id]
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        dets.append((cls_name, conf, (x1, y1, x2, y2)))
        
    if len(dets) > 0:
        # Print detections if we find Traffic light ahead or multiple signs
        has_traffic_light_ahead = any("Traffic light" in d[0] for d in dets)
        if has_traffic_light_ahead or len(dets) > 1:
            print(f"Frame {frame_idx}: {dets}")

cap.release()
