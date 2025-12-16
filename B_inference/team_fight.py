import threading
import queue
import time
import cv2
import requests  # 👈 必須加入這個庫來傳送資料
import numpy as np
from flask import Flask, request, jsonify
from ultralytics import YOLO

# ===========================
# 1. 設定與初始化
# ===========================

# ⚠️ [請修改這裡] D 伺服器的網址
# 如果 D 是用 ngrok，請填入 ngrok 網址
# 如果 D 在內網，請填 http://192.168.xx.xx:8000/submit
D_SERVER_URL = "https://lateritious-angele-multicolored.ngrok-free.dev/submit"

# 設定本機組別 ID
TEAM_ID = "B"

# 模型路徑
MODEL_PATH = r"C:\Users\User\Desktop\yolo_web\models\support_frontline.pt"

app = Flask(__name__)

# 建立兩個佇列 (確保相機不當機)
request_queue = queue.Queue()
result_queue = queue.Queue()

print(f"⏳ 正在載入模型: {MODEL_PATH}")
try:
    model = YOLO(MODEL_PATH)
    print("✅ 模型載入完成！")
except Exception as e:
    print(f"❌ 模型載入失敗: {e}")
    exit()

# ===========================
# 2. Flask 路由 (背景執行)
# ===========================
@app.route('/scan_request', methods=['POST'])
def handle_scan():
    """接收 A (樹莓派) 的觸發指令"""
    data = request.json
    print(f"🔔 收到 A 端觸發: {data.get('name')} (UID: {data.get('uid')})")
    
    # 1. 把請求丟給主執行緒 (相機)
    request_queue.put(data)
    
    # 2. 等待主執行緒回傳結果 (設定 15 秒超時)
    try:
        result = result_queue.get(timeout=15)
        return jsonify(result)
    except queue.Empty:
        print("⚠️ 處理逾時")
        return jsonify({"success": False, "error": "Camera busy or timeout"}), 500

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# ===========================
# 3. 傳送資料給 D 的功能 (新增)
# ===========================
def send_to_d_server(user_name, label, conf):
    """將辨識結果發送給後端資料庫 D"""
    payload = {
        "team": TEAM_ID,
        "player": user_name,
        "item": label,
        "confidence": conf,
        "correct": 1 # 假設辨識正確
    }
    
    print(f"📤 [上傳中] 傳送給 D: {payload}")
    try:
        # timeout 設定短一點，避免網路卡住
        response = requests.post(D_SERVER_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print("✅ D 伺服器接收成功！")
        else:
            print(f"⚠️ D 伺服器回應錯誤: {response.status_code}")
    except Exception as e:
        print(f"❌ 無法連接 D 伺服器: {e}")

# ===========================
# 4. 主程式 (相機與推論)
# ===========================
def main():
    # 啟動 Flask
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    print("🚀 B 端伺服器已啟動 (Port 5000)")

    # 開啟相機
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("❌ 無法開啟相機！")
        return

    window_name = "B - Team Camera"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1)

    print("🎥 相機監控中... 等待 A 端刷卡...")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        # 檢查是否有請求
        if not request_queue.empty():
            req_data = request_queue.get()
            user_name = req_data.get('name', 'Unknown')
            
            print(f"⚡ [觸發] 開始辨識對象: {user_name}")

            # --- YOLO 推論 ---
            # 這裡把 conf 門檻降低到 0.35，解決「偵測不到」的問題
            results = model(frame, conf=0.35) 
            annotated_frame = results[0].plot()

            detections = []
            best_label = None
            best_conf = 0.0

            if results[0].boxes is not None:
                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    label = model.names[cls_id]
                    conf = float(box.conf[0])
                    
                    # 記錄所有偵測到的物件
                    detections.append({
                        "label": label,
                        "confidence": round(conf, 2)
                    })

                    # 找出信心度最高的那個傳給 D
                    if conf > best_conf:
                        best_conf = conf
                        best_label = label

            # --- 關鍵：發送給 D ---
            if best_label:
                # 開一個新執行緒去寄信，才不會卡住畫面
                threading.Thread(target=send_to_d_server, 
                               args=(user_name, best_label, round(best_conf, 2))).start()
            else:
                print("⚠️ 本次未偵測到任何物件 (Confidence < 0.35)")

            # --- 顯示結果畫面 3 秒 ---
            display_text = f"User: {user_name} | Found: {best_label if best_label else 'None'}"
            cv2.putText(annotated_frame, display_text, 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            start_time = time.time()
            while time.time() - start_time < 3:
                cv2.imshow(window_name, annotated_frame)
                cv2.waitKey(10)

            # --- 回傳給 A ---
            response_data = {
                "success": True,
                "triggered_by": user_name,
                "detections": detections
            }
            result_queue.put(response_data)
            print("✅ 流程結束，回復監控")

        else:
            # 平常只顯示畫面
            cv2.imshow(window_name, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()