import cv2
import requests
import base64
import time

# ====================
# 配置 - 組內對抗模式
# ====================
B_INFERENCE_SERVER = "http://127.0.0.1:5002"  # ← 組內對抗用埠 5002
SCORE_URL = "https://lateritious-angele-multicolored.ngrok-free.dev/submit"
TEAM_ID = "A"
IMAGE_SIZE = 320

# 開啟攝影機
pipeline = (
        'libcamerasrc ! '
        'video/x-raw,width=640,height=480,framerate=30/1 ! '
        'videoconvert ! '
        'video/x-raw,format=BGR ! appsink'
    )
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("❌ 無法開啟攝影機！")
    exit(1)

# 推論狀態
inference_enabled = False
current_person = None
current_team = None
frame_count = 0
last_check_time = 0
CHECK_INTERVAL = 0.5  # 每 0.5 秒檢查一次推論狀態

print("📷 A 端（樹莓派）攝影機啟動中...")
print(f"🖥️  B 的推論伺服器：{B_INFERENCE_SERVER}")
print(f"🔗 排名伺服器：{SCORE_URL}")
print("💡 等待 C 掃磁扣觸發推論...")
print("⚠️  按 'q' 或 ESC 退出")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 無法讀取影像")
            break

        frame_count += 1
        current_time = time.time()

        # ====================
        # 每 0.5 秒檢查一次推論狀態
        # ====================
        if current_time - last_check_time > CHECK_INTERVAL:
            last_check_time = current_time

            try:
                health_response = requests.get(
                    f"{B_INFERENCE_SERVER}/health",
                    timeout=2,
                    headers={'ngrok-skip-browser-warning': 'true'}
                )

                if health_response.status_code == 200:
                    health_data = health_response.json()
                    inference_enabled = health_data.get("inference_active", False)
                    current_person = health_data.get("current_person")
                    current_team = health_data.get("current_team")

                    if inference_enabled and current_person:
                        print(f"🔔 推論已觸發：{current_person} ({current_team} 組)")

            except Exception:
                pass  # 靜默失敗，不中斷推論

        # ====================
        # 只有當推論被觸發才拍照發送
        # ====================
        if not inference_enabled:
            print("⏳ 等待觸發...", end="\r")
            time.sleep(0.05)
            continue

        # ====================
        # 推論被觸發：拍照並發送給 B
        # ====================
        if frame_count % 5 == 0:  # 每 5 幀發送一次（減少網路負擔）
            print(f"📸 第 {frame_count} 幀 - 發送照片給 B 進行推論...", end="\r")

            try:
                # 編碼影像
                _, img_buffer = cv2.imencode('.jpg', frame)
                img_base64 = base64.b64encode(img_buffer).decode('utf-8')

                payload = {"image": img_base64}

                # 發送給 B 的推論伺服器
                response = requests.post(
                    f"{B_INFERENCE_SERVER}/inference",
                    json=payload,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()

                    if result.get('success') and result.get('top_detection'):
                        top_detection = result['top_detection']
                        item = top_detection['label']
                        confidence = top_detection['confidence']
                        print(f"✅ 推論成功：{item} (信心度: {confidence})")

                elif response.status_code == 400:
                    reason = response.json().get('reason', '未知原因')
                    if reason == "inference not triggered":
                        inference_enabled = False

            except requests.exceptions.ConnectionError:
                print(f"❌ 無法連接到 B 的推論伺服器")
                print(f"   檢查 B 的 IP 地址是否正確：{B_INFERENCE_SERVER}")
                inference_enabled = False

            except requests.exceptions.Timeout:
                print("⏱️  B 的推論超時")

            except Exception as e:
                print(f"❌ 推論出錯：{e}")

        # 顯示影像（可選）
        # cv2.imshow("A - Camera Feed", frame)

        # 按 'q' 或 ESC 退出
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            print("\n⏹️ 使用者停止程式")
            break

        time.sleep(0.03)  # 約 30 FPS

except KeyboardInterrupt:
    print("\n⏹️ 程式被中斷")

finally:
    print("🧹 清理資源...")
    cap.release()
    # cv2.destroyAllWindows()
    print("✅ 程式結束")
