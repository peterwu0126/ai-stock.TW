import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
import pandas_ta as ta
import random
import time

# 1. 配置 Gemini API
api_key = st.secrets.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
# 修正模型名稱為穩定版
model = genai.GenerativeModel(model_name='gemini-2.5-flash')

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

# --- 2. 數據快取函數 ---
@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="6mo")
    info = stock.info
    return df, info

# --- 3. 首頁大按鈕佈局 ---
col_input, col_auto = st.columns([2, 1])

with col_input:
    tickers_input = st.text_input("手動輸入台股代碼 (如 2330, 2317)", "2330, 2317")
    manual_analyze = st.button("🔍 手動分析", use_container_width=True)

with col_auto:
    st.write("沒靈感？找 0050 裡最強的：")
    auto_analyze = st.button("🚀 啟動 0050 潛力股掃描", type="primary", use_container_width=True)

tickers = []
if manual_analyze:
    raw_tickers = [t.strip().upper() for t in tickers_input.split(",")]
    tickers = [t if "." in t else f"{t}.TW" for t in raw_tickers]
elif auto_analyze:
    with st.spinner('正在體檢 0050 成分股技術面...'):
        recommended = []
        scan_list = random.sample(TW_50_LIST, 15) # 隨機抽樣減少 API 負擔
        for t in scan_list:
            try:
                time.sleep(0.2)
                s = yf.Ticker(t)
                hist = s.history(period="1mo")
                if len(hist) > 15:
                    rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
                    ma20 = ta.sma(hist['Close'], length=20).iloc[-1]
                    if hist['Close'].iloc[-1] > ma20 and 45 < rsi < 65:
                        recommended.append(t)
            except: continue
        tickers = recommended[:4] if recommended else ["2330.TW", "2317.TW"]
        st.success(f"✅ 掃描完成！今日推薦：{', '.join(tickers)}")

# --- 4. 數據分析與 AI 生成 ---
if tickers:
    all_data_summary = ""
    cols = st.columns(len(tickers))
    
    for i, ticker in enumerate(tickers):
        df, info = get_stock_data(ticker)
        
        if not df.empty:
            # 基本面數據抓取
            pe = info.get('trailingPE', 'N/A')
            pb = info.get('priceToBook', 'N/A')
            rev_growth = info.get('revenueGrowth', 0) * 100
            
            # 技術指標計算
            df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            df['MA20'] = ta.sma(df['Close'], length=20)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            cur = df.iloc[-1]
            atr_val = df['ATR'].iloc[-1]
            status = "多頭" if cur['Close'] > cur['MA20'] else "空頭"
            suggested_stop = cur['Close'] - (atr_val * 2)
            suggested_target = cur['Close'] + (atr_val * 4)
            
            all_data_summary += f"股票: {ticker}, 現價: {cur['Close']:.2f}, RSI: {cur['RSI']:.1f}, PE: {pe}, 趨勢: {status}\n"
            
            with cols[i]:
                st.metric(ticker, f"{cur['Close']:.0f}", f"{cur['RSI']:.1f} RSI")
                st.line_chart(df[['Close', 'MA20']].tail(60))
                st.caption(f"止損: {suggested_stop:.1f} | 止盈: {suggested_target:.1f}")

    st.divider()
    tab1, tab2 = st.tabs(["🔍 綜合實力排名", "💰 100萬投資建議"])

    # 初始化 response 文字以防報錯
    res1_text = "分析生成失敗"
    res2_text = "配置建議生成失敗"

    with tab1:
        with st.spinner('經理人正在評分...'):
            try:
                prompt1 = f"你是一個資深基金經理人，請分析以下數據並給出實力排名與避雷提醒：\n{all_data_summary}"
                response1 = model.generate_content(prompt1)
                res1_text = response1.text
                st.markdown(res1_text)
            except:
                st.error("API 忙碌中")

    with tab2:
        with st.spinner('顧問正在計算配置比例...'):
            try:
                prompt2 = f"你是私人銀行顧問。請根據以下數據提供 100 萬台幣配置建議，需包含至少 10% 現金保留：\n{all_data_summary}"
                response2 = model.generate_content(prompt2)
                res2_text = response2.text
                st.markdown(res2_text)
            except:
                st.error("API 忙碌中")

    # 下載按鈕
    report_md = f"# 📈 AI 投資分析報告\n\n## 🔍 綜合實力排名\n{res1_text}\n\n## 💰 投資建議\n{res2_text}"
    st.download_button("📥 下載完整分析報告 (.md)", data=report_md, file_name="Stock_Report.md", use_container_width=True)
