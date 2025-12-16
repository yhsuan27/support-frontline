from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

# ===========================
# 1. 系統設定
# ===========================
DB_PATH = "scores.db"
app = Flask(__name__)
CORS(app) # 允許跨域存取

# 全域變數
CURRENT_MISSION = "Any"
MISSION_START_TIME = None  # [新增] 記錄任務開始的時間 (Server 時間為準)

# ===========================
# 2. 物品分類對照表
# ===========================
CATEGORY_MAP = {
    "tableware": ["bottle", "cup", "mug", "bowl", "plate", "lunchbox", "chopsticks", "spoon", "fork"],
    "food": ["snack", "candy", "bread", "fruit", "instant_noodles"],
    "stationery": ["tissue", "paper", "notebook", "book", "pen", "pencil", "marker", "eraser", "ruler", "pencil_case", "stapler", "tape"],
    "electronic": ["cellphone", "laptop", "mouse", "keyboard", "charger", "earphone", "power_bank", "microphone"],
    "personal": ["backpack", "wallet", "key", "id_card", "watch", "glasses", "mask", "umbrella", "coat", "hat", "towel", "lipstick", "accessory"],
    "money": ["coin", "banknote"]
}

# ===========================
# 3. 資料庫初始化
# ===========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 建立分數表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        team TEXT,
        player TEXT,
        item TEXT,
        correct INTEGER,
        confidence REAL,
        created_at TEXT
    )
    """)
    
    # 建立場次表
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        started_at TEXT,
        ended_at TEXT,
        status TEXT DEFAULT 'active'
    )
    """)
    
    conn.commit()
    
    # 檢查是否有活躍場次
    cur.execute("SELECT id FROM sessions WHERE status='active'")
    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO sessions (name, started_at, status) VALUES (?, ?, ?)",
            (f"第 1 場", datetime.now().isoformat(), "active")
        )
        conn.commit()
    
    conn.close()

init_db()

def get_current_session():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM sessions WHERE status='active' ORDER BY id DESC LIMIT 1")
    result = cur.fetchone()
    conn.close()
    if result:
        return {"id": result[0], "name": result[1]}
    return None

# ===========================
# 4. API 路由設定
# ===========================

# --- [題目] 設定當前任務 ---
@app.route("/set_mission", methods=["POST"])
def set_mission():
    global CURRENT_MISSION, MISSION_START_TIME
    data = request.json
    
    CURRENT_MISSION = data.get("mission", "Any")
    # [關鍵修改] 記錄當下時間 (含毫秒)，這就是所有人的「起跑槍響」時間
    MISSION_START_TIME = datetime.now().isoformat()
    
    print(f"👉 題目更新: {CURRENT_MISSION}, Start Time: {MISSION_START_TIME}")
    return jsonify({
        "status": "ok", 
        "mission": CURRENT_MISSION, 
        "start_time": MISSION_START_TIME
    })

# --- [題目] 取得當前任務 ---
@app.route("/get_mission", methods=["GET"])
def get_mission():
    # 前端需要知道 start_time 才能計算經過秒數
    return jsonify({
        "mission": CURRENT_MISSION, 
        "start_time": MISSION_START_TIME
    })

# --- [核心] 接收辨識結果並計分 ---
@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True) or {}
    team = data.get("team")
    player = data.get("player", "Unknown")
    item = data.get("item")
    confidence = float(data.get("confidence", 0.0))
    correct = 1
    
    if not team or not item:
        return jsonify({"error": "missing data"}), 400
    
    session = get_current_session()
    if not session:
        return jsonify({"error": "no active session"}), 400

    # === 判斷邏輯 ===
    is_match = False
    if CURRENT_MISSION == "Any":
        is_match = True
    elif CURRENT_MISSION == item:
        is_match = True
    elif CURRENT_MISSION in CATEGORY_MAP and item in CATEGORY_MAP[CURRENT_MISSION]:
        is_match = True
    
    if not is_match:
        print(f"⚠️ 忽略: {player} ({item}) 不符合 {CURRENT_MISSION}")
        return jsonify({"status": "ignored", "reason": "item mismatch", "mission": CURRENT_MISSION})

    # === 寫入資料庫 ===
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # [關鍵修改] 使用預設的 isoformat() 包含毫秒，確保精確度
    now_iso = datetime.now().isoformat()
    
    cur.execute(
        "INSERT INTO scores (session_id, team, player, item, correct, confidence, created_at) VALUES (?,?,?,?,?,?,?)",
        (session["id"], team, player, item, correct, confidence, now_iso)
    )
    conn.commit()
    conn.close()
    
    print(f"✅ 得分: {player} ({team}) -> {item}")
    return jsonify({"status": "ok", "team": team, "item": item})

# --- [查詢] 取得分數紀錄 ---
@app.route("/scores", methods=["GET"])
def scores():
    session = get_current_session()
    if not session: return jsonify([])
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    SELECT team, player, correct, item, created_at
    FROM scores WHERE session_id = ? ORDER BY id DESC
    """, (session["id"],))
    rows = cur.fetchall()
    conn.close()
    
    result = [
        {"team": r[0], "player": r[1], "score": r[2], "item": r[3], "time": r[4]} 
        for r in rows
    ]
    return jsonify(result)

# --- [控制] 重置比賽 ---
@app.route("/new_session", methods=["POST"])
def new_session():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE sessions SET status='finished', ended_at=? WHERE status='active'", (datetime.now().isoformat(),))
        
        cur.execute("SELECT COUNT(*) FROM sessions")
        count = cur.fetchone()[0]
        new_name = f"第 {count + 1} 場"
        
        cur.execute("INSERT INTO sessions (name, started_at, status) VALUES (?, ?, ?)", (new_name, datetime.now().isoformat(), "active"))
        conn.commit()
        conn.close()
        
        # 重置全域變數
        global MISSION_START_TIME
        MISSION_START_TIME = None
        
        return jsonify({"status": "ok", "message": f"已開始 {new_name}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- [歷史] 查詢紀錄 ---
@app.route("/sessions", methods=["GET"])
def list_sessions():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, name, started_at, ended_at, status FROM sessions ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return jsonify([{"id":r[0], "name":r[1], "started_at":r[2], "status":r[4]} for r in rows])

@app.route("/scores/<int:session_id>", methods=["GET"])
def scores_by_session(session_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sessions WHERE id=?", (session_id,))
    s_name = cur.fetchone()[0]
    cur.execute("SELECT team, player, item, created_at FROM scores WHERE session_id=? ORDER BY id DESC", (session_id,))
    rows = cur.fetchall()
    conn.close()
    return jsonify({"session_name": s_name, "scores": [{"team":r[0], "player":r[1], "item":r[2], "time":r[3]} for r in rows]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)