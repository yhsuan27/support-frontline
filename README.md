# 支援前線 YOLO 物體偵測遊戲系統

> 「支援前線」是一個分散式物體偵測遊戲系統，整合樹莓派相機模組、YOLO 深度學習模型、RFID 磁扣識別，支援**兩組對抗**及**組內對抗**兩種遊戲模式。

---

**主要特色：**
- ✅ 實時 YOLO 物體偵測推論
- ✅ RFID 磁扣觸發推論機制
- ✅ 支援遠端相機推論（跨機器通信）
- ✅ 即時排名顯示與數據持久化
- ✅ 雙模式遊戲切換

---

## 🏗️ 系統架構

### 模式 1：兩組對抗

```
       A 組                          B 組
        │                            │
        ▼                            ▼
    A 端樹莓派                    B 端 Windows
      相機拍照                      相機拍照
        │                            │
        │                            │
        └────────┬───────────────────┘
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

**特點：** A、B 兩組各自拍照並將影像傳送給 B 端推論伺服器進行 YOLO 推論，推論結果回傳後分別提交分數到 D 伺服器進行排名比較

---

### 模式 2：組內對抗

```
       Alice             Bob              Charlie
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

**特點：** 同組成員透過 RFID 磁扣觸發共用相機進行推論，競爭組內排名

---

## 👥 團隊角色分工

| 姓名 | 角色 | 設備 | 功能 | 主要責任 |
|------|------|------|------|---------|
| 范值均 | **A** | 樹莓派 | 相機擷取 | 攝影 + 回傳影像 |
| 葉諭玹 | **B** | Windows | 推論伺服器 + 辨識 | 遠端推論計算 |
| 范值均 | **C** | 樹莓派 | RFID 磁扣讀取 | 身份識別 + 觸發 |
| 李宣影 | **D** | Linux | 分數伺服器 + 資料庫 | 數據管理 + 計分 |
| 蘇家軍 | **E** | 網頁 | 排名顯示與監控 | 前端 UI + 即時更新 |

---

## 📁 專案結構

```
support-frontline/
├── README.md
│
├── A_camera/                    # 相機端
│   ├── client_cam_A.py
│   ├── 2_group.py
│   ├── requirements.txt
│   └── README.md
│
├── B_inference/                 # 推論伺服器
│   ├── inference_server.py
│   ├── team_fight.py
│   ├── support_frontline.pt
│   ├── requirements.txt
│   └── README.md
│
├── C_rfid/                      # RFID 讀取
│   ├── uid_list.json
│   ├── Intra_group.py
│   ├── ID_data.txt
│   └── README.md
│
├── D_server/                    # 伺服器端
│   ├── score_server.py
│   ├── requirements.txt
│   └── README.md
│
└── E_web/                       # 網頁前端
    ├── index.html
    ├── app.js
    ├── style.css
    └── README.md
```

---

## 🔧 遇到的挑戰

### 1. 跨網段連線問題
* **問題**：Server 架在虛擬機，無法直接透過內網 IP 連線。
* **解決**：使用 **ngrok** 內網穿透技術，在 Server 端執行 `ngrok http 8000`，產生公開 URL（如 `https://xxxx.ngrok-free.app`），讓所有 Client 端突破網段限制，成功建立連線。

### 2. 網頁跨域請求被擋
* **問題**：前端網頁（`index.html`）直接開啟（file://）去呼叫 Server API 時，瀏覽器基於安全性會擋下跨域請求（CORS）。
* **解決**：安裝 **flask-cors** 套件（`pip install flask-cors`），在 Server 程式（`score_server.py`）中引入 `CORS(app)`，允許跨來源資源共用，讓網頁能順利撈取即時排名資料。

### 3. 跨平台檔案同步效率低
* **問題**：Windows 開發環境與 Linux 伺服器之間需手動複製程式碼，導致除錯效率低落。
* **解決**：在 Linux 伺服器上架設 **Samba 檔案伺服器**，讓 Windows 端可透過網路芳鄰直接存取 Linux 專案目錄，修改後立即生效，大幅提升團隊協作效率。配置範例：

---

## 🛠️ 技術與工具

### 後端 
- **Python + Flask**
- **SQLite**
- **ngrok**
- **flask-cors**

### 物體偵測
- **YOLO (Ultralytics)**：實時物體偵測模型
- **OpenCV**：影像處理與相機操作

### 前端 Frontend
- **HTML / CSS / JavaScript**
- **Chart.js**
- **Fetch API**

### 硬體整合 
- **樹莓派 (Raspberry Pi)**
- **PiCamera2**
- **MFRC522**
---

## 🚀 未來展望

- 擴充訓練資料集，提升 YOLO 模型在複雜場景下的辨識精準度
- 調整模型超參數（confidence threshold、IoU threshold）減少誤判
- 引入資料增強技術量化模型（如 YOLOv5n），減少推論延遲
- 新增即時影像預覽功能，讓玩家確認偵測結果
- 支援多人同時對戰，擴展遊戲模式
- 將伺服器部署至雲端平台（AWS/GCP），提升系統穩定性
- 使用 Docker 容器化部署，簡化環境配置流程

---

## 📖 詳細文檔

- [A 相機程式說明](A_camera/README.md)
- [B 推論伺服器說明](B_inference/README.md)
- [C RFID 程式說明](C_rfid/README.md)
- [D 伺服器說明](D_server/README.md)
- [E 網頁說明](E_web/README.md)

---

## 📄 授權

MIT License

---

## 👨‍💼 貢獻者

- **A** - 相機擷取與推論
- **B** - YOLO 推論伺服器
- **C** - RFID 磁扣識別
- **D** - 後端伺服器與資料庫
- **E** - 網頁前端與數據可視化

---

<div align="center">

⭐ 如果覺得有幫助，請給個 Star！

Made with ❤️ by Your Team

</div>
