import cv2
import requests
import base64
import json
import time

# =======================
# ★★★ 改這裡 ★★★
# =======================
INFERENCE_SERVER = "http://172.20.10.12:5000"
SCORE_URL = "https://lateritious-angele-multicolored.ngrok-free.dev/submit"
TEAM_ID = "A"
CONFIDENCE_THRESHOLD = 0.5
STABLE_FRAMES = 2
NOOBJ_FRAMES = 10

# 開啟攝影機
pipeline = (
        'libcamerasrc ! '
        'video/x-raw,width=640,height=480,framerate=30/1 ! '
        'videoconvert ! '
        'video/x-raw,format=BGR ! appsink'
    )
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
#cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ 無法開啟攝影機！")
    exit(1)

# 穩定邏輯的狀態變數
candidate_label = None
candidate_count = 0
stable_label = None
none_count = 0
last_sent = None
frame_count = 0

print("📷 A 端（樹莓派）攝影機啟動中...")
print(f"🖥️ 推論伺服器：{INFERENCE_SERVER}")
print(f"🔗 排名伺服器：{SCORE_URL}")
print("⚠️ 按 Ctrl+C 退出")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ 無法讀取影像")
            break

        frame_count += 1

        # 每 5 幀進行一次推論
        if frame_count % 5 == 0:
            print(f"\n📸 第 {frame_count} 幀 - 發送給 B 進行推論...")

            try:
                # 編碼影像
                _, img_buffer = cv2.imencode('.jpg', frame)
                img_base64 = base64.b64encode(img_buffer).decode('utf-8')

                # 發送給 B 的推論伺服器
                payload = {
                    "image": img_base64
                }

                response = requests.post(
                    f"{INFERENCE_SERVER}/inference",
                    json=payload,
                    timeout=10
                )

                if response.status_code != 200:
                    print(f"⚠️ 推論伺服器返回狀態碼 {response.status_code}")
                    none_count += 1
                    continue

                result = response.json()

                if not result.get('success'):
                    print(f"⚠️ 推論失敗：{result.get('error')}")
                    none_count += 1
                    continue

                # 處理推論結果
                top_detection = result.get('top_detection')

                if top_detection is None:
                    print("⚠️ 未檢測到物體")
                    none_count += 1
                else:
                    label_now = top_detection['label']
                    conf_now = top_detection['confidence']

                    print(f"✅ 檢測到：{label_now} (信心度: {conf_now})")

                    none_count = 0

                    # 穩定邏輯
                    if label_now == candidate_label:
                        candidate_count += 1
                    else:
                        candidate_label = label_now
                        candidate_count = 1

                    if candidate_count >= STABLE_FRAMES:
                        stable_label = candidate_label

                    # 發送到 D
                    if stable_label is not None and stable_label != last_sent:
                        payload_d = {
                            "team": TEAM_ID,
                            "item": stable_label,
                            "correct": 1,
                            "confidence": conf_now
                        }

                        try:
                            res_d = requests.post(SCORE_URL, json=payload_d, timeout=5)
                            if res_d.status_code == 200:
                                print(f"📨 送到 D 成功：{stable_label}")
                                last_sent = stable_label
                            else:
                                print(f"⚠️ D 返回狀態碼 {res_d.status_code}")
                        except Exception as e:
                            print(f"❌ 送到 D 失敗：{e}")

            except requests.exceptions.ConnectionError:
                print(f"❌ 無法連接到推論伺服器")
                print(f"   檢查 URL 是否正確：{INFERENCE_SERVER}")
                none_count += 1

            except requests.exceptions.Timeout:
                print("⏱️ 推論超時")
                none_count += 1

            except Exception as e:
                print(f"❌ 推論出錯：{e}")
                none_count += 1

        # 穩定邏輯：沒有檢測
        if none_count >= NOOBJ_FRAMES:
            stable_label = None
            candidate_label = None
            candidate_count = 0
            last_sent = None

        # ⭐ 沒有視窗顯示，樹莓派不需要
        # cv2.imshow() 和 cv2.waitKey() 都移除了

        time.sleep(0.03)  # 約 30 FPS

except KeyboardInterrupt:
    print("\n⏹️ 程式被中斷")

finally:
    print("🧹 清理資源...")
    cap.release()
    # cv2.destroyAllWindows() # 沒有視窗所以不需要
    print("✅ 程式結束")
