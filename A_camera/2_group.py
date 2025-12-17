import board
import busio
import threading
import sys
import json
import os
import time
import requests
from adafruit_pn532.i2c import PN532_I2C

# ====================
# ⚙️ 配置區域 (請依照實際情況修改)
# ====================

# [修改後] B 端電腦 IP
B_SERVER_IP = "172.20.10.12"
B_SERVER_PORT = 5000
B_ENDPOINT = "/scan_request"

# 組合完整的 URL
B_TRIGGER_URL = f"http://{B_SERVER_IP}:{B_SERVER_PORT}{B_ENDPOINT}"

# 檔案名稱設定
TEAM_CONFIG_FILE = "uid_group.json"   # ← 修改後
UID_FILE = "uid_list.json"

# ====================
# 📂 檔案讀取功能
# ====================

def load_uid_map():
    if not os.path.exists(UID_FILE):
        with open(UID_FILE, "w", encoding="utf-8") as f:
            f.write("{}")
        return {}
    with open(UID_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_uid_map(uid_map):
    with open(UID_FILE, "w", encoding="utf-8") as f:
        json.dump(uid_map, f, indent=4, ensure_ascii=False)

def load_team_config():
    default_config = {
        "Alice": "A",
        "Bob": "A",
        "Charlie": "A",
        "David": "B",
        "Eve": "B",
        "Frank": "B"
    }

    if not os.path.exists(TEAM_CONFIG_FILE):
        with open(TEAM_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        return default_config

    with open(TEAM_CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except:
            return default_config

UID_MAP = load_uid_map()
TEAM_CONFIG = load_team_config()

# ====================
# 📡 初始化 PN532
# ====================
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    pn532 = PN532_I2C(i2c, debug=False)
    pn532.SAM_configuration()
except Exception as e:
    print(f"❌ 無法初始化 PN532: {e}")
    sys.exit(1)

latest_uid = None
waiting_for_name = False
pending_uid = None

# ====================
# ⌨️ 背景輸入監聽
# ====================

def input_listener():
    global waiting_for_name, pending_uid

    while True:
        try:
            user_input = input().strip()

            if user_input.lower() == "exit":
                print("Exiting program...")
                os._exit(0)

            if waiting_for_name and pending_uid:
                name = user_input
                if name == "":
                    print(f"🚫 未為 {pending_uid} 命名 -> 保持 Unknown")
                else:
                    UID_MAP[pending_uid] = name
                    save_uid_map(UID_MAP)
                    print(f"💾 已儲存新磁扣：{pending_uid} -> {name}")

                    if name not in TEAM_CONFIG:
                        TEAM_CONFIG[name] = "A"
                        print(f"   (暫時自動分配 {name} 到 A 組，請檢查 {TEAM_CONFIG_FILE})")

                waiting_for_name = False
                pending_uid = None
                print("--- 繼續偵測 ---")

        except EOFError:
            pass

threading.Thread(target=input_listener, daemon=True).start()

# ====================
# 📝 寫入 Log
# ====================

def write_log(name, team):
    with open("log.txt", "a", encoding="utf-8") as f:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        f.write(f"{ts} - {name} ({team})\n")

# ====================
# 🚀 發送觸發信號給 B
# ====================

def trigger_b_inference(uid, name, team):
    try:
        payload = {
            "uid": uid,
            "name": name,
            "team": team,
            "action": "trigger_camera"
        }

        print(f"📡 正在傳送請求給 B: {B_TRIGGER_URL} ...")
        response = requests.post(B_TRIGGER_URL, json=payload, timeout=5)

        if response.status_code == 200:
            print("✅ B 端回應成功！")
            try:
                data = response.json()
                print(f"🎯 B 端偵測結果: {data.get('detections', '無資料')}")
            except:
                print(f"📄 B 回應: {response.text}")
        else:
            print(f"⚠️ B 返回狀態碼: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到 B 端！")
        print(f"   請檢查: B 是否執行 / IP ({B_SERVER_IP}) 是否正確 / 防火牆")
    except requests.exceptions.Timeout:
        print("⏱️ 連線 B 超時")
    except Exception as e:
        print(f"❌ 觸發失敗: {e}")

# ====================
# 🏁 主程式
# ====================

print("\n" + "=" * 40)
print("📡 C 端 RFID 讀取器啟動完成")
print(f"🔗 目標 B 端位址：{B_TRIGGER_URL}")
print(f"📋 目前已知人員：{list(TEAM_CONFIG.keys())}")
print("👉 請刷卡 (輸入 'exit' 結束程式)")
print("=" * 40 + "\n")

while True:
    try:
        uid = pn532.read_passive_target(timeout=0.5)

        if uid is not None:
            uid_str = "-".join([hex(i) for i in uid])

            if uid_str != latest_uid:
                latest_uid = uid_str
                print(f"\n🔍 偵測到 UID: {uid_str}")

                if uid_str in UID_MAP:
                    name = UID_MAP[uid_str]

                    if name in TEAM_CONFIG:
                        team = TEAM_CONFIG[name]
                        print(f"👤 識別身分: {name} | 組別: {team}")

                        write_log(name, team)
                        trigger_b_inference(uid_str, name, team)
                    else:
                        print(f"⚠️ {name} 未在 {TEAM_CONFIG_FILE} 中設定組別")

                else:
                    print("❓ 未知磁扣！")
                    if not waiting_for_name:
                        print("⌨️ 請輸入此磁扣對應的人名 (Enter 跳過)")
                        pending_uid = uid_str
                        waiting_for_name = True

            time.sleep(1)

        else:
            latest_uid = None

    except RuntimeError as e:
        print(f"⚠️ PN532 讀取錯誤: {e}")
        time.sleep(0.1)

    except KeyboardInterrupt:
        print("程式結束")
        break
