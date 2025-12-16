# 支援前線 YOLO 物體偵測遊戲系統

> 🎮 基於 YOLO 的實時互動遊戲系統

<div align="center">

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Status](https://img.shields.io/badge/Status-Completed-brightgreen.svg)

**[查看演示](#-遊戲演示) • [快速開始](#-快速開始) • [架構說明](#-系統架構)**

</div>

---

## 📸 遊戲演示

### 遊戲排名介面
![遊戲排名介面](docs/images/game_interface.png)

### 硬體設置
![硬體設置](docs/images/system_setup.jpg)

### 系統架構圖
![系統架構](docs/images/architecture_diagram.png)

---

## 📋 專案概述

「支援前線」是一個分散式物體偵測遊戲系統，整合樹莓派相機模組、YOLO 深度學習模型、RFID 磁扣識別，支援**兩組對抗**及**組內對抗**兩種遊戲模式。

**主要特色：**
- ✅ 實時 YOLO 物體偵測推論
- ✅ RFID 磁扣觸發推論機制
- ✅ 支援遠端相機推論（跨機器通信）
- ✅ 即時排名顯示與數據持久化
- ✅ 雙模式遊戲切換

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                      支援前線遊戲系統                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐     ┌──────────────┐   ┌──────────────┐   │
│  │   A 端       │     │   B 端       │   │   C 端       │   │
│  │  樹莓派      │     │  Windows     │   │  樹莓派      │   │
│  │  相機模組    │────▶│  推論伺服器  │◀──│ RFID讀取器   │   │
│  └──────────────┘     └──────────────┘   └──────────────┘   │
│         │                     │                    │          │
│         └─────────────────────┼────────────────────┘          │
│                               ▼                               │
│                     ┌──────────────────┐                      │
│                     │   D 端           │                      │
│                     │  Linux 伺服器    │                      │
│                     │  Flask + ngrok   │                      │
│                     └──────────────────┘                      │
│                               │                               │
│                               ▼                               │
│                     ┌──────────────────┐                      │
│                     │   E 端           │                      │
│                     │  網頁顯示排名    │                      │
│                     │  Chart.js 圖表   │                      │
│                     └──────────────────┘                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 👥 團隊角色分工

| 角色 | 設備 | 功能 | 主要責任 |
|------|------|------|---------|
| **A** | 樹莓派 | 相機擷取 + 推論 | 攝影 + 即時推論 |
| **B** | Windows | 推論伺服器 | 遠端推論計算 |
| **C** | 樹莓派 | RFID 磁扣讀取 | 身份識別 + 觸發 |
| **D** | Linux | 分數伺服器 + 資料庫 | 數據管理 + 計分 |
| **E** | 網頁 | 排名顯示與監控 | 前端 UI + 即時更新 |

---

## 🎮 遊戲模式

### 模式 1：兩組對抗
```
A 組                        B 組
  │                          │
  ▼                          ▼
自己推論                  自己推論
  │                          │
  └──────────┬───────────────┘
             ▼
          D 伺服器計分
             ▼
          實時排名比較
```

**特點：** 各組獨立運作，即時對比分數

---

### 模式 2：組內對抗
```
中央相機（共用）
  △
  │
  │ 磁扣觸發
  │
┌─┴─────────────────┐
│                   │
Alice (A組)    Bob (A組)    Charlie (A組)
   │               │              │
   └───────┬───────┴──────────────┘
           ▼
      組別計分統計
```

**特點：** 同組成員輪流推論，競爭組內排名

---

## 🚀 快速開始

### 安裝步驟

**1. Clone 專案**
```bash
git clone https://github.com/你的用戶名/support-frontline.git
cd support-frontline
```

**2. D 端伺服器啟動**
```bash
cd D_server
pip install -r requirements.txt
python score_server.py
```

**3. B 端推論伺服器啟動**
```bash
cd B_inference
pip install -r requirements.txt

# 兩組對抗模式
python inference_server.py

# 或組內對抗模式
python inference_server_team.py
```

**4. A 端相機程式啟動**
```bash
cd A_camera
pip install -r requirements.txt

# 兩組對抗模式
python3 client_cam_A.py

# 或組內對抗模式
python3 client_cam_A_team.py
```

**5. C 端 RFID 程式啟動**
```bash
cd C_rfid
pip install -r requirements.txt
python3 c_rfid_reader.py
```

**6. E 端網頁打開**
```bash
# 用瀏覽器打開
E_web/index.html
```

---

## ⚙️ 關鍵配置

### A 端 - 修改 B 的 IP
```python
# client_cam_A.py 或 client_cam_A_team.py
B_INFERENCE_SERVER = "http://192.168.x.x:5000"  # 改成 B 的真實 IP
```

### C 端 - 修改觸發 URL
```python
# c_rfid_reader.py
B_TRIGGER_URL = "http://192.168.x.x:5002/trigger"
```

### E 端 - 修改 D 的 ngrok 網址
```javascript
// app.js
const API_URL = "https://你的ngrok網址/scores";
```

---

## 📊 數據流程

### 兩組對抗模式
```
┌─────────────────┐
│  A 拍照推論     │
└────────┬────────┘
         │
    發送結果到 D
         │
         ▼
┌─────────────────┐
│  D 計分+儲存    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  E 查詢+顯示    │
└─────────────────┘
```

### 組內對抗模式
```
┌─────────────────┐
│  C 掃磁扣       │
│  觸發 B 推論    │
└────────┬────────┘
         │
┌────────▼────────┐
│  A 拍照         │
│  B 推論         │
└────────┬────────┘
         │
    發送結果到 D
         │
         ▼
┌─────────────────┐
│  D 計分+儲存    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  E 查詢+顯示    │
└─────────────────┘
```

---

## 📁 專案結構

```
support-frontline/
├── README.md
├── .gitignore
│
├── D_server/                    # 伺服器端
│   ├── score_server.py
│   ├── requirements.txt
│   └── README.md
│
├── B_inference/                 # 推論伺服器
│   ├── inference_server.py
│   ├── inference_server_team.py
│   ├── best.pt
│   ├── requirements.txt
│   └── README.md
│
├── A_camera/                    # 相機端
│   ├── client_cam_A.py
│   ├── client_cam_A_team.py
│   ├── requirements.txt
│   └── README.md
│
├── C_rfid/                      # RFID 讀取
│   ├── c_rfid_reader.py
│   ├── uid_list.json
│   ├── team_config.json
│   ├── requirements.txt
│   └── README.md
│
├── E_web/                       # 網頁前端
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── README.md
│
└── docs/
    ├── images/
    │   ├── game_interface.png
    │   ├── system_setup.jpg
    │   └── architecture_diagram.png
    ├── 架構說明.md
    ├── 安裝指南.md
    └── 遊戲規則.md
```

---

## 🔌 API 端點

### D 伺服器

**POST /submit** - 提交分數
```json
{
  "team": "A",
  "item": "person",
  "correct": 1,
  "confidence": 0.95
}
```

**GET /scores** - 查詢排名
```json
[
  {"team": "B", "score": 15, "total": 15},
  {"team": "A", "score": 10, "total": 10}
]
```

### B 推論伺服器

**POST /inference** - 推論
```json
{
  "image": "base64編碼的影像"
}
```

**POST /trigger** - 觸發推論（組內對抗）
```json
{
  "name": "Alice",
  "team": "A"
}
```

---

## 📖 詳細文檔

- [D 伺服器說明](D_server/README.md)
- [B 推論伺服器說明](B_inference/README.md)
- [A 相機程式說明](A_camera/README.md)
- [C RFID 程式說明](C_rfid/README.md)
- [E 網頁說明](E_web/README.md)

---

## 🔧 故障排除

| 問題 | 解決方案 |
|------|---------|
| A 無法連接 B | 檢查 B 的 IP，修改 A 的設定 |
| RFID 無法讀取 | 樹莓派執行 `raspi-config` 啟用 I2C |
| 網頁顯示 404 | 重啟 ngrok，更新 E 的 URL |
| 推論很慢 | 用 B 的遠端推論代替本地推論 |

---

## 📄 授權

MIT License - 詳見 [LICENSE](LICENSE) 檔案

---

## 👨‍💼 貢獻者

- **A** - 范植鈞 - 相機擷取與推論
- **B** - 葉諭玹 - YOLO 推論伺服器
- **C** - 范植鈞 - RFID 磁扣識別
- **D** - 李宣穎 - 後端伺服器與資料庫
- **E** - 蘇嘉鈞 - 網頁前端與數據可視化

