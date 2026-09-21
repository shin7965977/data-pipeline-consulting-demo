import os
import subprocess

HTML_SLIDES = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>電商營運自動化與 AI 智慧決策方案 — 專案簡報</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=Noto+Sans+TC:wght@400;500;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --primary-light: #eff6ff;
            --accent: #f59e0b;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Plus Jakarta Sans', 'Noto Sans TC', sans-serif;
            background: #090d16;
            color: var(--text-main);
            overflow: hidden;
            height: 100vh;
            width: 100vw;
            display: flex;
            flex-direction: column;
            user-select: none;
        }

        /* Top Bar */
        .topbar {
            height: 56px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            z-index: 100;
        }
        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 800;
            font-size: 1.05rem;
            letter-spacing: -0.5px;
            color: #ffffff;
        }
        .brand-badge {
            background: linear-gradient(135deg, #2563eb, #3b82f6);
            color: #ffffff;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 6px;
            text-transform: uppercase;
        }
        .nav-controls {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .slide-counter {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 12px;
            border-radius: 20px;
            border: 1px solid var(--card-border);
        }
        .btn-nav {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid var(--card-border);
            color: #ffffff;
            padding: 6px 14px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .btn-nav:hover {
            background: var(--primary);
            border-color: var(--primary);
        }

        /* Slides Viewport */
        .deck-container {
            flex: 1;
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            background: radial-gradient(circle at 50% 20%, #1e293b 0%, #090d16 80%);
        }

        .slide {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            padding: 3rem 5rem 4.5rem 5rem;
            opacity: 0;
            pointer-events: none;
            transform: translateX(40px);
            transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            flex-direction: column;
            justify-content: center;
            max-width: 1400px;
            margin: 0 auto;
            right: 0;
        }

        .slide.active {
            opacity: 1;
            pointer-events: auto;
            transform: translateX(0);
        }

        /* Typography & Slide Elements */
        .category-tag {
            color: #60a5fa;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .action-title {
            font-size: 2.1rem;
            font-weight: 800;
            line-height: 1.25;
            color: #ffffff;
            margin-bottom: 0.75rem;
            letter-spacing: -0.5px;
        }
        .action-title span {
            background: linear-gradient(135deg, #60a5fa, #38bdf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .action-subtitle {
            font-size: 1.1rem;
            color: var(--text-muted);
            margin-bottom: 2rem;
            line-height: 1.5;
            max-width: 90%;
        }

        /* Grid Layouts */
        .grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 2rem;
        }
        .grid-4 {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1.25rem;
        }

        /* Cards */
        .card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.75rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .card:hover {
            border-color: rgba(96, 165, 250, 0.4);
            transform: translateY(-4px);
            box-shadow: 0 16px 32px rgba(0, 0, 0, 0.3);
        }
        .card-icon {
            font-size: 2rem;
            margin-bottom: 1rem;
            display: inline-block;
        }
        .card-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.5rem;
        }
        .card-desc {
            font-size: 0.925rem;
            color: var(--text-muted);
            line-height: 1.6;
        }
        .card-highlight {
            margin-top: 1rem;
            padding-top: 0.75rem;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
            font-size: 0.85rem;
            font-weight: 600;
            color: #38bdf8;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        /* Comparison Table / Box */
        .compare-box {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        .box-before {
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid rgba(239, 68, 68, 0.25);
            border-radius: 16px;
            padding: 1.75rem;
        }
        .box-after {
            background: rgba(16, 185, 129, 0.08);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 16px;
            padding: 1.75rem;
        }
        .box-head {
            font-size: 1.1rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 1.25rem;
        }
        .box-before .box-head { color: #f87171; }
        .box-after .box-head { color: #34d399; }
        .compare-item {
            display: flex;
            align-items: flex-start;
            gap: 10px;
            margin-bottom: 1rem;
            font-size: 0.95rem;
            line-height: 1.5;
        }
        .compare-item:last-child { margin-bottom: 0; }
        .bullet-red { color: #ef4444; font-weight: bold; }
        .bullet-green { color: #10b981; font-weight: bold; }

        /* Metric Highlights */
        .metric-big {
            font-size: 2.8rem;
            font-weight: 900;
            color: #ffffff;
            line-height: 1;
            margin-bottom: 0.25rem;
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: linear-gradient(135deg, #ffffff, #94a3b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .metric-highlight {
            background: linear-gradient(135deg, #38bdf8, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Roadmap Timeline */
        .timeline {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            position: relative;
        }
        .timeline-step {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            position: relative;
        }
        .step-badge {
            background: #2563eb;
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 800;
            padding: 3px 10px;
            border-radius: 20px;
            display: inline-block;
            margin-bottom: 0.75rem;
        }

        /* Bottom Controls / Dots */
        .bottom-nav {
            position: absolute;
            bottom: 1.25rem;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 0.5rem;
            z-index: 100;
        }
        .dot {
            width: 10px;
            height: 10px;
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.2);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .dot.active {
            width: 28px;
            background: #3b82f6;
        }

        /* Print / PDF Media query */
        @media print {
            body {
                background: #ffffff !important;
                color: #0f172a !important;
                overflow: visible !important;
                height: auto !important;
            }
            .topbar, .bottom-nav { display: none !important; }
            .deck-container {
                display: block !important;
                background: none !important;
            }
            .slide {
                position: relative !important;
                opacity: 1 !important;
                transform: none !important;
                page-break-after: always !important;
                height: 100vh !important;
                padding: 2.5rem 3rem !important;
                color: #0f172a !important;
            }
            .action-title { color: #0f172a !important; }
            .card {
                background: #f8fafc !important;
                border: 1px solid #cbd5e1 !important;
                color: #0f172a !important;
            }
            .card-title { color: #0f172a !important; }
            .metric-big { color: #0f172a !important; -webkit-text-fill-color: initial !important; }
            .action-subtitle { color: #475569 !important; }
            .card-desc { color: #475569 !important; }
        }
    </style>
</head>
<body>

    <!-- Top Navigation Bar -->
    <div class="topbar">
        <div class="brand">
            <span>⚡ Platzi Analytics & Copilot</span>
            <span class="brand-badge">SME Solution</span>
        </div>
        <div class="nav-controls">
            <span class="slide-counter" id="slideCounter">1 / 7</span>
            <button class="btn-nav" id="btnPrev">◀ 上一頁</button>
            <button class="btn-nav" id="btnNext" style="background: var(--primary);">下一頁 ▶</button>
            <button class="btn-nav" id="btnFullscreen">⛶ 全螢幕</button>
        </div>
    </div>

    <!-- Main Deck Container -->
    <div class="deck-container">

        <!-- SLIDE 1: COVER -->
        <div class="slide active" data-index="1">
            <div class="category-tag">🚀 專為中小電商老闆打造 · 數位升級解決方案</div>
            <h1 class="action-title" style="font-size: 3rem; margin-bottom: 1.25rem;">
                告別 Excel 搬磚與盲目救火<br>
                <span>自動化電商數據中台與 AI 營運軍師</span>
            </h1>
            <p class="action-subtitle" style="font-size: 1.25rem; max-width: 850px;">
                釋放 <strong>90% 人工對帳與拉表工時</strong> · 守住 <strong>8% 隱形退款與取消漏損</strong> · 讓數據像自動導航一樣，天天替您的電商業務即時看盤、主動診斷！
            </p>
            <div class="grid-3" style="margin-top: 1rem;">
                <div class="card">
                    <div class="metric-big metric-highlight">0 小時</div>
                    <div class="card-title">自動化資料同步</div>
                    <p class="card-desc">蝦皮、官網、POS 資料每晚自動整合，週一開機報表已就緒。</p>
                </div>
                <div class="card">
                    <div class="metric-big" style="color: #34d399; -webkit-text-fill-color: initial;">100% 真實</div>
                    <div class="card-title">看清實質淨利潤</div>
                    <p class="card-desc">自動扣除退款、取消與折價券，不再被虛假膨脹的 GMV 誤導。</p>
                </div>
                <div class="card">
                    <div class="metric-big" style="color: #f59e0b; -webkit-text-fill-color: initial;">24h 在線</div>
                    <div class="card-title">AI 商業歸因顧問</div>
                    <p class="card-desc">不只畫圖，秒級告訴您業績下滑原因，並直接產出挽回簡訊與對策。</p>
                </div>
            </div>
        </div>

        <!-- SLIDE 2: CURRENT PAIN POINTS -->
        <div class="slide" data-index="2">
            <div class="category-tag">⚠️ 經營現狀審視 · 老闆的共同痛點</div>
            <h2 class="action-title">
                為什麼努力賣貨，卻總覺得<span>被雜事綁架、看不清真實利潤？</span>
            </h2>
            <p class="action-subtitle">
                80% 的中小電商在日常營運中，都深陷於以下三大「隱形營運黑洞」：
            </p>
            <div class="grid-3">
                <div class="card" style="border-top: 4px solid #ef4444;">
                    <div class="card-icon">⏳</div>
                    <div class="card-title">黑洞一：每週人工搬磚拉表</div>
                    <p class="card-desc">
                        同仁每週一要手動登入官網、蝦皮、物流後台，下載好幾份 CSV，再手工複製貼上。一不小心公式貼錯、格式變更，就要加班抓漏，主管拿到的報表永遠延遲 3 天。
                    </p>
                    <div class="card-highlight" style="color: #f87171;">
                        💸 損失：每月白白消耗 20+ 小時高薪主管與會計工時
                    </div>
                </div>

                <div class="card" style="border-top: 4px solid #f59e0b;">
                    <div class="card-icon">📉</div>
                    <div class="card-title">黑洞二：業績虛假繁榮，毛利被吃掉</div>
                    <p class="card-desc">
                        行銷部門高興地報告「這檔活動破百萬」，但月底財務扣掉退貨、取消、運費補貼和折扣券後，才驚覺根本沒賺錢！缺乏統一指標分流，看不見底層真實獲利防線。
                    </p>
                    <div class="card-highlight" style="color: #fbbf24;">
                        💸 損失：隱形退款與取消漏洞，吃掉 3%~8% 淨利
                    </div>
                </div>

                <div class="card" style="border-top: 4px solid #a855f7;">
                    <div class="card-icon">🤷‍♂️</div>
                    <div class="card-title">黑洞三：死板報表，業績跌了盲目救火</div>
                    <p class="card-desc">
                        外購 Power BI/Tableau 每月一人要付好幾百，介面太難沒人會用；傳統報表只能看過去數字，當營收下滑或退款反常飆高時，開會大家都說不出原因，錯失挽回客人的黃金期。
                    </p>
                    <div class="card-highlight" style="color: #c084fc;">
                        💸 損失：跨部門會議推諉，流失高價值 VIP 客戶
                    </div>
                </div>
            </div>
        </div>

        <!-- SLIDE 3: SOLUTION ARCHITECTURE -->
        <div class="slide" data-index="3">
            <div class="category-tag">💡 完整解決方案全景 · 大白話解讀</div>
            <h2 class="action-title">
                專屬電商的一體化中台：<span>從資料採集到 AI 診斷的全自動流水線</span>
            </h2>
            <p class="action-subtitle">
                您不需要懂任何程式碼，系統已經為您打通了「採集、清洗、視覺化、AI 諮詢」的每一步：
            </p>
            <div class="grid-4">
                <div class="card">
                    <div class="card-icon">🔌</div>
                    <div class="card-title">1. 自動採集管家</div>
                    <p class="card-desc">
                        自動串接官網、通路與資料庫，每晚無感增量同步，徹底告別手動下載 CSV。
                    </p>
                    <div class="card-highlight">✔ 零人工手動介入</div>
                </div>

                <div class="card">
                    <div class="card-icon">🛡️</div>
                    <div class="card-title">2. 淨利守門標準</div>
                    <p class="card-desc">
                        將資料分層過濾（金銀銅湖倉），嚴格扣除取消、退款與折價，還原每一塊錢真實毛利。
                    </p>
                    <div class="card-highlight">✔ 數據精準無偏差</div>
                </div>

                <div class="card">
                    <div class="card-icon">📊</div>
                    <div class="card-title">3. 隨選拖曳大看板</div>
                    <p class="card-desc">
                        內建類 Tableau 畫布與自然語言產圖，滑鼠拖一下或打字「看各品類銷量」立刻出圖。
                    </p>
                    <div class="card-highlight">✔ 省下每年數萬軟體費</div>
                </div>

                <div class="card">
                    <div class="card-icon">🧠</div>
                    <div class="card-title">4. 24h AI 顧問</div>
                    <p class="card-desc">
                        麥肯錫級 AI 大腦，秒級分析圖表問題，主動告訴您「問題在哪、該做什麼行動」。
                    </p>
                    <div class="card-highlight">✔ 秒出挽回簡訊與策略</div>
                </div>
            </div>
        </div>

        <!-- SLIDE 4: BEFORE VS AFTER COMPARISON -->
        <div class="slide" data-index="4">
            <div class="category-tag">🔄 轉變與成效對比 · 營運效率翻倍</div>
            <h2 class="action-title">
                導入前後強烈對比：<span>您的團隊日常工作方式將徹底改變</span>
            </h2>
            <p class="action-subtitle">
                從「疲於奔命整理歷史資料」轉變為「即時看盤、主動出擊」的敏捷電商團隊：
            </p>
            <div class="compare-box">
                <div class="box-before">
                    <div class="box-head">❌ 傳統舊流程 (痛點與內耗)</div>
                    <div class="compare-item">
                        <span class="bullet-red">✕</span>
                        <div><strong>每週耗費 5~8 小時人工拉表</strong>：週一早上主管忙著抓報表對齊，無法及時處理顧客急件。</div>
                    </div>
                    <div class="compare-item">
                        <span class="bullet-red">✕</span>
                        <div><strong>指標口徑各說各話</strong>：業務說業績達成、財務說帳面虧損，退款手動扣除容易漏算。</div>
                    </div>
                    <div class="compare-item">
                        <span class="bullet-red">✕</span>
                        <div><strong>報表死板且授權昂貴</strong>：想看個交叉分析要等好幾天，外購 BI 軟體每年燒掉幾十萬。</div>
                    </div>
                    <div class="compare-item">
                        <span class="bullet-red">✕</span>
                        <div><strong>異常發生只能瞎猜原因</strong>：營收掉了大家開會互推責任，不知道是物流延遲還是特定商品缺貨。</div>
                    </div>
                </div>

                <div class="box-after">
                    <div class="box-head">✅ 本方案導入後 (全自動化與智能賦能)</div>
                    <div class="compare-item">
                        <span class="bullet-green">✓</span>
                        <div><strong>0 秒自動更新，隨時隨地看盤</strong>：系統全自動同步，開機即見今日最新 GMV、AOV 與營收走勢。</div>
                    </div>
                    <div class="compare-item">
                        <span class="bullet-green">✓</span>
                        <div><strong>真實淨營收一目了然</strong>：自動剔除退款退貨，一眼看清每個品類、每位客戶的真實貢獻毛利。</div>
                    </div>
                    <div class="compare-item">
                        <span class="bullet-green">✓</span>
                        <div><strong>瀏覽器內建自訂畫布</strong>：打字「我想看熱銷商品走勢」立即生成，完全省下外購 BI 月租費。</div>
                    </div>
                    <div class="compare-item">
                        <span class="bullet-green">✓</span>
                        <div><strong>AI 顧問即時歸因與建議</strong>：點一下診斷按鈕，AI 秒出 SCQA 分析，並附上現成 VIP 挽回簡訊範本。</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- SLIDE 5: AI COPILOT SHOWCASE -->
        <div class="slide" data-index="5">
            <div class="category-tag">⭐ 殺手級核心特色 · FastMCP 商業大腦</div>
            <h2 class="action-title">
                不僅是報表工具：<span>更是聘請了一位 24 小時在線的「AI 營運總監」</span>
            </h2>
            <p class="action-subtitle">
                結合頂尖管理顧問（MBB）框架與雙向對話能力，讓 AI 成為老闆身邊最懂電商的決策智囊：
            </p>
            <div class="grid-3">
                <div class="card">
                    <div class="card-icon">🎯</div>
                    <div class="card-title">1. SCQA 深度因果歸因</div>
                    <p class="card-desc">
                        不只告訴您「退款率增加 3%」，而是結構化告訴您：<strong>現況 (S)</strong>、<strong>併發痛點 (C)</strong>、<strong>核心挑戰 (Q)</strong> 與 <strong>戰略假設 (A)</strong>，直接找出集中度風險。
                    </p>
                </div>

                <div class="card">
                    <div class="card-icon">📱</div>
                    <div class="card-title">2. 立即落地的武器 (簡訊文案)</div>
                    <p class="card-desc">
                        針對未結帳購物車或取消訂單，AI 直接產出高轉換召回簡訊模板（如 <code>VIPRECOVER</code> 免運折扣碼），並貼心設定邊際利潤防線，防止顧客常態刷折扣。
                    </p>
                </div>

                <div class="card">
                    <div class="card-icon">💬</div>
                    <div class="card-title">3. 連續多輪深度追問</div>
                    <p class="card-desc">
                        就像與真人顧問對談！您可以隨時追問：<em>「如果我只有 10 萬預算該優先投哪？」</em>、<em>「幫我把這張表寫成給董事會的摘要」</em>，AI 隨時給予精闢策略。
                    </p>
                </div>
            </div>

            <div class="card" style="margin-top: 1.5rem; background: rgba(37, 99, 235, 0.1); border-color: rgba(37, 99, 235, 0.3);">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <strong style="color: #60a5fa; font-size: 1.05rem;">🛡️ 雙重高可用與防呆保障 (BYOK 安全架構)</strong>
                        <p style="font-size: 0.9rem; color: #cbd5e1; margin-top: 0.25rem;">
                            支援 Google Gemini 多層自動降級（遇尖峰 503 自動秒切 3.6/2.5），離線亦可無損運作；金鑰完全由您掌控，系統絕不儲存亦無額外轉手費用。
                        </p>
                    </div>
                    <div style="font-size: 1.8rem; margin-left: 1.5rem;">🔒</div>
                </div>
            </div>
        </div>

        <!-- SLIDE 6: ROI & BUSINESS IMPACT -->
        <div class="slide" data-index="6">
            <div class="category-tag">💰 投資報酬率 · 具體商業收益回報</div>
            <h2 class="action-title">
                算一筆明白帳：<span>每個月能為您的公司創造多少實質價值？</span>
            </h2>
            <p class="action-subtitle">
                這不是一筆額外的花費，而是一筆在第一個月就能快速回收投資（Fast Payback）的降本增效投資：
            </p>
            <div class="grid-3">
                <div class="card" style="text-align: center; padding: 2.25rem 1.5rem;">
                    <div class="metric-big" style="color: #38bdf8;">25+ 小時</div>
                    <div class="card-title" style="margin-top: 0.5rem;">每月省下的人工工時</div>
                    <p class="card-desc">
                        釋放原本手動下載、整理、核對報表的時間，讓店長與行銷團隊專注於選品、廣告與客群經營。
                    </p>
                    <div class="card-highlight" style="justify-content: center; color: #38bdf8;">
                        相當於年省十數萬人力成本
                    </div>
                </div>

                <div class="card" style="text-align: center; padding: 2.25rem 1.5rem;">
                    <div class="metric-big" style="color: #34d399;">+3% ~ 5%</div>
                    <div class="card-title" style="margin-top: 0.5rem;">挽回流失之實質淨營收</div>
                    <p class="card-desc">
                        透過 AI 即時預警與止血簡訊，挽回在購物車猶豫、取消結帳的顧客，守住每一分原本會流失的營收。
                    </p>
                    <div class="card-highlight" style="justify-content: center; color: #34d399;">
                        月營收 100 萬即可多賺 3~5 萬
                    </div>
                </div>

                <div class="card" style="text-align: center; padding: 2.25rem 1.5rem;">
                    <div class="metric-big" style="color: #f59e0b;">10 萬元+</div>
                    <div class="card-title" style="margin-top: 0.5rem;">每年省下的外購軟體費</div>
                    <p class="card-desc">
                        免買昂貴的 Tableau / Power BI 商業席位與客製化報表系統，瀏覽器打開直接全功能使用。
                    </p>
                    <div class="card-highlight" style="justify-content: center; color: #f59e0b;">
                        零隱藏訂閱費，成本精簡可控
                    </div>
                </div>
            </div>
        </div>

        <!-- SLIDE 7: 30-DAY POC & CALL TO ACTION -->
        <div class="slide" data-index="7">
            <div class="category-tag">🤝 合作與落地推進 · 零風險驗證</div>
            <h2 class="action-title">
                30 天概念驗證 (PoC)：<span>低風險、不改動現有系統，看見實效再決定</span>
            </h2>
            <p class="action-subtitle">
                我們深知中小企業不容許漫長的系統開發週期。我們提供輕量化、敏捷的 30 天落地路徑：
            </p>
            <div class="timeline">
                <div class="timeline-step">
                    <span class="step-badge">第 1 週 · 零打擾對接</span>
                    <div class="card-title">通路資料管線打通</div>
                    <p class="card-desc">
                        無需更換現有任何官網或 POS 系統，透過自動排程安全對接您的資料來源，建立雲端資料底座。
                    </p>
                </div>

                <div class="timeline-step">
                    <span class="step-badge" style="background: #0284c7;">第 2~3 週 · 專屬看板</span>
                    <div class="card-title">指標建模與看板校準</div>
                    <p class="card-desc">
                        為您的店面校準真正的「淨利防線、會員 LTV 與熱銷排行」，產出專屬老闆的手機/電腦即時畫布。
                    </p>
                </div>

                <div class="timeline-step">
                    <span class="step-badge" style="background: #059669;">第 4 週 · 成果驗證</span>
                    <div class="card-title">AI 營運軍師開箱</div>
                    <p class="card-desc">
                        正式啟用 FastMCP 商業診斷室，團隊實際體驗自然語言產圖、AI 秒級歸因與挽回簡訊決策效益。
                    </p>
                </div>
            </div>

            <div style="margin-top: 2rem; background: linear-gradient(135deg, rgba(37, 99, 235, 0.2), rgba(16, 185, 129, 0.15)); border: 1px solid rgba(59, 130, 246, 0.4); border-radius: 16px; padding: 1.5rem 2rem; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h3 style="color: #ffffff; font-size: 1.3rem; margin-bottom: 0.25rem;">讓數據替您工作，把時間還給生意！</h3>
                    <p style="color: #94a3b8; font-size: 0.95rem;">我們已經準備好現成的完整互動系統 Demo，隨時可以為您現場實機演示！</p>
                </div>
                <div style="background: #2563eb; color: #ffffff; font-weight: 700; font-size: 1rem; padding: 10px 24px; border-radius: 10px; cursor: pointer; border: none;">
                    👉 立即預約 15 分鐘實機展示
                </div>
            </div>
        </div>

    </div>

    <!-- Bottom Indicator Dots -->
    <div class="bottom-nav" id="dotsContainer"></div>

    <script>
        const slides = document.querySelectorAll('.slide');
        const dotsContainer = document.getElementById('dotsContainer');
        const slideCounter = document.getElementById('slideCounter');
        const btnPrev = document.getElementById('btnPrev');
        const btnNext = document.getElementById('btnNext');
        const btnFullscreen = document.getElementById('btnFullscreen');
        
        let currentIndex = 0;
        const totalSlides = slides.length;

        // Create navigation dots
        slides.forEach((_, idx) => {
            const dot = document.createElement('div');
            dot.classList.add('dot');
            if (idx === 0) dot.classList.add('active');
            dot.addEventListener('click', () => goToSlide(idx));
            dotsContainer.appendChild(dot);
        });

        const dots = document.querySelectorAll('.dot');

        function updateSlideUI() {
            slides.forEach((slide, idx) => {
                slide.classList.toggle('active', idx === currentIndex);
            });
            dots.forEach((dot, idx) => {
                dot.classList.toggle('active', idx === currentIndex);
            });
            slideCounter.textContent = `${currentIndex + 1} / ${totalSlides}`;
            btnPrev.disabled = currentIndex === 0;
            btnNext.disabled = currentIndex === totalSlides - 1;
        }

        function goToSlide(index) {
            if (index >= 0 && index < totalSlides) {
                currentIndex = index;
                updateSlideUI();
            }
        }

        btnPrev.addEventListener('click', () => goToSlide(currentIndex - 1));
        btnNext.addEventListener('click', () => goToSlide(currentIndex + 1));

        // Keyboard Controls
        window.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowRight' || e.key === 'Space') {
                e.preventDefault();
                goToSlide(currentIndex + 1);
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                goToSlide(currentIndex - 1);
            }
        });

        // Fullscreen Toggle
        btnFullscreen.addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen().catch(err => alert(`無法進入全螢幕：${err.message}`));
            } else {
                document.exitFullscreen();
            }
        });
    </script>
</body>
</html>
"""


def main():
    docs_dir = os.path.join(os.getcwd(), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    html_file = os.path.join(docs_dir, "ecommerce_owner_pitch_deck.html")
    pdf_file = os.path.join(docs_dir, "ecommerce_owner_pitch_deck.pdf")

    # 1. Write HTML Presentation
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(HTML_SLIDES)
    print(f"[OK] HTML slide deck generated at: {html_file}")

    # 2. Print to PDF via Edge Headless
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    edge_bin = next((p for p in edge_paths if os.path.exists(p)), None)

    if edge_bin:
        cmd = [
            edge_bin,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_file}",
            html_file,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
            size_kb = os.path.getsize(pdf_file) / 1024
            print(f"[SUCCESS] PDF slide deck created: {pdf_file} ({size_kb:.1f} KB)")
        else:
            print(f"[WARN] Edge PDF output: {res.stderr}")


if __name__ == "__main__":
    main()
