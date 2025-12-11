// ⚠️ 請修改為您 D 端 (ngrok) 的網址
const API_BASE_URL = "https://lateritious-angele-multicolored.ngrok-free.dev";

// 全域變數
let currentMode = 'team'; // 當前模式: 'team' (團體) 或 'individual' (個人)
let rawData = [];         // 存放從 Server 抓回來的所有原始資料
let missionStartTime = null; // 任務開始時間 (由 Server 統一控制，毫秒)

// Chart.js 圖表初始化
let ctx = document.getElementById("chart").getContext("2d");
let chart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: [],
        datasets: [{
            label: '積分',
            data: [],
            borderWidth: 1,
            backgroundColor: [
                'rgba(255, 99, 132, 0.7)', // 紅
                'rgba(54, 162, 235, 0.7)', // 藍
                'rgba(255, 206, 86, 0.7)', // 黃
                'rgba(75, 192, 192, 0.7)', // 綠
                'rgba(153, 102, 255, 0.7)', // 紫
                'rgba(255, 159, 64, 0.7)'  // 橘
            ],
            borderColor: [
                'rgba(255, 99, 132, 1)',
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(153, 102, 255, 1)',
                'rgba(255, 159, 64, 1)'
            ]
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            y: {
                beginAtZero: true,
                ticks: { stepSize: 1 } // 設定刻度為整數
            }
        },
        plugins: {
            legend: { display: false } // 隱藏圖例
        }
    }
});

// ==========================================
// 1. 任務與時間控制 (API)
// ==========================================

// 設定新題目 (主持人按下按鈕)
async function setMission() {
    let mission = document.getElementById("missionSelect").value;
    try {
        let res = await fetch(`${API_BASE_URL}/set_mission`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'ngrok-skip-browser-warning': 'true'
            },
            body: JSON.stringify({ mission: mission })
        });
        
        if(res.ok) {
            let data = await res.json();
            // 立即更新前端的時間與題目
            if (data.start_time) {
                missionStartTime = new Date(data.start_time).getTime();
            }
            fetchMission(); // 更新 UI文字
            
            // 清空戰況顯示，顯示「計時開始」
            document.getElementById("battleLog").innerHTML = '<div class="empty-log">🚀 題目已更新，計時開始！</div>';
            
            // 立即重整數據
            fetchResults(); 
        } else {
            alert("❌ 設定失敗");
        }
    } catch (e) {
        alert("❌ 無法連接伺服器，請檢查 URL");
        console.error(e);
    }
}

// 從 Server 取得當前題目與時間狀態 (同步用)
async function fetchMission() {
    try {
        let res = await fetch(`${API_BASE_URL}/get_mission`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        let data = await res.json();
        
        // 同步 Server 時間 (轉換為毫秒 timestamp)
        if (data.start_time) {
            missionStartTime = new Date(data.start_time).getTime();
        } else {
            missionStartTime = null;
        }

        // 物品名稱中文化對照表
        let displayMap = {
            "Any": "✨ 自由模式 (什麼都加分)",
            // 餐具
            "bottle": "🍾 瓶子", "cup": "🥤 杯子", "mug": "🍺 馬克杯", "bowl": "🥣 碗", "plate": "🍽️ 盤子",
            "lunchbox": "🍱 便當盒", "chopsticks": "🥢 筷子", "spoon": "🥄 湯匙", "fork": "🍴 叉子",
            // 食物
            "snack": "🍟 零食", "candy": "🍬 糖果", "bread": "🍞 麵包", "fruit": "🍎 水果", "instant_noodles": "🍜 泡麵",
            // 文具
            "tissue": "🧻 衛生紙", "paper": "📄 紙張", "notebook": "📓 筆記本", "book": "📖 書籍",
            "pen": "🖊️ 原子筆", "pencil": "✏️ 鉛筆", "marker": "🖍️ 麥克筆", "eraser": "🧼 橡皮擦", "ruler": "📏 尺",
            "pencil_case": "👝 鉛筆盒", "stapler": "📎 釘書機", "tape": "🎞️ 膠帶",
            // 電子
            "cellphone": "📱 手機", "laptop": "💻 筆電", "mouse": "🖱️ 滑鼠", "keyboard": "⌨️ 鍵盤",
            "charger": "🔌 充電器", "earphone": "🎧 耳機", "power_bank": "🔋 行動電源", "microphone": "🎤 麥克風",
            // 個人
            "backpack": "🎒 背包", "wallet": "👛 錢包", "key": "🔑 鑰匙", "id_card": "🪪 識別證",
            "watch": "⌚ 手錶", "glasses": "👓 眼鏡", "mask": "😷 口罩", "umbrella": "☂️ 雨傘",
            "coat": "🧥 外套", "hat": "🧢 帽子", "towel": "🧣 毛巾", "lipstick": "💄 口紅", "accessory": "💍 飾品",
            // 金錢
            "coin": "🪙 硬幣", "banknote": "💵 紙鈔"
        };
        
        let missionText = displayMap[data.mission] || data.mission;
        document.getElementById("currentMissionDisplay").innerText = missionText;
        
        // 避免下拉選單一直跳回 Server 值，只有當值不同時才更新
        if(document.getElementById("missionSelect").value !== data.mission) {
             document.getElementById("missionSelect").value = data.mission;
        }
            
    } catch (e) {
        console.error("無法取得題目", e);
    }
}

// ==========================================
// 2. 資料獲取與處理 (核心邏輯)
// ==========================================

// 切換 團體/個人 賽制
function switchMode(mode) {
    currentMode = mode;
    // 更新按鈕樣式
    document.getElementById('btnTeam').className = mode === 'team' ? 'switch-btn active' : 'switch-btn';
    document.getElementById('btnIndividual').className = mode === 'individual' ? 'switch-btn active' : 'switch-btn';
    // 重新渲染畫面
    processAndRender();
}

// 從 Server 抓取分數紀錄
async function fetchResults() {
    try {
        let res = await fetch(`${API_BASE_URL}/scores`, {
            headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        if (!res.ok) throw new Error("連線錯誤");
        
        let text = await res.text();
        // 簡單防止 ngrok 回傳錯誤網頁
        if (text.trim().startsWith('<')) throw new Error("API 回傳 HTML (可能是 ngrok 錯誤頁面)");
        
        rawData = JSON.parse(text); // 儲存全域資料
        processAndRender(); // 呼叫渲染函式
        
        // 更新狀態列
        let now = new Date();
        let statusEl = document.getElementById("status");
        statusEl.innerText = `✅ 連線正常 (更新於 ${now.toLocaleTimeString()})`;
        statusEl.style.color = "#155724";
        statusEl.style.background = "#d4edda";

    } catch (error) {
        let statusEl = document.getElementById("status");
        statusEl.innerText = `❌ 連線失敗: ${error.message}`;
        statusEl.style.color = "#721c24";
        statusEl.style.background = "#f8d7da";
    }
}

// 處理資料並呼叫渲染
function processAndRender() {
    let rankingData = [];
    let currentRoundScores = []; // 專門存放「本局」的戰況

    let items = {}; // 暫存物件: { "TeamA": {score: 5, count: 2...} }

    rawData.forEach(record => {
        // 根據模式決定 Key 是 Team Name 還是 Player Name
        let key = currentMode === 'team' ? (record.team || "未知") : (record.player || "未知");
        if(key === "Unknown") return;

        // 統計總分
        if (!items[key]) {
            items[key] = { name: key, score: 0, count: 0, team: record.team };
        }
        items[key].score += (record.score || 1);
        items[key].count += 1;

        // === [關鍵邏輯] 判斷是否為「本局」得分 (用來算秒數) ===
        // 只有當 Server 有設定時間，且該紀錄的時間在設定時間之後
        if (missionStartTime && record.time) {
            let scoreTime = new Date(record.time).getTime();
            
            // 允許 1 秒寬容值 (Tolerance)，避免 Server 寫入延遲或微小誤差
            if (scoreTime >= (missionStartTime - 1000)) {
                currentRoundScores.push({
                    name: key, // 顯示名稱
                    scoreTime: scoreTime, // 得分時間 (毫秒)
                    item: record.item // 物品名稱
                });
            }
        }
    });

    // 將暫存物件轉為陣列並排序 (分數高 -> 低)
    rankingData = Object.values(items);
    rankingData.sort((a, b) => b.score - a.score);
    
    // 1. 渲染排行榜表格
    renderTable(rankingData);
    // 2. 更新長條圖
    updateChart(rankingData);
    // 3. 渲染戰況速報
    renderBattleLog(currentRoundScores);
}

// ==========================================
// 3. UI 渲染函式
// ==========================================

// 渲染戰況速報 (Battle Feed)
function renderBattleLog(scores) {
    let logContainer = document.getElementById("battleLog");
    
    // 如果還沒設定題目
    if (!missionStartTime) {
        logContainer.innerHTML = '<div class="empty-log">請先設定題目以開始計時</div>';
        return;
    }
    
    // 如果本局還沒人得分
    if (scores.length === 0) {
        logContainer.innerHTML = '<div class="empty-log">⏳ 計時中... 選手請準備...</div>';
        return;
    }

    // 依時間排序：時間小的 (越早完成的) 排前面
    scores.sort((a, b) => a.scoreTime - b.scoreTime);

    let html = "";
    let firstTime = scores[0].scoreTime; // 第一名的時間

    scores.forEach((s, index) => {
        // 計算耗時 (秒)
        // scoreTime - missionStartTime = 經過毫秒數
        // Math.max(0, ...) 避免因為時鐘誤差出現負數
        let duration = Math.max(0, (s.scoreTime - missionStartTime) / 1000);
        let durationStr = duration.toFixed(2); // 取小數點兩位 (例如 3.52)

        // 計算與第一名的差距
        let diff = (s.scoreTime - firstTime) / 1000;
        
        // 顯示文字與樣式設定
        let diffHtml = "";
        let rankClass = "rank-2"; // 預設樣式
        let badge = "";

        if (index === 0) {
            // 第一名
            diffHtml = "👑 Winner";
            rankClass = "rank-1"; // 金牌樣式
            badge = `<span class="badge-first">TOP 1</span>`;
        } else {
            // 後面的名次
            diffHtml = `<span style="color: #e53e3e; font-weight: bold;">+${diff.toFixed(2)} 秒</span>`;
        }

        // 產生 HTML
        html += `
            <div class="battle-card ${rankClass}">
                <div class="battle-info">
                    <strong>${s.name} ${badge}</strong>
                    <small>成功辨識：${s.item}</small>
                </div>
                <div class="battle-time">
                    <div class="seconds">${durationStr}s</div>
                    <span class="time-diff">${diffHtml}</span>
                </div>
            </div>
        `;
    });

    logContainer.innerHTML = html;
}

// 渲染總分表格
function renderTable(data) {
    let html = `<table><thead><tr><th>排名</th><th>名稱</th><th>總分</th><th>成功次數</th></tr></thead><tbody>`;
    
    if (data.length === 0) {
        html += "<tr><td colspan='4' style='color:#999'>尚無資料</td></tr>";
    } else {
        data.forEach((r, index) => {
            // 前三名用獎牌符號
            let medal = ['🥇','🥈','🥉'][index] || (index + 1);
            html += `
                <tr>
                    <td>${medal}</td>
                    <td style="font-weight:bold">${r.name}</td>
                    <td style="color:#e53e3e; font-weight:bold; font-size:1.1em">${r.score}</td>
                    <td>${r.count}</td>
                </tr>`;
        });
    }
    html += "</tbody></table>";
    document.getElementById("ranking").innerHTML = html;
}

// 更新圖表
function updateChart(data) {
    chart.data.labels = data.map(d => d.name);
    chart.data.datasets[0].data = data.map(d => d.score);
    chart.update();
}

// ==========================================
// 4. 事件監聽與排程
// ==========================================

// 重置比賽按鈕
document.getElementById("newSessionBtn").addEventListener("click", async () => {
    if(!confirm("確定要重置比賽嗎？\n這將會歸零所有分數並開始新的一場。")) return;
    
    await fetch(`${API_BASE_URL}/new_session`, { 
        method: 'POST', 
        headers: {'ngrok-skip-browser-warning': 'true'} 
    });
    
    // 清空前端狀態
    document.getElementById("battleLog").innerHTML = '<div class="empty-log">比賽已重置</div>';
    fetchResults();
    fetchMission();
});

// 歷史紀錄按鈕邏輯
document.getElementById("historyBtn").addEventListener("click", () => {
    document.getElementById("historyModal").style.display = "block";
    loadHistory();
});

async function loadHistory() {
    try {
        let res = await fetch(`${API_BASE_URL}/sessions`, { headers: {'ngrok-skip-browser-warning': 'true'} });
        let sessions = await res.json();
        let html = "";
        sessions.forEach(s => {
            let statusText = s.status === 'active' ? '🟢進行中' : '⚫已結束';
            // 點擊可以查看該場次的詳細分數 (這裡只做簡單顯示，若有需要可擴充)
            html += `
                <div class="session-item" style="padding:10px; border-bottom:1px solid #eee;">
                    <div><strong>${s.name}</strong> <small>${statusText}</small></div>
                    <small style="color:#666">${s.started_at.replace('T', ' ')}</small>
                </div>`;
        });
        document.getElementById("historyList").innerHTML = html;
    } catch (e) {
        document.getElementById("historyList").innerHTML = "無法載入紀錄";
    }
}

// 關閉 Modal
document.querySelector(".close").addEventListener("click", () => { 
    document.getElementById("historyModal").style.display = "none"; 
});
window.onclick = (event) => { 
    if (event.target == document.getElementById("historyModal")) {
        document.getElementById("historyModal").style.display = "none";
    }
};

// ==========================================
// 5. 啟動定時器
// ==========================================

// 每 2 秒抓一次最新分數
setInterval(fetchResults, 2000);

// 每 3 秒確認一次目前題目 (確保大家題目同步)
setInterval(fetchMission, 3000);

// 初次載入
fetchResults();
fetchMission();