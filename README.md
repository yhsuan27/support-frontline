# 支援前線 YOLO 物體偵測遊戲系統

「支援前線」是一個分散式物體偵測遊戲系統，整合樹莓派相機模組、YOLO 深度學習模型、RFID 磁扣識別，支援**兩組對抗**及**組內對抗**兩種遊戲模式。玩家透過尋找指定物品進行競賽，系統即時計分並顯示排名，創造緊張刺激的競技體驗。

**主要特色：**
- YOLO 物體偵測推論
- RFID 磁扣觸發推論機制
- 支援遠端相機推論
- 即時排名顯示與數據持久化
- 雙模式遊戲切換

---

## 🏗️ 系統架構

### 模式 1：兩組對抗

```
       A 組                          B 組
        │                             │
        ▼                             ▼
    A 端樹莓派                    B 端 Windows
      相機拍照                      相機拍照
        │                             │
        │                             │
        └────────┬────────────────────┘
                 │
                 │  傳送影像給推論伺服器
                 │  
                 ▼
           B 端推論伺服器
           (YOLO 模型推論)
                 │
                 │  回傳偵測結果
                 ▼
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
     A 組結果          B 組結果
        │                 │
        │                 │
        └────────┬────────┘
                 ▼
             D 端伺服器
          (Flask + SQLite)
             計分與排名
                 │
                 │  
                 ▼
            E 端網頁介面
            即時排名比較
```


**遊戲流程：** 
1. A、B 兩組各自啟動相機程式
2. 系統指定待偵測物品（如 cellphone、bottle）
3. 玩家尋找物品並拍照
4. 影像傳送至 B 端推論伺服器進行 YOLO 推論
5. 推論結果回傳，系統判定是否正確
6. 分數即時提交至 D 端伺服器並更新排名
7. E 端網頁即時顯示兩組分數與排名變化


---

### 模式 2：組內對抗

```
      Alice              Bob              Charlie
      (A 組)            (A 組)             (A 組)
        │                 │                  │
        ▼                 ▼                  ▼
      掃磁扣             掃磁扣             掃磁扣
        │                 │                  │
        └────────┬────────┴──────────────────┘
                 │
                 │  
                 │  
                 ▼
           C 端 RFID 讀取器
             (身份識別)
                 │
                 │  觸發推論請求
                 │
                 ▼
           B 端推論伺服器
                 │
                 │  等待影像
                 │  
                 ▼
           A 端樹莓派相機
            (拍照並回傳)
                 │
                 │  
                 ▼
           B 端推論伺服器
           (YOLO 模型推論)
                 │
                 │ 
                 ▼
             D 端伺服器
          (Flask + SQLite)
             記錄個人分數
                 │
                 │ 
                 ▼
           E 端網頁介面
           組內排名與統計
```

**遊戲流程：** 
1. 組員使用 RFID 磁扣識別身份
2. C 端讀取 UID 並觸發 B 端推論伺服器
3. B 端向 A 端相機請求影像
4. A 端拍照並回傳 base64 編碼影像
5. B 端執行 YOLO 推論並判定結果
6. 個人分數提交至 D 端伺服器
7. E 端網頁顯示組內個人排名與統計

---

## 📁 專案結構

```
support-frontline/
├── README.md
│
├── A_camera/                    # 樹梅派相機端
│   ├── client_cam_A.py
│   └── requirements.txt
│   
│
├── B_inference/                 # 推論伺服器
│   ├── inference_server.py
│   ├── team_fight.py
│   ├── support_frontline.pt
│   └── requirements.txt
│  
│
├── C_rfid/                      # RFID 讀取
│   ├── uid_list.json
│   ├── Intra_group.py
│   └── uid_group.json
│   
│
├── D_server/                    # 伺服器端
│   ├── score_server.py
│   └── requirements.txt
│   
│
└── E_web/                       # 網頁前端
    ├── index.html
    ├── app.js
    └── style.css
```
---
## 🤖 YOLO 模型訓練過程

本專案使用 YOLOv8 訓練自定義物體偵測模型，共識別 **49 種物品類別**。

### 訓練流程

**1. 環境準備**
```bash
# 建立虛擬環境
python -m venv venv
venv\Scripts\activate  

# 安裝必要套件
pip install ultralytics bing-image-downloader opencv-python
```

**2. 從網路下載訓練影像**
- 使用 `bing-image-downloader` 自動從網路下載各類別影像
- 每類下載 50 張照片
- 自動儲存至 `images/` 資料夾

```python
from bing_image_downloader import downloader

categories = ['person', 'bicycle', 'car', 'bottle', 'laptop', ...]  # 49 種類別
for category in categories:
    downloader.download(category, limit=50, output_dir='images')
```

**3. 使用預訓練模型自動標註**
- 載入 YOLOv8 預訓練模型（`yolov8n.pt`）
- 自動對下載的影像進行物體偵測並生成標註檔

```python
from ultralytics import YOLO
model = YOLO('yolov8n.pt')

# 自動標註影像
results = model(img_path)
# 產生 YOLO 格式標註檔 (.txt)
```

**4. 資料集準備**
```
dataset/
├── images/        
│   ├── train/     # 訓練影像 (80%)
│   └── val/       # 驗證影像 (20%)
└── labels/          
    ├── train/     # 訓練標註檔
    └── val/       # 驗證標註檔
```

**5. 設定配置檔 (data.yaml)**
```yaml
train: ./dataset/images/train
val: ./dataset/images/val
nc: 49  # 49 種類別
names: [person, bicycle, car, motorcycle, airplane, bus, ...]
```

**6. 開始訓練**
```bash
# 訓練模型
yolo detect train model=yolov8n.pt data=data.yaml epochs=50 imgsz=640 batch=16

# 訓練過程會自動儲存至 runs/detect/train/
```

**7. 訓練成果**
- **訓練時間**：約 13-15 小時（使用 GPU）
- **最終模型**：`support_frontline.pt`
- 可即時透過相機辨識 49 種物品並框選標示

---


## 🔧 遇到的挑戰

### 1. 跨網段連線問題
* **問題**：Server 架在虛擬機，無法直接透過內網 IP 連線。
* **解決**：使用 **ngrok** 內網穿透技術，在 Server 端執行 `ngrok http 8000`，產生公開 URL（如 `https://xxxx.ngrok-free.app`），讓所有 Client 端突破網段限制，成功建立連線。

### 2. 網頁跨域請求被擋
* **問題**：前端網頁（`index.html`）直接開啟（file://）去呼叫 Server API 時，瀏覽器基於安全性會擋下跨域請求（CORS）。
* **解決**：安裝 **flask-cors** 套件，在 Server 程式（`score_server.py`）中引入 `CORS(app)`，允許跨來源資源共用，讓網頁能順利撈取即時排名資料。

### 3. 跨平台檔案同步效率低
* **問題**：Windows 開發環境與 Linux 伺服器之間需手動複製程式碼，導致除錯效率低落。
* **解決**：在 Linux 伺服器上架設 **Samba 檔案伺服器**，讓 Windows 端可透過網路芳鄰直接存取 Linux 專案目錄，修改後立即生效，提升團隊協作效率。

---

## 🛠️ 技術與工具

### 後端 
- **Python + Flask**
- **SQLite**
- **ngrok**
- **flask-cors**

### 物體偵測
- **YOLO**
- **OpenCV**

### 前端 Frontend
- **HTML / CSS / JavaScript**
- **Chart.js**
- **Fetch API**

### 硬體整合 
- **樹莓派 (Raspberry Pi3)**
- **PiCamera V1**
- **PN532 NFC RFID**
---

## 🚀 未來展望

- 擴充訓練資料集，提升 YOLO 模型辨識精準度降低誤判
- 新增即時影像預覽功能，讓玩家確認偵測結果
- 支援多人同時對戰，擴展遊戲模式
- 將伺服器部署至雲端平台（AWS/GCP），提升系統穩定性
- 使用 Docker 容器化部署，簡化環境配置流程

---

## 👥 團隊角色分工

| 姓名 | 角色 | 設備 | 功能 | 主要責任 |
|------|------|------|------|---------|
| 范植鈞 | **A** | 樹莓派 | 相機擷取 | 攝影 + 回傳影像 |
| 葉諭玹 | **B** | Windows | 推論伺服器 + 拍照辨識 | 訓練模型 + 遠端推論計算 |
| 范植鈞 | **C** | 樹莓派 | RFID 磁扣讀取 | 身份識別 + 觸發 |
| 李宣穎 | **D** | Linux | 分數伺服器 + 資料庫 | 數據管理 + 計分 |
| 蘇嘉鈞 | **E** | 網頁 | 排名顯示與監控 | 前端 UI + 即時更新 |


