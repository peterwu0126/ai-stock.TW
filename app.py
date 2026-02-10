import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
import pandas_ta as ta

# 1. 配置 Gemini API
api_key = st.secrets.get("GEMINI_API_KEY")
genai.configure(api_key)
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash'
)

TW_50_LIST = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2412.TW", "2881.TW", "2882.TW",
    "2357.TW", "3711.TW", "2891.TW", "2303.TW", "2886.TW", "1301.TW", "1303.TW", "2408.TW",
    "2884.TW", "2885.TW", "3008.TW", "1216.TW", "2005.TW", "2327.TW", "2892.TW", "5880.TW",
    "2880.TW", "2912.TW", "3034.TW", "2379.TW", "1101.TW", "3231.TW", "2301.TW", "2603.TW",
    "2609.TW", "2615.TW", "2474.TW", "2883.TW", "2887.TW", "2890.TW", "5871.TW", "5876.TW",
    "9910.TW", "2395.TW", "3045.TW", "2345.TW", "6505.TW", "6669.TW", "1513.TW", "1503.TW"
]

st.set_page_config(page_title="AI 台股專業選股助手", layout="wide")
st.title("🏆 AI 雙料選股助手：0050 強勢股掃描")

# --- 2. 首頁大按鈕佈局 ---
col_input, col_auto = st.columns([2, 1])

with col_input:
    tickers_input = st.text_input("手動輸入台股代碼 (如 2330, 2317)", "2330, 2317")
    manual_analyze = st.button("🔍 手動分析", use_container_width=True)

with col_auto:
    st.write("沒靈感？找 0050 裡最強的：")
    auto_analyze = st.button("🚀 啟動 0050 潛力股掃描", type="primary", use_container_width=True)

# --- 3. 處理邏輯 ---
tickers = []
if manual_analyze:
    raw_tickers = [t.strip().upper() for t in tickers_input.split(",")]
    tickers = [t if "." in t else f"{t}.TW" for t in raw_tickers]
elif auto_analyze:
    with st.spinner('正在體檢 0050 成分股技術面...'):
        recommended = []
        # 為了避開 API 頻率限制，我們隨機抽樣或只掃描前 20 支最熱門的
        for t in TW_50_LIST[:25]: 
            try:
                s = yf.Ticker(t)
                hist = s.history(period="1mo")
                if len(hist) > 15:
                    rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
                    ma20 = ta.sma(hist['Close'], length=20).iloc[-1]
                    cur_p = hist['Close'].iloc[-1]
                    # 篩選：站上月線且 RSI 在 45~65 (強勢但未過熱)
                    if cur_p > ma20 and 45 < rsi < 65:
                        recommended.append(t)
            except: continue
        tickers = recommended[:4] if recommended else ["2330.TW", "2317.TW"]
        st.success(f"✅ 掃描完成！今日推薦關注：{', '.join(tickers)}")

# --- 4. 數據分析與 AI 生成 (僅在 tickers 有值時執行) ---
if tickers:
    all_data_summary = ""
    cols = st.columns(len(tickers))
    
    for i, ticker in enumerate(tickers):
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")
        
        # --- 抓取基本面數據 ---
        info = stock.info
        pe = info.get('trailingPE', 'N/A')  # 本益比
        pb = info.get('priceToBook', 'N/A') # 股價淨值比
        rev_growth = info.get('revenueGrowth', 0) * 100 # 營收成長率
        
        if not df.empty:
            # --- 修正縮排的計算區塊 ---
            # 1. 計算技術指標 (確保 ta 函數前是 12 個空格)
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            atr_val = df['ATR'].iloc[-1]
            cur = df.iloc[-1]
            status = "多頭" if cur['Close'] > cur['MA20'] else "空頭"
            
            # 2. 專業停損停利建議 (根據 ATR 波動率)
            suggested_stop = cur['Close'] - (atr_val * 2)
            suggested_target = cur['Close'] + (atr_val * 4)
            
            # 3. 建立 AI 摘要
            all_data_summary += f"""
            股票: {ticker}
            - 技術面: 現價 {cur['Close']:.2f}, RSI {cur['RSI']:.2f}, 趨勢 {status}
            - 基本面: 本益比(PE) {pe}, 股價淨值比(PB) {pb}, 營收成長率 {rev_growth:.1f}%
            - 建議防守價(停損): {suggested_stop:.2f}
            - 建議進攻價(停利): {suggested_target:.2f}
            ---
            """
            
            # 4. 顯示卡片 (新增 ATR 警示)
            with cols[i]:
                st.metric(ticker, f"{cur['Close']:.0f}", f"{cur['RSI']:.1f} RSI")
                
                # --- 新增：過去 60 天的走勢圖，包含收盤價與 20 日均線 ---
                chart_data = df[['Close', 'MA20']].tail(60)
                st.line_chart(chart_data)
                
                st.write(f"📊 **策略參數**")
                st.caption(f"止損: {suggested_stop:.1f}")
                st.caption(f"止盈: {suggested_target:.1f}")

    # 讓 AI 進行綜合點評
    comparison_prompt = f"""
    你是一個資深基金經理人。請針對以下數據進行深度分析：
    {all_data_summary}
    
    請以繁體中文提供分析：
    1. 【綜合實力排名】：考量「趨勢是否向上」且「估值是否合理(PE/PB)」。
    2. 【數據解讀】：針對 RSI 與 ATR 提供的點位，說明目前是否為合適進場點。
    3. 【避雷提醒】：哪些股票雖然股價在漲但其實已經「太貴」？
    """
    
    portfolio_prompt = f"""
    你是私人銀行顧問。基於以下股票數據：
    {all_data_summary}
    
   如果客戶有 100 萬台幣，請提供配置建議：
   1. 【資產配置表】：盡量包含「現金保留比例」(建議 10-20%)，其餘才分配給股票。
   2. 【配置邏輯】：說明為何保留這些現金（例如應對市場波動、等待加碼點）。
   3. 【風控提醒】：提供整體組合跌幅超過多少時，應動用現金防守或減碼。
    
    請以繁體中文回答。
    """

    st.divider()

    # --- 修改顯示邏輯：使用分頁標籤 ---
    tab1, tab2 = st.tabs(["🔍 綜合實力排名", "💰 100萬投資建議"])

    with tab1:
        with st.spinner('經理人正在評分...'):
            try:
                response1 = model.generate_content(comparison_prompt)
                with st.container(height=500):
                    st.markdown(response1.text)
            except Exception as e:
                st.error("目前 API 配額忙碌中，請稍候一分鐘再試，或檢查 API Key。")
                response1 = type('obj', (object,), {'text' : '分析暫時無法生成'})() # 建立虛擬物件防止下載按鈕報錯

    with tab2:
        with st.spinner('顧問正在計算配置比例...'):
            try:
                response2 = model.generate_content(portfolio_prompt)
                with st.container(height=500):
                    st.markdown(response2.text)
            except Exception as e:
                st.error("無法生成配置建議。")
                response2 = type('obj', (object,), {'text' : '建議暫時無法生成'})()
    report_md = f"""# 📈 AI 投資分析報告
**生成日期**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
**分析標的**: {", ".join(tickers)}

---

## 🔍 綜合實力排名
{response1.text}

---

## 💰 100萬投資建議
{response2.text}

---
*免責聲明：本報告由 AI 自動生成，僅供參考。投資必有風險，決策前請務必謹慎評估。*
"""

    # 2. 放置下載按鈕 (放在 tabs 下方或上方皆可，這裡建議放在最下方做總結)
    st.write("") # 留一點空白
    st.download_button(
        label="📥 下載完整分析報告 (.md)",
        data=report_md,
        file_name=f"Stock_Report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
        use_container_width=True # 讓按鈕變寬，更好點擊

    )
