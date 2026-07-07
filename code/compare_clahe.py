import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO("models/best.pt")
cap = cv2.VideoCapture("videos/test.mp4")

def apply_clahe(frame):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

print("Frame | Normal Conf | CLAHE Conf")
print("-" * 35)

frame_idx = 0
while frame_idx < 30:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    
    # 1. Normal frame
    res_normal = model(frame, conf=0.01, verbose=False)[0]
    conf_normal = 0.0
    for box in res_normal.boxes:
        if int(box.cls[0]) == 22: # Traffic light ahead
            conf_normal = max(conf_normal, float(box.conf[0]))
            
    # 2. CLAHE frame
    frame_clahe = apply_clahe(frame)
    res_clahe = model(frame_clahe, conf=0.01, verbose=False)[0]
    conf_clahe = 0.0
    for box in res_clahe.boxes:
        if int(box.cls[0]) == 22:
            conf_clahe = max(conf_clahe, float(box.conf[0]))
            
    print(f"{frame_idx:5d} | {conf_normal:11.4f} | {conf_clahe:10.4f}")

cap.release()
