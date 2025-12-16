import threading
from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2
import base64
import numpy as np

MODEL_PATH = "best.pt"
model = YOLO(r"C:\Users\User\Desktop\yolo_web\models\support_frontline.pt")

app = Flask(__name__)

# ========== B 自己的推論（主執行緒）==========
NGROK_URL = "https://lateritious-angele-multicolored.ngrok-free.dev/submit"
TEAM_ID = "B"

cap = cv2.VideoCapture(0)

def run_b_inference():
    """B 自己的實時推論"""
    print("📷 B 端推論執行緒啟動...")
    
    candidate_label = None
    candidate_count = 0
    stable_label = None
    none_count = 0
    last_sent = None
    STABLE_FRAMES = 10
    NOOBJ_FRAMES = 15
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # B 的推論
        results = model(frame, conf=0.5, verbose=False)
        r = results[0]
        
        label_now = None
        conf_now = 0
        if r.boxes is not None and len(r.boxes) > 0:
            idx = r.boxes.conf.argmax().item()
            cls_id = int(r.boxes.cls[idx])
            label_now = model.names[cls_id]
            conf_now = float(r.boxes.conf[idx])
            none_count = 0
        else:
            none_count += 1
        
        # 穩定邏輯
        if label_now is not None:
            if label_now == candidate_label:
                candidate_count += 1
            else:
                candidate_label = label_now
                candidate_count = 1
            
            if candidate_count >= STABLE_FRAMES:
                stable_label = candidate_label
        else:
            if none_count >= NOOBJ_FRAMES:
                stable_label = None
                candidate_label = None
                candidate_count = 0
                last_sent = None
        
        # 發送到 D
        if stable_label is not None and stable_label != last_sent:
            import requests
            payload = {
                "team": TEAM_ID,
                "item": stable_label,
                "correct": 1,
                "confidence": conf_now
            }
            try:
                requests.post(NGROK_URL, json=payload, timeout=3)
                print(f"📨 B 送出：{stable_label}")
                last_sent = stable_label
            except:
                pass
        
        cv2.imshow("B - YOLO Live", r.plot())
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# ========== A 的推論請求（Flask 伺服器）==========
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    return response

@app.route('/inference', methods=['POST'])
def inference():
    """A 發送的推論請求"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return {"success": False, "error": "缺少 image"}, 400
        
        # 解碼影像
        image_data = base64.b64decode(data['image'])
        image_array = np.frombuffer(image_data, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            return {"success": False, "error": "無法解碼"}, 400
        
        # A 的推論
        results = model(frame, conf=0.5, verbose=False)
        r = results[0]
        
        detections = []
        top_detection = None
        max_conf = 0
        
        if r.boxes is not None and len(r.boxes) > 0:
            for box in r.boxes:
                conf = float(box.conf)
                cls_id = int(box.cls)
                label = model.names[cls_id]
                
                detection = {
                    "label": label,
                    "confidence": round(conf, 3)
                }
                detections.append(detection)
                
                if conf > max_conf:
                    max_conf = conf
                    top_detection = detection
        
        return {
            "success": True,
            "detections": detections,
            "top_detection": top_detection
        }, 200
    
    except Exception as e:
        return {"success": False, "error": str(e)}, 500

@app.route('/health', methods=['GET'])
def health():
    return {"status": "ok"}, 200

if __name__ == "__main__":
    # 啟動 B 的推論執行緒
    b_thread = threading.Thread(target=run_b_inference, daemon=True)
    b_thread.start()
    
    # 啟動 Flask 伺服器（處理 A 的請求）
    print("🚀 啟動推論伺服器...")
    app.run(host="0.0.0.0", port=5000, debug=False)