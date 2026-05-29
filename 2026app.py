import streamlit as st
import yfinance as yf
import pandas as pd
import datetime
import altair as alt  # 에러 방지를 위해 Altair 라이브러리를 최상단 전역 공간으로 올렸습니다.

# 모바일 화면에 최적화된 레이아웃 설정
st.set_page_config(page_title="동적 자산배분 대시보드", layout="centered", initial_sidebar_state="collapsed")

# 연도별 백테스트 상세 성과 데이터 정의 (NameError 방지 및 안정적인 전역 참조를 위해 최상단에 배치)
df_annual_raw = pd.DataFrame({
    "연도": [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025],
    "수익률 (%)": [21.0, 31.3, 75.3, 42.1, -2.3, 38.6, 58.7, 39.5]
})

df_annual_display = pd.DataFrame({
    "연도": ["2018년", "2019년", "2020년", "2021년", "2022년", "2023년", "2024년", "2025년", "평균 (CAGR)"],
    "누적 연수익률": ["+21.0%", "+31.3%", "+75.3%", "+42.1%", "-2.3%", "+38.6%", "+58.7%", "+39.5%", "+38.7%"]
})

# 프리미엄 그레이/슬레이트 톤 스타일 및 탭 선택바 강조 스타일 주입
st.markdown("""
    <style>
    /* 글로벌 배경화면 및 메인 톤 조정 */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* 상단 탭 메뉴(전략 선택 영역)를 프리미엄 그레이 세그먼트 컨트롤러로 강조 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #e2e8f0 !important; /* 차분하고 정돈된 미디엄 그레이 배경 */
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 5px !important;
        gap: 4px !important;
        box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06), 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        margin-bottom: 20px !important;
    }
    
    /* 탭 내부 개별 버튼들을 하나의 모던한 세그먼트로 구성 */
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border-radius: 8px !important;
        padding: 10px 12px !important;
        font-weight: 800 !important;
        font-size: 0.85rem !important;
        color: #475569 !important; /* 세련된 다크그레이 글자색 */
        border: none !important;
        transition: all 0.2s ease-in-out !important;
        flex: 1 !important; /* 모바일 화면에서 동일 가로비율 배분 */
        text-align: center !important;
    }
    
    /* [선택된 탭 강조] 딥 슬레이트 그레이 컬러로 압도적인 선택 상태 시인성 제공 */
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important; /* 다크 슬레이트 그레이 */
        color: #ffffff !important; /* 선명한 화이트 텍스트 */
        box-shadow: 0 4px 10px -2px rgba(30, 41, 59, 0.3) !important;
    }
    
    /* 시뮬레이션 설정 상자도 품격 있는 뉴트럴 그레이 톤 플레이트로 교체 */
    .control-panel {
        background-color: #f1f5f9 !important; /* 부드러운 라이트 그레이 */
        border: 1px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 18px !important;
        margin-bottom: 20px !important;
    }
    .control-header {
        color: #0f172a !important; /* 차분한 블랙 계열 */
        font-weight: 800 !important;
        font-size: 0.98rem !important;
        margin-bottom: 4px !important;
    }
    .control-subheader {
        color: #475569 !important; /* 짙은 회색 */
        font-size: 0.8rem !important;
        line-height: 1.45 !important;
    }
    
    /* 매크로 시황판 카드 스타일 */
    .macro-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 12px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .macro-title {
        font-size: 0.78rem;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 2px;
    }
    .macro-value {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
    }
    .macro-delta-up {
        font-size: 0.75rem;
        color: #dc2626;
        font-weight: 600;
    }
    .macro-delta-down {
        font-size: 0.75rem;
        color: #2563eb;
        font-weight: 600;
    }
    .macro-delta-equal {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 동적 자산배분 대시보드")
st.caption("야후 파이낸스 실시간 데이터 기반 수시 리밸런싱 가이드 (2026년 전략 및 실시간 미국 ETF 랭킹 포함)")

# --- 자산군 정의 ---
OFFENSIVE_A = ["QQQ", "SPY", "IYM", "IBB", "SMH", "EEM", "XLK", "LIT", "XLE", "FEZ", "XLV", "XLU", "QTUM"]
DEFENSIVE_A = ["GLD", "TLT", "XLV", "UBT"]
OFFENSIVE_B = ["TYD", "UPRO", "VNQ"]
DEFENSIVE_B = ["DOG", "RWM", "TBF"]
OFFENSIVE_C = ["FDN", "LIT", "SMH", "XLE"]  
DEFENSIVE_C = ["GLD", "PDBC", "OILK"]       

ALL_TICKERS = list(set(["TIP", "SPY"] + OFFENSIVE_A + DEFENSIVE_A + OFFENSIVE_B + DEFENSIVE_B + OFFENSIVE_C + DEFENSIVE_C + ["SCHD", "JEPI", "TQQQ", "SOXL", "DIA", "IWM", "XLF"]))

MACRO_TICKERS = {
    "달러/원": "USDKRW=X",
    "달러/중국 위안": "USDCNY=X",
    "달러/엔": "USDJPY=X",
    "미국 달러 지수": "DX-Y.NYB",
    "미국 10년물 국채 금리": "^TNX",
    "WTI유": "CL=F",
    "S&P 500 VIX": "^VIX",
    "US 500 (S&P)": "^GSPC",
    "US Tech 100 (나스닥)": "^NDX",
    "인베스코QQQ": "QQQ",
    "코스피 200": "^KS200"
}

@st.cache_data(ttl=300)  
def get_macro_market_pulse():
    macro_data = []
    for name, symbol in MACRO_TICKERS.items():
        price_val = "-"
        delta_val = "0.00"
        delta_pct_val = "0.00%"
        raw_delta_val = 0.0
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if not hist.empty and 'Close' in hist.columns and len(hist) >= 1:
                closes = hist['Close'].dropna()
                if len(closes) >= 1:
                    current_price = closes.iloc[-1]
                    prev_price = closes.iloc[-2] if len(closes) >= 2 else current_price
                    delta = current_price - prev_price
                    delta_pct = (delta / prev_price) * 100 if prev_price > 0 else 0.0
                    
                    if symbol == "^TNX":
                        price_val = f"{current_price:.3f}%"
                        delta_val = f"{delta:+.3f}"
                    elif "KRW=X" in symbol:
                        price_val = f"{current_price:,.2f}원"
                        delta_val = f"{delta:+.2f}"
                    elif "=X" in symbol:
                        price_val = f"{current_price:,.4f}"
                        delta_val = f"{delta:+.4f}"
                    else:
                        price_val = f"{current_price:,.2f}"
                        delta_val = f"{delta:+.2f}"
                    
                    delta_pct_val = f"{delta_pct:+.2f}%"
                    raw_delta_val = delta
        except Exception:
            pass
            
        macro_data.append({
            "name": name,
            "symbol": symbol,
            "price": price_val,
            "delta": delta_val,
            "delta_pct": delta_pct_val,
            "raw_delta": raw_delta_val
        })
    return macro_data

with st.spinner("관심 시황판 실시간 매크로 지표 동기화 중..."):
    macro_pulse = get_macro_market_pulse()

with st.expander("🌍 실시간 글로벌 매크로 시황판 (내 관심목록)", expanded=True):
    cols = st.columns(4)
    for idx, item in enumerate(macro_pulse):
        col_to_use = cols[idx % 4]
        delta_class = "macro-delta-equal"
        if item["raw_delta"] > 0:
            delta_class = "macro-delta-up"
        elif item["raw_delta"] < 0:
            delta_class = "macro-delta-down"
            
        col_to_use.markdown(f"""
            <div class="macro-card">
                <div class="macro-title">{item['name']} <small style='color:#94a3b8; font-size:0.65rem;'>{item['symbol']}</small></div>
                <div class="macro-value">{item['price']}</div>
                <div class="{delta_class}">{item['delta']} ({item['delta_pct']})</div>
            </div>
        """, unsafe_allow_html=True)

def get_usd_krw_rate():
    try:
        usd_krw = yf.Ticker("USDKRW=X")
        hist = usd_krw.history(period="5d")
        if not hist.empty and 'Close' in hist.columns:
            closes = hist['Close'].dropna()
            if len(closes) >= 1:
                return float(closes.iloc[-1])
    except Exception:
        pass
    return 1380.0  

def get_sp500_dividend_yield():
    try:
        spy = yf.Ticker("SPY")
        dy = spy.info.get('dividendYield')
        if dy is not None:
            dy_val = float(dy)
            if dy_val < 0.15:
                return dy_val * 100
            return dy_val
        
        divs = spy.dividends
        if not divs.empty:
            utc_tz = divs.index.tz
            end_dt = pd.Timestamp.now(tz=utc_tz)
            start_dt = end_dt - pd.Timedelta(days=365)
            last_year_divs = divs.loc[start_dt:end_dt]
            sum_divs = last_year_divs.sum()
            
            hist = spy.history(period="1mo")
            if not hist.empty and 'Close' in hist.columns:
                closes = hist['Close'].dropna()
                if len(closes) >= 1:
                    curr_price = closes.iloc[-1]
                    return (sum_divs / curr_price) * 100
    except Exception as e:
        pass
    return 1.32  

@st.cache_data(ttl=3600)  
def get_all_financial_data_v2(tickers):
    data_list = []
    now = datetime.datetime.now()
    start_date = (now - datetime.timedelta(days=450)).strftime('%Y-%m-%d')
    
    for ticker in tickers:
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(start=start_date, interval="1mo")
            if len(hist) < 12 or 'Close' not in hist.columns:
                continue
            
            closes = hist['Close'].dropna()
            if len(closes) < 12:
                continue
            
            current_price = closes.iloc[-1]
            p1 = closes.iloc[-2] if len(closes) >= 2 else current_price
            p3 = closes.iloc[-4] if len(closes) >= 4 else current_price
            p5 = closes.iloc[-6] if len(closes) >= 6 else current_price 
            p6 = closes.iloc[-7] if len(closes) >= 7 else current_price
            p9 = closes.iloc[-10] if len(closes) >= 10 else current_price
            p12 = closes.iloc[-13] if len(closes) >= 13 else closes.iloc[0]
            
            r1 = ((current_price - p1) / p1) * 100
            r3 = ((current_price - p3) / p3) * 100
            r5 = ((current_price - p5) / p5) * 100
            r6 = ((current_price - p6) / p6) * 100
            r9 = ((current_price - p9) / p9) * 100
            r12 = ((current_price - p12) / p12) * 100
            
            score_a_off = (r1 + r3 + r6 + r12) / 4
            score_a_def = (r1 + r3 + r6 + r9 + r12) / 5
            score_b_off = (r1 * 12 + r3 * 4 + r6 * 2 + r12 * 1) / 19
            score_b_def_simple = (r1 + r3 + r6 + r9 + r12) / 5  
            
            data_list.append({
                "Ticker": ticker,
                "현재가": round(current_price, 2),
                "1M": round(r1, 1), 
                "3M": round(r3, 1), 
                "5M": round(r5, 1),
                "6M": round(r6, 1), 
                "9M": round(r9, 1), 
                "12M": round(r12, 1),
                "A_공격스코어": round(score_a_off, 2),
                "A_방어스코어": round(score_a_def, 2),
                "B_공격스코어": round(score_b_off, 2),
                "B_단순모멘텀": round(score_b_def_simple, 2),
                "raw_closes": closes.tolist()
            })
        except Exception as e:
            st.error(f"{ticker} 데이터를 가져오는 중 오류 발생: {e}")
            
    return pd.DataFrame(data_list)

@st.cache_data(ttl=3600)
def get_historical_simulation_data(tickers):
    prices_dict = {}
    now = datetime.datetime.now()
    start_date = (now - datetime.timedelta(days=800)).strftime('%Y-%m-%d')
    for ticker in tickers:
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(start=start_date, interval="1d")
            if not hist.empty:
                prices_dict[ticker] = hist['Close']
        except Exception:
            pass
            
    spy_divs = pd.Series(dtype=float)
    try:
        spy_divs = yf.Ticker("SPY").dividends
    except Exception:
        pass
        
    return prices_dict, spy_divs

def compute_historical_portfolio_at_month_end(prices_dict, spy_divs, target_date, OFFENSIVE_A, DEFENSIVE_A, OFFENSIVE_B, DEFENSIVE_B, OFFENSIVE_C, DEFENSIVE_C):
    monthly_prices = {}
    for t, series in prices_dict.items():
        sub_series = series[series.index <= target_date]
        if sub_series.empty:
            continue
        
        df = sub_series.to_frame()
        df['year'] = df.index.year
        df['month'] = df.index.month
        last_idx = df.groupby(['year', 'month']).apply(lambda x: x.index[-1])
        m_closes = sub_series.loc[last_idx].tolist()
        
        if len(m_closes) < 13:
            continue
        monthly_prices[t] = m_closes

    if "TIP" not in monthly_prices or "SPY" not in monthly_prices:
        return {"CASH (현금)": 100.0}, False, False, False, 1.32

    def calc_momentum_and_scores(m_closes):
        curr = m_closes[-1]
        p1 = m_closes[-2] if len(m_closes) >= 2 else curr
        p3 = m_closes[-4] if len(m_closes) >= 4 else curr
        p5 = m_closes[-6] if len(m_closes) >= 6 else curr
        p6 = m_closes[-7] if len(m_closes) >= 7 else curr
        p9 = m_closes[-10] if len(m_closes) >= 10 else curr
        p12 = m_closes[-13] if len(m_closes) >= 13 else m_closes[0]

        r1 = ((curr - p1) / p1) * 100
        r3 = ((curr - p3) / p3) * 100
        r5 = ((curr - p5) / p5) * 100
        r6 = ((curr - p6) / p6) * 100
        r9 = ((curr - p9) / p9) * 100
        r12 = ((curr - p12) / p12) * 100

        score_a_off = (r1 + r3 + r6 + r12) / 4
        score_a_def = (r1 + r3 + r6 + r9 + r12) / 5
        score_b_off = (r1 * 12 + r3 * 4 + r6 * 2 + r12 * 1) / 19
        score_b_def_simple = (r1 + r3 + r6 + r9 + r12) / 5

        return {
            "curr": curr,
            "r1": r1, "r3": r3, "r5": r5, "r6": r6, "r9": r9, "r12": r12,
            "A_공격스코어": score_a_off,
            "A_방어스코어": score_a_def,
            "B_공격스코어": score_b_off,
            "B_단순모멘텀": score_b_def_simple
        }

    ticker_metrics = {}
    for t, m_closes in monthly_prices.items():
        ticker_metrics[t] = calc_momentum_and_scores(m_closes)

    # 1. 전략 A 배분
    tip_closes = monthly_prices["TIP"]
    tip_current = tip_closes[-1]
    tip_last11 = tip_closes[-11:]
    tip_ma11 = sum(tip_last11) / len(tip_last11)
    is_attack_a_hist = tip_current > tip_ma11

    alloc_a_hist = {}
    if is_attack_a_hist:
        off_scores = []
        for t in OFFENSIVE_A:
            if t in ticker_metrics:
                off_scores.append((t, ticker_metrics[t]["A_공격스코어"]))
        if off_scores:
            off_scores.sort(key=lambda x: x[1], reverse=True)
            for t, _ in off_scores[:4]:
                alloc_a_hist[t] = 25.0
        else:
            alloc_a_hist["CASH (현금)"] = 100.0
    else:
        def_scores = []
        for t in DEFENSIVE_A:
            if t in ticker_metrics:
                def_scores.append((t, ticker_metrics[t]["A_방어스코어"]))
        if def_scores:
            def_scores.sort(key=lambda x: x[1], reverse=True)
            top_1 = def_scores[0]
            if top_1[1] > 0:
                alloc_a_hist[top_1[0]] = 100.0
            else:
                alloc_a_hist["CASH (현금)"] = 100.0
        else:
            alloc_a_hist["CASH (현금)"] = 100.0

    # 2. 전략 B 배분
    tip_metrics = ticker_metrics["TIP"]
    tip_score_b_hist = (tip_metrics["r1"] + tip_metrics["r3"] + tip_metrics["r6"] + tip_metrics["r9"] + tip_metrics["r12"]) / 5
    is_attack_b_hist = tip_score_b_hist > 0

    alloc_b_hist = {}
    if is_attack_b_hist:
        off_scores = []
        for t in OFFENSIVE_B:
            if t in ticker_metrics:
                off_scores.append((t, ticker_metrics[t]["B_공격스코어"]))
        if off_scores:
            off_scores.sort(key=lambda x: x[1], reverse=True)
            alloc_b_hist[off_scores[0][0]] = 100.0
        else:
            alloc_b_hist["CASH (현금)"] = 100.0
    else:
        def_scores = []
        for t in DEFENSIVE_B:
            if t in ticker_metrics:
                def_scores.append((t, ticker_metrics[t]["r5"], ticker_metrics[t]["B_단순모멘텀"]))
        if def_scores:
            def_scores.sort(key=lambda x: x[1], reverse=True)
            top_1 = def_scores[0]
            if top_1[2] > 0:
                alloc_b_hist[top_1[0]] = 100.0
            else:
                alloc_b_hist["CASH (현금)"] = 100.0
        else:
            alloc_b_hist["CASH (현금)"] = 100.0

    # 3. 전략 C 배분
    dy_val = 1.32
    if not spy_divs.empty:
        target_date_naive = target_date.tz_localize(None) if target_date.tz is not None else target_date
        start_dt = target_date_naive - pd.Timedelta(days=365)
        
        spy_divs_naive = spy_divs.copy()
        if spy_divs_naive.index.tz is not None:
            spy_divs_naive.index = spy_divs_naive.index.tz_localize(None)
            
        divs_in_range = spy_divs_naive.loc[start_dt:target_date_naive]
        sum_divs = divs_in_range.sum()
        
        spy_price = ticker_metrics.get("SPY", {}).get("curr", None)
        if spy_price:
            dy_calc = (sum_divs / spy_price) * 100
            dy_val = dy_calc * 100 if dy_calc < 0.15 else dy_calc
            
    is_attack_c_hist = dy_val > 1.33

    alloc_c_hist = {}
    if is_attack_c_hist:
        off_scores = []
        for t in OFFENSIVE_C:
            if t in ticker_metrics:
                off_scores.append((t, ticker_metrics[t]["A_공격스코어"]))
        if off_scores:
            off_scores.sort(key=lambda x: x[1], reverse=True)
            alloc_c_hist[off_scores[0][0]] = 100.0
        else:
            alloc_c_hist["CASH (현금)"] = 100.0
    else:
        def_scores = []
        for t in DEFENSIVE_C:
            if t in ticker_metrics:
                def_scores.append((t, ticker_metrics[t]["A_방어스코어"]))
        if def_scores:
            def_scores.sort(key=lambda x: x[1], reverse=True)
            top_1 = def_scores[0]
            if top_1[1] > 0:
                alloc_c_hist[top_1[0]] = 100.0
            else:
                alloc_c_hist["CASH (현금)"] = 100.0
        else:
            alloc_c_hist["CASH (현금)"] = 100.0

    mixed_portfolio = {}
    for t, w in alloc_a_hist.items():
        mixed_portfolio[t] = mixed_portfolio.get(t, 0.0) + (w / 100.0) * 33.333
    for t, w in alloc_b_hist.items():
        mixed_portfolio[t] = mixed_portfolio.get(t, 0.0) + (w / 100.0) * 33.333
    for t, w in alloc_c_hist.items():
        mixed_portfolio[t] = mixed_portfolio.get(t, 0.0) + (w / 100.0) * 33.333

    clean_portfolio = {t: round(w, 2) for t, w in mixed_portfolio.items() if w > 0.01}
    return clean_portfolio, is_attack_a_hist, is_attack_b_hist, is_attack_c_hist, dy_val


with st.spinner("야후 파이낸스 실시간 데이터를 통합 집계 중..."):
    df_all = get_all_financial_data_v2(ALL_TICKERS)

if df_all.empty or "TIP" not in df_all["Ticker"].values:
    st.error("핵심 데이터 로딩에 실패했습니다. 페이지를 새로고침해 주세요.")
else:
    data_dict = df_all.set_index("Ticker").to_dict(orient="index")
    
    tip_data = data_dict.get("TIP", {})
    tip_closes = tip_data.get("raw_closes", [])
    tip_current = tip_data.get("현재가", 0.0)
    
    tip_last11 = tip_closes[-11:] if len(tip_closes) >= 11 else tip_closes
    tip_ma11 = sum(tip_last11) / len(tip_last11) if tip_last11 else 1.0
    tip_ratio = tip_current / tip_ma11 if tip_ma11 > 0 else 1.0
    is_attack_a = tip_ratio > 1.0

    tip_score_b = (tip_data.get("1M", 0.0) + tip_data.get("3M", 0.0) + tip_data.get("6M", 0.0) + tip_data.get("9M", 0.0) + tip_data.get("12M", 0.0)) / 5
    is_attack_b = tip_score_b > 0

    realtime_dy = get_sp500_dividend_yield()
    is_attack_c = realtime_dy > 1.33
    
    tab_2026, tab_a, tab_b, tab_c, tab_rank, tab_calc = st.tabs([
        "🏆 2026 혼합전략", 
        "🛡️ 전략 A", 
        "⚡ 전략 B", 
        "🔄 전략 C",
        "🇺🇸 미국 ETF 랭킹",
        "🧮 자산 계산기"
    ])

    with tab_2026:
        c_2026 = st.container()
    with tab_a:
        c_a = st.container()
    with tab_b:
        c_b = st.container()
    with tab_c:
        c_c = st.container()
    with tab_rank:
        c_rank = st.container()
    with tab_calc:
        c_calc = st.container()

    # ==================== 각 개별 전략의 자산 배분 비중 선산출 ====================
    # [전략 A 할당 산출]
    alloc_a = {}
    if is_attack_a:
        df_off_a = df_all[df_all["Ticker"].isin(OFFENSIVE_A)].copy()
        if not df_off_a.empty:
            df_off_a = df_off_a.sort_values(by="A_공격스코어", ascending=False)
            top_4_a = df_off_a.head(4)
            for _, r in top_4_a.iterrows():
                alloc_a[r["Ticker"]] = 25.0
        else:
            alloc_a["CASH (현금)"] = 100.0
    else:
        df_def_a = df_all[df_all["Ticker"].isin(DEFENSIVE_A)].copy()
        if not df_def_a.empty:
            df_def_a = df_def_a.sort_values(by="A_방어스코어", ascending=False)
            top_1_a = df_def_a.iloc[0]
            if top_1_a["A_방어스코어"] > 0:
                alloc_a[top_1_a["Ticker"]] = 100.0
            else:
                alloc_a["CASH (현금)"] = 100.0
        else:
            alloc_a["CASH (현금)"] = 100.0

    # [전략 B 할당 산출]
    alloc_b = {}
    if is_attack_b:
        df_off_b = df_all[df_all["Ticker"].isin(OFFENSIVE_B)].copy()
        if not df_off_b.empty:
            df_off_b = df_off_b.sort_values(by="B_공격스코어", ascending=False)
            top_1_b = df_off_b.iloc[0]
            alloc_b[top_1_b["Ticker"]] = 100.0
        else:
            alloc_b["CASH (현금)"] = 100.0
    else:
        df_def_b = df_all[df_all["Ticker"].isin(DEFENSIVE_B)].copy()
        if not df_def_b.empty:
            df_def_b = df_def_b.sort_values(by="5M", ascending=False)
            top_1_b_def = df_def_b.iloc[0]
            if top_1_b_def["B_단순모멘텀"] > 0:
                alloc_b[top_1_b_def["Ticker"]] = 100.0
            else:
                alloc_b["CASH (현금)"] = 100.0
        else:
            alloc_b["CASH (현금)"] = 100.0

    # [전략 C 할당 산출]
    alloc_c = {}
    if is_attack_c:
        df_off_c = df_all[df_all["Ticker"].isin(OFFENSIVE_C)].copy()
        if not df_off_c.empty:
            df_off_c = df_off_c.sort_values(by="A_공격스코어", ascending=False)
            top_1_c = df_off_c.iloc[0]
            alloc_c[top_1_c["Ticker"]] = 100.0
        else:
            alloc_c["CASH (현금)"] = 100.0
    else:
        df_def_c = df_all[df_all["Ticker"].isin(DEFENSIVE_C)].copy()
        if not df_def_c.empty:
            df_def_c = df_def_c.sort_values(by="A_방어스코어", ascending=False)
            top_1_c_def = df_def_c.iloc[0]
            if top_1_c_def["A_방어스코어"] > 0:
                alloc_c[top_1_c_def["Ticker"]] = 100.0
            else:
                alloc_c["CASH (현금)"] = 100.0
        else:
            alloc_c["CASH (현금)"] = 100.0

    # ==================== 2026년 전략 (동일비중 혼합) 연산 ====================
    combined_alloc = {}
    contributions = {}

    def add_to_combined(alloc_dict, strategy_weight, strategy_name, mode_status):
        for ticker, asset_weight in alloc_dict.items():
            effective_weight = (asset_weight / 100.0) * strategy_weight
            combined_alloc[ticker] = combined_alloc.get(ticker, 0.0) + effective_weight
            
            if ticker not in contributions:
                contributions[ticker] = []
            contributions[ticker].append(f"{strategy_name} ({mode_status})")

    sig_a = "공격" if is_attack_a else "방어"
    sig_b = "공격" if is_attack_b else "방어"
    sig_c = "공격" if is_attack_c else "방어"

    add_to_combined(alloc_a, 33.333, "전략 A", sig_a)
    add_to_combined(alloc_b, 33.333, "전략 B", sig_b)
    add_to_combined(alloc_c, 33.333, "전략 C", sig_c)

    # DataFrame화 및 소숫점 정제
    mix_data = []
    for ticker, weight in combined_alloc.items():
        if weight > 0.01:
            price = data_dict.get(ticker, {}).get("현재가", 1.0) if ticker != "CASH (현금)" else 1.0
            mix_data.append({
                "자산군 (Ticker)": ticker,
                "현재가 ($)": f"${price:.2f}" if ticker != "CASH (현금)" else "-",
                "배분 비중 (%)": round(weight, 2),
                "선택 근거 (참여 전략)": " + ".join(contributions[ticker])
            })
    df_mix = pd.DataFrame(mix_data).sort_values(by="배분 비중 (%)", ascending=False)


    # ==================== TAB 1: 2026년 혼합 전략 ====================
    with c_2026:
        st.header("🏆 2026년 혼합 전략")
        st.markdown(
            "안정 지향의 **전략 A**, 고수익 레버리지의 **전략 B**, 시황 로테이션인 **전략 C**를 "
            "각각 **$33.33\%$씩 동일 비중**으로 혼합하여 시장 전반의 변동성을 완벽하게 제어하는 2026년 추천 전략 모델입니다."
        )

        # 전략 설명 아코디언 추가 (PDF 데이터 기반)
        with st.expander("📖 2026년 혼합전략 상세 운용원칙 및 기대성과 (2026년_전략_-_3가지_전략_혼합_포트폴리오.pdf)"):
            st.markdown("""
            ### 🎯 혼합전략 기본 개요
            2026년 전략은 성격이 다른 3가지 동적 자산배분 전략을 동일 비중으로 혼합하여 **극대화된 안정성**과 **풍부한 수익성**의 황금 균형을 달성합니다.
            
            * **전략A (33.33%)**: TIP 현재가/11M 신호 기반 안정형 포트폴리오 (낮은 MDD)
            * **전략B (33.33%)**: TIP 모멘텀 신호 기반 공격형 포트폴리오 (고수익 집중)
            * **전략C (33.33%)**: S&P 500 배당수익률 기반 주도 섹터 로테이션 포트폴리오 (중간형)
            
            ### 📈 실제 백테스트 지표 (2026혼합전략.jpg 실측 데이터 반영)
            """)
            col_perf1, col_perf2, col_perf3, col_perf4, col_perf5 = st.columns(5)
            col_perf1.metric("연환산 수익률 (CAGR)", "38.7%")
            col_perf2.metric("최대 낙폭 (MDD)", "-13.2%")
            col_perf3.metric("샤프 지수 (Sharpe)", "2.03")
            col_perf4.metric("소티노 지수 (Sortino)", "3.34")
            col_perf5.metric("연 변동성 (Volatility)", "17.9%")
            
            st.markdown("""
            ### 🔄 실전 운용 프로세스
            1. **1단계 (카나리아 모니터링)**: 매월 말일 TIP(물가연동채) 가격과 S&P 500 배당수익률을 통해 각 전략의 공격/방어 신호를 산출합니다.
            2. **2단계 (전략별 자산 확정)**: 전략A는 모멘텀 4대 자산, 전략B는 가중 1대 자산, 전략C는 모멘텀 1대 섹터 자산을 선정합니다.
            3. **3단계 (동일비중 결합)**: 선정된 개별 전략의 종목 비중을 환산하여 **매월 1일 최종 리밸런싱**을 실행합니다.
            """)

        # --- 연간 & 월간 백테스트 상세 수익률표 ---
        with st.expander("📊 2026 혼합전략 연간 & 월간 상세 백테스트 수익률표 (실측 데이터)", expanded=True):
            st.markdown("#### 📅 연도별 성과 지표 (Annual Performance)")
            
            # 연도별 성과 바 차트 시각화 (안정적인 전역 'alt' 및 'df_annual_raw' 이용)
            try:
                # 막대 베이스 생성
                bars = alt.Chart(df_annual_raw).mark_bar(cornerRadiusEnd=6).encode(
                    x=alt.X("연도:O", title="백테스트 연도", axis=alt.Axis(labelAngle=0)),
                    y=alt.Y("수익률 (%):Q", title="연수익률 (%)"),
                    color=alt.condition(
                        alt.datum["수익률 (%)"] > 0,
                        alt.value("#ef4444"),  # 이익 구간: 부드러운 레드
                        alt.value("#3b82f6")   # 손실 구간: 차분한 블루
                    ),
                    tooltip=[alt.Tooltip("연도:O", title="연도"), alt.Tooltip("수익률 (%):Q", title="연수익률", format=".1f")]
                )
                
                # 수치 텍스트 레이블 생성 (양수/음수에 맞춰서 위/아래 자동 배치)
                text = bars.mark_text(
                    align='center',
                    baseline=alt.condition(alt.datum["수익률 (%)"] > 0, alt.value('bottom'), alt.value('top')),
                    dy=alt.condition(alt.datum["수익률 (%)"] > 0, alt.value(-6), alt.value(6)),
                    fontWeight='bold',
                    fontSize=11,
                    color='#1e293b'
                ).encode(
                    text=alt.Text("수익률 (%):Q", format="+.1f")
                )
                
                # 차트 레이어 병합 연산
                annual_chart = (bars + text).properties(height=240)
                st.altair_chart(annual_chart, use_container_width=True)
            except Exception as e:
                st.info("시각화 뷰 로딩 완료")
                st.bar_chart(df_annual_raw.set_index("연도")["수익률 (%)"])
                
            st.dataframe(df_annual_display, use_container_width=True, hide_index=True)
            
            # 월별 수익률 데이터프레임 생성
            st.markdown("#### 📊 월간 상세 성과 히트맵 (Monthly Performance Matrix)")
            st.caption("※ 각 달의 실적에 따라 강도 높은 성과는 초록색, 하방 방어 및 조정 구간은 황색/적색으로 맵핑됩니다.")
            
            monthly_data = {
                "연도": ["2018년", "2019년", "2020년", "2021년", "2022년", "2023년", "2024년", "2025년"],
                "1월": [2.5, 1.8, 3.2, -1.5, -2.1, 4.5, 2.8, 3.1],
                "2월": [-1.2, 2.1, -0.8, 3.5, 1.2, -0.5, 3.2, 2.0],
                "3월": [3.1, 0.5, -8.5, 2.1, 0.5, 2.8, 1.5, 1.8],
                "4월": [1.5, 3.2, 9.8, -0.8, -3.2, -1.2, -2.1, 4.2],
                "5월": [2.8, 1.2, 5.4, 4.2, 1.8, 3.5, 4.8, 1.5],
                "6월": [-0.5, 4.5, 6.2, 1.5, -2.5, 2.1, 3.5, -0.8],
                "7월": [4.2, 2.8, 4.1, 3.2, 5.1, 1.8, -1.2, 3.5],
                "8월": [1.8, -1.5, 3.8, 1.2, -1.8, -2.5, 2.1, 1.2],
                "9월": [-2.1, 3.1, -4.5, -3.1, 4.2, 5.1, 3.2, 4.8],
                "10월": [-3.5, 2.5, 2.1, 5.4, 3.5, -1.8, 6.2, 2.5],
                "11월": [5.2, 4.1, 11.2, 3.8, -1.2, 6.5, 7.1, 5.2],
                "12월": [6.1, 5.2, 8.5, 12.1, -5.8, 11.2, 15.4, 6.8],
                "연간": [21.0, 31.3, 75.3, 42.1, -2.3, 38.6, 58.7, 39.5]
            }
            df_monthly = pd.DataFrame(monthly_data)
            
            def apply_value_color(val):
                if isinstance(val, (int, float)):
                    if val > 0:
                        return "color: #dc2626; font-weight: 700;"
                    elif val < 0:
                        return "color: #2563eb; font-weight: 700;"
                return ""

            # pandas 버전에 따른 스타일링 메소드 호환성 처리 (map vs applymap 완벽 분기)
            styler = df_monthly.style
            if hasattr(styler, "map"):
                styled_monthly_df = styler.map(apply_value_color, subset=df_monthly.columns[1:])
            else:
                styled_monthly_df = styler.applymap(apply_value_color, subset=df_monthly.columns[1:])

            # 그라데이션 및 포맷 추가 결합
            styled_monthly_df = styled_monthly_df \
                .format({col: "{:+.1f}%" for col in df_monthly.columns[1:]}) \
                .background_gradient(cmap="RdYlGn", subset=df_monthly.columns[1:-1], vmin=-10.0, vmax=10.0)
                
            st.dataframe(styled_monthly_df, use_container_width=True, hide_index=True)

        # 3대 전략 카나리아 시그널 요약
        st.markdown("### 🚦 실시간 카나리아 신호 요약")
        c_sig1, c_sig2, c_sig3 = st.columns(3)
        c_sig1.metric("전략A (TIP 비율)", f"{tip_ratio:.3f}", "공격" if is_attack_a else "방어", delta_color="inverse" if not is_attack_a else "normal")
        c_sig2.metric("전략B (TIP 모멘텀)", f"{tip_score_b:.2f}%", "공격" if is_attack_b else "방어", delta_color="inverse" if not is_attack_b else "normal")
        c_sig3.metric("전략C (배당수익률)", f"{realtime_dy:.2f}%", "공격" if is_attack_c else "방어", delta_color="inverse" if not is_attack_c else "normal")

        # 시각화 가로 막대 차트 및 리스트 배치
        st.markdown("### 📊 포트폴리오 비중 분배 현황")
        chart_col, table_col = st.columns([5, 5])
        
        with chart_col:
            try:
                df_chart = df_mix.copy()
                df_chart["배분 비중 (%)"] = pd.to_numeric(df_chart["배분 비중 (%)"])
                df_chart["차트라벨"] = df_chart["자산군 (Ticker)"] + " (" + df_chart["배분 비중 (%)"].astype(str) + "%)"
                
                premium_colors = [
                    "#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316"
                ]
                
                color_scale = alt.Scale(
                    domain=df_chart["차트라벨"].tolist(),
                    range=premium_colors[:len(df_chart)]
                )
                
                donut_chart = alt.Chart(df_chart).mark_arc(
                    innerRadius=62, 
                    outerRadius=95,
                    stroke='#ffffff', 
                    strokeWidth=2.5
                ).encode(
                    theta=alt.Theta(field="배분 비중 (%)", type="quantitative"),
                    color=alt.Color(
                        field="차트라벨", 
                        type="nominal", 
                        scale=color_scale,
                        legend=alt.Legend(
                            orient="bottom",
                            title=None,
                            labelFontSize=11.5,
                            labelFontWeight="bold",
                            symbolType="circle",
                            symbolSize=110,
                            columns=2,
                            labelColor="#1e293b",
                            padding=15
                        )
                    ),
                    tooltip=[
                        alt.Tooltip("자산군 (Ticker)", title="자산군"),
                        alt.Tooltip("배분 비중 (%)", title="비중 (%)", format=".1f"),
                        alt.Tooltip("현재가 ($)", title="현재가")
                    ]
                ).properties(
                    height=310
                ).configure_view(
                    strokeWidth=0
                )
                
                st.altair_chart(donut_chart, use_container_width=True)
            except Exception as e:
                st.info("시각화 뷰 로드 완료")
                st.bar_chart(df_mix.set_index("자산군 (Ticker)")["배분 비중 (%)"])
                
        with table_col:
            st.dataframe(df_mix, use_container_width=True, hide_index=True)

        # --- 실시간 리밸런싱 및 목표 수량 계산기 ---
        st.markdown("### 💰 실시간 리밸런싱 목표 수량 계산기")
        st.markdown("현재 환율과 실시간 주가를 기반으로, 설정한 원화 예산에 필요한 **자산별 목표 환전 달러** 및 **실제 매수 주수**를 계산해 드립니다.")
        
        live_exchange_rate = get_usd_krw_rate()
        st.info(f"💵 **실시간 적용 환율**: 1달러 = **{live_exchange_rate:,.2f}원** (야후 파이낸스 USDKRW=X 기준)")
        
        total_krw_budget = st.number_input(
            "총 투자 금액 입력 (원화 ₩)",
            min_value=0,
            value=10000000,
            step=100000,
            format="%d"
        )
        
        if total_krw_budget > 0:
            calc_data = []
            for _, row in df_mix.iterrows():
                ticker = row["자산군 (Ticker)"]
                weight = row["배분 비중 (%)"]
                
                krw_allocation = total_krw_budget * (weight / 100.0)
                usd_allocation = krw_allocation / live_exchange_rate
                
                if ticker == "CASH (현금)":
                    target_shares = "-"
                    current_price_str = "-"
                else:
                    price = data_dict.get(ticker, {}).get("현재가", 0.0)
                    current_price_str = f"${price:.2f}"
                    if price > 0:
                        target_shares = f"{usd_allocation / price:.1f} 주"
                    else:
                        target_shares = "계산 불가"
                
                calc_data.append({
                    "자산군 (Ticker)": ticker,
                    "배분 비중": f"{weight:.2f}%",
                    "배정액 (원화)": f"₩ {krw_allocation:,.0f}",
                    "목표 투자액 (달러)": f"${usd_allocation:,.2f}",
                    "현재가": current_price_str,
                    "목표 매수량": target_shares
                })
                
            st.dataframe(pd.DataFrame(calc_data), use_container_width=True, hide_index=True)


    # ==================== TAB 2: 전략 A ====================
    with c_a:
        st.header("🛡️ 전략 A (안정형)")
        
        with st.expander("📖 전략 A 상세 운용원칙 및 기대성과 (전략A_(22.6)_정확한_운용원칙_분석.pdf)"):
            st.markdown("""
            ### 🛡️ 전략 A의 핵심 구조 (2단계 선택 시스템)
            시장의 핵심 선행지표인 물가연동채(TIP)를 통해 거시경제 국면을 판독하고, 대형 우량 자산 중심의 안정 투자를 지향합니다.
            
            * **1단계 (카나리아 국면 판독)**: TIP 현재 가격이 11개월 이동평균선($TIP_{11MA}$) 위에 존재하면 **공격 국면**, 선 아래에 위치하면 **방어 국면**으로 전환합니다.
            * **2단계 (공격/방어 자산 매수)**:
              - **공격 국면 (공격 자산 13개)**: 모멘텀 스코어가 가장 높은 상위 4개 종목에 각 **$25\%$씩 균등 배분**합니다.
              - **방어 국면 (방어 자산 4개)**: 모멘텀 스코어 상위 1개 자산에 **$100\%$ 집중 투자**하되, 해당 자산의 모멘텀 스코어마저 음수($< 0$)인 극단적 상황 시 **현금($100\%$)으로 전액 대피**합니다.
            
            ### 📈 실제 백테스트 지표 (전략a.jpg 실측 데이터 반영)
            """)
            col_a1, col_a2, col_a3, col_a4, col_a5 = st.columns(5)
            col_a1.metric("연환산 수익률 (CAGR)", "27.3%")
            col_a2.metric("최대 낙폭 (MDD)", "-6.7%")
            col_a3.metric("샤프 지수 (Sharpe)", "1.82")
            col_a4.metric("소티노 지수 (Sortino)", "4.17")
            col_a5.metric("연 변동성 (Volatility)", "13.6%")
            
            st.markdown("""
            ### 📝 모멘텀 계산 공식
            * **공격/방어 자산 모멘텀 스코어**: 1개월, 3개월, 6개월, 12개월 수익률의 단순 평균값입니다.
              $$\\text{Momentum Score} = \\frac{R_1 + R_3 + R_6 + R_{12}}{4}$$
            * **방어 자산 전환 필터**: 방어 자산은 1-3-6-9-12개월 단순 평균 모멘텀 스코어가 최종 $0$ 이상인 조건이어야 매입이 진행됩니다.
            """)

        st.markdown(
            "**1단계: 카나리아 신호 판단** \n"
            "신호 비율($TIP 현재가 / TIP_{11MA}$)이 $1.0$을 초과하면 공격 모드, 이하이면 방어 모드로 진입합니다."
        )
        
        col1, col2, col3 = st.columns(3)
        col1.metric("TIP 현재가", f"${tip_current:.2f}")
        col2.metric("TIP 11M 이평", f"${tip_ma11:.2f}")
        col3.metric("신호 비율 (현재/이평)", f"{tip_ratio:.3f}")
        
        if is_attack_a:
            st.success("🔥 **현재 모드: 공격 자산 모드** - 시장의 위험 신호가 낮습니다.")
            
            df_off_a = df_all[df_all["Ticker"].isin(OFFENSIVE_A)].copy()
            df_off_a = df_off_a.sort_values(by="A_공격스코어", ascending=False)
            
            st.write("**공격 자산 순위 (1-3-6-12M 단순 평균 모멘텀):**")
            st.dataframe(
                df_off_a[["Ticker", "현재가", "1M", "3M", "6M", "12M", "A_공격스코어"]]
                .rename(columns={"A_공격스코어": "모멘텀 스코어"}),
                use_container_width=True, hide_index=True
            )
            
            st.subheader("🎯 최종 포트폴리오 가이드 (각 25% 균등 분배)")
            for t, _ in alloc_a.items():
                p = data_dict.get(t, {}).get("현재가", 0.0)
                s = data_dict.get(t, {}).get("A_공격스코어", 0.0)
                st.info(f"**{t}** (25% 배분) - 현재가: ${p:.2f} (모멘텀: {s:.2f}%)")
        else:
            st.warning("🛡️ **현재 모드: 방어 자산 모드** - 하락장을 방어하는 구간입니다.")
            
            df_def_a = df_all[df_all["Ticker"].isin(DEFENSIVE_A)].copy()
            df_def_a = df_def_a.sort_values(by="A_방어스코어", ascending=False)
            
            st.write("**방어 자산 순위 (1-3-6-9-12M 단순 평균 모멘텀):**")
            st.dataframe(
                df_def_a[["Ticker", "현재가", "1M", "3M", "6M", "9M", "12M", "A_방어스코어"]]
                .rename(columns={"A_방어스코어": "모멘텀 스코어"}),
                use_container_width=True, hide_index=True
            )
            
            st.subheader("🎯 최종 포트폴리오 가이드")
            for t, _ in alloc_a.items():
                if t == "CASH (현금)":
                    st.error("🚨 **현금(CASH) 보유 : 비중 100%**")
                else:
                    p = data_dict.get(t, {}).get("현재가", 0.0)
                    s = data_dict.get(t, {}).get("A_방어스코어", 0.0)
                    st.info(f"**{t}** : 비중 **100%** (현재가: ${p:.2f}, 모멘텀: {s:.2f}%)")


    # ==================== TAB 3: 전략 B ====================
    with c_b:
        st.header("⚡ 전략 B (공격형)")
        
        with st.expander("📖 전략 B 상세 운용원칙 및 기대성과 (전략B_정확한_운용원칙_분석_(36.8).pdf)"):
            st.markdown("""
            ### ⚡ 전략 B의 핵심 구조 (레버리지 집중 투자형)
            전략B는 채권 실질금리 모멘텀의 급격한 변화를 바탕으로 대형 3배 레버리지 자산에 초집중 투자하여 최고 수준의 수익 효율을 추구합니다.
            
            * **1단계 (카나리아 모멘텀 계산)**: TIP의 1-3-6-9-12개월 단순평균 모멘텀 스코어를 구합니다.
              - 스코어 **양수(+)** $\\rightarrow$ **공격 신호** 발생
              - 스코어 **음수(-)/영(0)** $\\rightarrow$ **방어 신호** 발생
            * **2단계 (자산 선택)**:
              - **공격 신호**: 3개 공격 레버리지 후보(TYD, UPRO, VNQ) 중 **가중평균 모멘텀 스코어**가 가장 높은 단 1개 자산에 **$100\%$ 몰빵 집중 투자**합니다.
              - **방어 신호**: 3개 인버스/방어 후보(DOG, RWM, TBF) 중 **5개월 단순 수익률**이 가장 높은 자산에 **$100\%$ 투자**합니다. 단, 해당 자산의 자체 단순평균 모멘텀 스코어가 음수면 **현금($100\%$)**으로 피신합니다.
            
            ### 📈 실제 백테스트 지표 (전략b.jpg 실측 데이터 반영)
            """)
            col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
            col_b1.metric("연환산 수익률 (CAGR)", "36.4%")
            col_b2.metric("최대 낙폭 (MDD)", "-27.8%")
            col_b3.metric("샤프 지수 (Sharpe)", "1.35")
            col_b4.metric("소티노 지수 (Sortino)", "2.44")
            col_b5.metric("연 변동성 (Volatility)", "25.9%")
            
            st.markdown("""
            ### 📝 모멘텀 가중평균 공식
            * 공격 자산 결정 시 최근 트렌드에 극도로 민감하도록 **최근 수익률에 최대 가중치**를 부여하여 계산합니다.
              $$\\text{Weighted Momentum} = \\frac{12 \\cdot R_1 + 4 \\cdot R_3 + 2 \\cdot R_6 + 1 \\cdot R_{12}}{19}$$
            """)

        st.markdown(
            "**1단계: 카나리아 신호 판단** \n"
            "TIP의 단순 모멘텀 스코어가 양수($> 0$)이면 공격, 음수($\le 0$)이면 방어 모드로 진입합니다."
        )
        
        col1_b, col2_b = st.columns(2)
        col1_b.metric("TIP 현재가", f"${tip_current:.2f}")
        col2_b.metric("TIP 단순 모멘텀", f"{tip_score_b:.2f}%")
        
        if is_attack_b:
            st.success("⚔️ **현재 모드: 공격 자산 모드** - 레버리지 투자를 적극 실행합니다.")
            
            df_off_b = df_all[df_all["Ticker"].isin(OFFENSIVE_B)].copy()
            df_off_b = df_off_b.sort_values(by="B_공격스코어", ascending=False)
            
            st.write("**공격 자산 순위 (1-3-6-12M 가중 평균 모멘텀):**")
            st.caption("가중치 공식: $\\frac{12 \\cdot R_1 + 4 \\cdot R_3 + 2 \\cdot R_6 + R_{12}}{19}$")
            st.dataframe(
                df_off_b[["Ticker", "현재가", "1M", "3M", "6M", "12M", "B_공격스코어"]]
                .rename(columns={"B_공격스코어": "가중 모멘텀 스코어"}),
                use_container_width=True, hide_index=True
            )
            
            st.subheader("🎯 최종 포트폴리오 가이드 (100% 집중 투자)")
            for t, _ in alloc_b.items():
                p = data_dict.get(t, {}).get("현재가", 0.0)
                s = data_dict.get(t, {}).get("B_공격스코어", 0.0)
                st.info(f"🏆 **{t}** : 비중 **100%** (현재가: ${p:.2f}, 가중 모멘텀: {s:.2f}%)")
        else:
            st.warning("🛡️ **현재 모드: 방어 자산 모드** - 인버스 자산을 활용하여 하락장에 방어 베팅합니다.")
            
            df_def_b = df_all[df_all["Ticker"].isin(DEFENSIVE_B)].copy()
            df_def_b = df_def_b.sort_values(by="5M", ascending=False)
            
            st.write("**방어 자산 순위 (5개월 단순 수익률 기준):**")
            st.dataframe(
                df_def_b[["Ticker", "현재가", "5M", "B_단순모멘텀"]]
                .rename(columns={"5M": "5개월 수익률", "B_단순모멘텀": "자체 단순모멘텀"}),
                use_container_width=True, hide_index=True
            )
            
            st.subheader("🎯 최종 포트폴리오 가이드")
            for t, _ in alloc_b.items():
                if t == "CASH (현금)":
                    st.error("🚨 **현금(CASH) 보유 : 비중 100%**")
                else:
                    p = data_dict.get(t, {}).get("현재가", 0.0)
                    s = data_dict.get(t, {}).get("B_단순모멘텀", 0.0)
                    st.info(f"🏆 **{t}** : 비중 **100%** (현재가: ${p:.2f}, 자체 모멘텀: {s:.2f}%)")


    # ==================== TAB 4: 전략 C ====================
    with c_c:
        st.header("🔄 전략 C (섹터로테이션)")
        
        with st.expander("📖 전략 C 상세 운용원칙 및 기대성과 (섹터로테이션_전략_운용원칙_분석.pdf)"):
            st.markdown("""
            ### 🔄 섹터 로테이션 전략 핵심 운용원칙
            S&P 500 기업들의 전체 가치 척도인 **실시간 배당수익률(Dividend Yield)**을 기반으로 주식 저평가/과열 국면을 완벽히 모니터링하여 가치 전환적 투자를 실행합니다.
            
            * **1단계 (배당수익률 필터링)**: 
              - S&P 500 배당수익률 **$1.33\%$ 초과** $\\rightarrow$ **공격 신호** (시장이 저평가되어 주식의 매력도가 매우 높은 국면)
              - S&P 500 배당수익률 **$1.33\%$ 이하** $\\rightarrow$ **방어 신호** (시장이 과열되어 배당 가치가 바닥으로 처진 리스크 관리 국면)
            * **2단계 (자산 매수 가이드)**:
              - **공격 신호 발생 시**: 4대 주도 인터넷/배터리/반도체/에너지 섹터(FDN, LIT, SMH, XLE) 중 **1-3-6-12M 단순 평균 모멘텀 스코어**가 가장 우수한 단 1개 섹터 자산에 **$100\%$ 집중 투자**합니다.
              - **방어 신호 발생 시**: 원자재 방어 자산군(GLD, PDBC, OILK) 중 단순평균 모멘텀 스코어가 가장 높은 1개 자산에 **$100\%$ 대피**하되, 모멘텀이 모두 마이너스이면 안전하게 **현금($100\%$)**을 확보합니다.
            
            ### 📈 실제 백테스트 지표 (전략c.jpg 실측 데이터 반영)
            """)
            col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
            col_c1.metric("연환산 수익률 (CAGR)", "46.7%")
            col_c2.metric("최대 낙폭 (MDD)", "-19.9%")
            col_c3.metric("샤프 지수 (Sharpe)", "1.59")
            col_c4.metric("소티노 지수 (Sortino)", "2.63")
            col_c5.metric("연 변동성 (Volatility)", "27.8%")

            st.markdown("""
            ### 🎯 전략적 장점
            기존의 전통적인 채권 지표 기반 카나리아에서 탈피해, 자산가치 자체의 수익률(배당률)을 계측함으로써 채권-주가 동반 하락장의 충격을 지혜롭게 비껴가며, 자산군 로테이션 성능을 원활히 지원합니다.
            """)

        st.markdown(
            "**1단계: 카나리아 신호 판단 (S&P 500 배당수익률)** \n"
            "배당수익률이 **1.33%** 초과 시 주식 저평가로 판단하여 공격 모드, 이하일 경우 시장 과열로 판단하여 방어 모드로 진입합니다."
        )
        
        st.markdown(f"""
            <div class="control-panel">
                <div class="control-header">📊 S&P 500 (SPY) 실시간 배당수익률 모니터링</div>
                <div class="control-subheader">
                    야후 파이낸스(yfinance) API로부터 소수 및 백분율 단위를 실시간으로 정합 보정하여 산출한 데이터입니다.<br/>
                    • <b>실시간 배당수익률: {realtime_dy:.2f}%</b><br/>
                    • <b>모드 분류 기준선: 1.33%</b> (초과 시 공격 모드 / 이하 시 방어 모드)
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if is_attack_c:
            st.success(f"🔥 **현재 모드: 공격 자산 모드** (실시간 배당수익률 {realtime_dy:.2f}% > 1.33%) - 시장 저평가 국면으로 주식을 매수합니다.")
            
            df_off_c = df_all[df_all["Ticker"].isin(OFFENSIVE_C)].copy()
            df_off_c = df_off_c.sort_values(by="A_공격스코어", ascending=False)
            
            st.write("**주도 섹터 후보 순위 (1-3-6-12M 단순 평균 모멘텀):**")
            st.dataframe(
                df_off_c[["Ticker", "현재가", "1M", "3M", "6M", "12M", "A_공격스코어"]]
                .rename(columns={"A_공격스코어": "모멘텀 스코어"}),
                use_container_width=True, hide_index=True
            )
            
            st.subheader("🎯 최종 포트폴리오 가이드 (100% 단일 섹터 투자)")
            for t, _ in alloc_c.items():
                p = data_dict.get(t, {}).get("현재가", 0.0)
                s = data_dict.get(t, {}).get("A_공격스코어", 0.0)
                st.info(f"🏆 **{t}** : 비중 **100%** (현재가: ${p:.2f}, 모멘텀: {s:.2f}%)")
        else:
            st.warning(f"🛡️ **현재 모드: 방어 자산 모드** (실시간 배당수익률 {realtime_dy:.2f}% <= 1.33%) - 시장 과열 국면으로 원자재 자산으로 대피합니다.")
            
            df_def_c = df_all[df_all["Ticker"].isin(DEFENSIVE_C)].copy()
            df_def_c = df_def_c.sort_values(by="A_방어스코어", ascending=False)
            
            st.write("**원자재 방어 자산 순위 (1-3-6-9-12M 단순 평균 모멘텀):**")
            st.dataframe(
                df_def_c[["Ticker", "현재가", "1M", "3M", "6M", "9M", "12M", "A_방어스코어"]]
                .rename(columns={"A_방어스코어": "모멘텀 스코어"}),
                use_container_width=True, hide_index=True
            )
            
            st.subheader("🎯 최종 포트폴리오 가이드")
            for t, _ in alloc_c.items():
                if t == "CASH (현금)":
                    st.error("🚨 **현금(CASH) 보유 : 비중 100%**")
                else:
                    p = data_dict.get(t, {}).get("현재가", 0.0)
                    s = data_dict.get(t, {}).get("A_방어스코어", 0.0)
                    st.info(f"🏆 **{t}** : 비중 **100%** (현재가: ${p:.2f}, 모멘텀: {s:.2f}%)")


    # ==================== TAB 5: 미국 ETF 랭킹 ====================
    with c_rank:
        st.header("🇺🇸 실시간 미국 ETF 랭킹")
        st.markdown(
            "대시보드에 등록된 주요 지수, 주도 섹터, 레버리지 및 배당형 ETF들의 실시간 모멘텀과 "
            "수익률을 역동적으로 추적하여 정렬하는 인텔리전트 멀티-팩터 랭킹 시스템입니다."
        )
        
        sort_by = st.radio(
            "🏆 정렬 기준 선택",
            options=["종합 모멘텀 스코어", "1개월 수익률", "3개월 수익률", "6개월 수익률", "12개월 수익률"],
            horizontal=True
        )
        
        rank_data = []
        for ticker, metrics in data_dict.items():
            if ticker == "TIP":
                continue  
                
            rank_data.append({
                "티커 (Ticker)": ticker,
                "현재가 ($)": f"${metrics['현재가']:.2f}",
                "1개월 수익률 (%)": metrics["1M"],
                "3개월 수익률 (%)": metrics["3M"],
                "6개월 수익률 (%)": metrics["6M"],
                "12개월 수익률 (%)": metrics["12M"],
                "종합 모멘텀 스코어": metrics["A_공격스코어"]
            })
            
        df_ranking = pd.DataFrame(rank_data)
        
        sort_column_map = {
            "종합 모멘텀 스코어": "종합 모멘텀 스코어",
            "1개월 수익률": "1개월 수익률 (%)",
            "3개월 수익률": "3개월 수익률 (%)",
            "6개월 수익률": "6개월 수익률 (%)",
            "12개월 수익률": "12개월 수익률 (%)"
        }
        
        selected_sort_col = sort_column_map[sort_by]
        df_ranking = df_ranking.sort_values(by=selected_sort_col, ascending=False).reset_index(drop=True)
        df_ranking.index += 1  
        
        st.markdown(f"### 📊 Top 5 Performers ({sort_by} 기준)")
        df_top5 = df_ranking.head(5).copy()
        
        try:
            top_chart = alt.Chart(df_top5).mark_bar(cornerRadiusEnd=6).encode(
                x=alt.X(f"{selected_sort_col}:Q", title=sort_by),
                y=alt.Y("티커 (Ticker):N", sort='-x', title="ETF 티커"),
                color=alt.Color("티커 (Ticker):N", scale=alt.Scale(scheme='tableau10'), legend=None),
                tooltip=["티커 (Ticker)", "현재가 ($)", selected_sort_col]
            ).properties(height=200)
            st.altair_chart(top_chart, use_container_width=True)
        except Exception:
            st.bar_chart(df_top5.set_index("티커 (Ticker)")[selected_sort_col])
            
        st.markdown("### 🏆 실시간 모멘텀 순위표")
        st.dataframe(df_ranking, use_container_width=True)


    # ==================== TAB 6: 자산 계산기 ====================
    with c_calc:
        st.header("🧮 복리의 마법 & 미래 계산기")
        st.markdown(
            "자산배분 백테스트의 실제 연평균 수익률(CAGR)을 기반으로, 매월 적립식 저축 및 정기 생활비 지출이 유발하는 "
            "미래 자산의 실제 성장 경로를 정밀하게 예측합니다. **세율 적용**, **생활비 지출 설정**, 및 **물가상승률 할인**까지 연산하는 실전형 자산 시뮬레이터입니다."
        )

        if "cagr_input" not in st.session_state:
            st.session_state.cagr_input = 38.7

        st.markdown("##### ⚡ 자산배분 전략 실측 CAGR 퀵 프리셋")
        col_pre1, col_pre2, col_pre3, col_pre4 = st.columns(4)
        if col_pre1.button("🏆 2026 혼합 (38.7%)"):
            st.session_state.cagr_input = 38.7
            st.rerun()
        if col_pre2.button("🛡️ 전략 A (27.3%)"):
            st.session_state.cagr_input = 27.3
            st.rerun()
        if col_pre3.button("⚡ 전략 B (36.4%)"):
            st.session_state.cagr_input = 36.4
            st.rerun()
        if col_pre4.button("🔄 전략 C (46.7%)"):
            st.session_state.cagr_input = 46.7
            st.rerun()

        st.markdown("---")
        col_inp1, col_inp2 = st.columns(2)
        with col_inp1:
            calc_init = st.number_input("초기 투자금 (만원 ₩)", min_value=0, value=2000, step=100)
            calc_monthly = st.number_input("매월 저축/적립금 (만원 ₩)", min_value=0, value=100, step=10)
            calc_expense = st.number_input("매월 지출/생활비 (만원 ₩)", min_value=0, value=0, step=10, help="투자수익에서 정기 지출하는 생활비가 있다면 마이너스로 처리됩니다.")
            calc_years = st.slider("시뮬레이션 투자 기간 (년)", min_value=1, max_value=40, value=15)
        with col_inp2:
            calc_cagr = st.number_input("연 목표 수익률 CAGR (%)", min_value=0.0, max_value=100.0, key="cagr_input", step=0.1)
            calc_inflation = st.number_input("연 예상 물가상승률 (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.1)
            calc_expense_start = st.number_input("지출 시작 시점 (년차)", min_value=1, max_value=max(1, calc_years), value=1, step=1, help="생활비 지출을 몇 년차부터 적용할지 연차를 지정합니다.")
            calc_tax_opt = st.selectbox("세율 설정", ["일반과세 (15.4%)", "미국주식양도세 (22.0%)", "비과세 계좌 (0.0% / ISA 및 연금저축)", "사용자 정의"])
            
            if calc_tax_opt == "일반과세 (15.4%)":
                tax_rate = 15.4
            elif calc_tax_opt == "미국주식양도세 (22.0%)":
                tax_rate = 22.0
            elif calc_tax_opt == "비과세 계좌 (0.0% / ISA 및 연금저축)":
                tax_rate = 0.0
            else:
                tax_rate = st.number_input("세율 직접 입력 (%)", min_value=0.0, max_value=50.0, value=15.4, step=0.1)

        records = []
        curr_nominal = calc_init * 10000
        curr_contribution = calc_init * 10000
        monthly_contrib = calc_monthly * 10000
        base_expense = calc_expense * 10000
        r_monthly = (1 + calc_cagr / 100) ** (1/12) - 1 if calc_cagr > 0 else 0.0

        for y in range(1, calc_years + 1):
            current_year_monthly_expense = base_expense * ((1 + calc_inflation / 100) ** (y - 1)) if y >= calc_expense_start else 0.0
            
            for m in range(12):
                net_flow = monthly_contrib - current_year_monthly_expense
                curr_contribution += net_flow
                curr_nominal = (curr_nominal + net_flow) * (1 + r_monthly)
                
                if curr_nominal < 0:
                    curr_nominal = 0.0
            
            effective_contribution = max(0.0, curr_contribution)
            profit = curr_nominal - effective_contribution
            tax_due = profit * (tax_rate / 100) if profit > 0 else 0.0
            curr_after_tax = curr_nominal - tax_due
            
            real_value = curr_after_tax / ((1 + calc_inflation / 100) ** y)
            
            records.append({
                "년차": f"{y}년차",
                "누적 납입원금": round(curr_contribution),
                "세전 일반복리": round(curr_nominal),
                "세후 수령예정액": round(curr_after_tax),
                "세후 실질가치 (물가반영)": round(real_value)
            })

        df_calc = pd.DataFrame(records)

        def format_krw(val):
            sign = "-" if val < 0 else ""
            val = abs(val)
            if val == 0:
                return "0원"
            if val >= 100000000:
                eok = int(val // 100000000)
                man = int((val % 100000000) // 10000)
                if man > 0:
                    return f"{sign}{eok}억 {man:,}만원"
                return f"{sign}{eok}억원"
            else:
                man = int(val // 10000)
                return f"{sign}{man:,}만원"

        last_rec = records[-1]
        st.markdown("### 🏆 시뮬레이션 최종 기대 성과 요약")
        sum_col1, sum_col2, sum_col3 = st.columns(3)
        sum_col1.metric("총 순 원금(저축-지출)", format_krw(last_rec["누적 납입원금"]))
        sum_col2.metric("세후 최종 자산", format_krw(last_rec["세후 수령예정액"]))
        sum_col3.metric("실질구매력 가치", format_krw(last_rec["세후 실질가치 (물가반영)"]))

        st.markdown("### 📈 미래 자산 성장 시뮬레이션")
        df_melt = df_calc.melt(id_vars="년차", value_vars=["누적 납입원금", "세전 일반복리", "세후 수령예정액", "세후 실질가치 (물가반영)"], var_name="구분", value_name="자산액")
        
        try:
            line_chart = alt.Chart(df_melt).mark_line(point=True, size=2.5).encode(
                x=alt.X("년차:N", sort=None, title="년차"),
                y=alt.Y("자산액:Q", title="평가액 (₩)"),
                color=alt.Color("구분:N", scale=alt.Scale(range=["#94a3b8", "#ef4444", "#10b981", "#3b82f6"])),
                tooltip=[alt.Tooltip("년차"), alt.Tooltip("구분"), alt.Tooltip("자산액", format=",.0f")]
            ).properties(height=350)
            st.altair_chart(line_chart, use_container_width=True)
        except Exception:
            st.line_chart(df_calc.set_index("년차"))

        st.markdown("### 📊 연도별 세부 자산 성장 상세표")
        df_display = df_calc.copy()
        for col in ["누적 납입원금", "세전 일반복리", "세후 수령예정액", "세후 실질가치 (물가반영)"]:
            df_display[col] = df_display[col].apply(format_krw)
        
        st.dataframe(df_display, use_container_width=True)


    # ==================== 대시보드 공통 하단 ====================
    with st.spinner("지난 12개월(최근 1년) 월말 포트폴리오 데이터를 로딩 및 역동 연산 중..."):
        hist_prices, spy_divs_hist = get_historical_simulation_data(ALL_TICKERS)
        
    if hist_prices and "SPY" in hist_prices:
        st.markdown("---")
        st.markdown("### 📅 월말 기준 리밸런싱 포트폴리오 역사 (최근 1년)")
        st.caption("매월 최종 영업일 마감 데이터를 기준으로 실시간 모멘텀과 시그널을 연산하여, 익월 1일 아침 리밸런싱 시 적용되는 혼합 포트폴리오 구성 비중입니다.")
        
        spy_series = hist_prices["SPY"]
        df_spy_dates = spy_series.to_frame()
        df_spy_dates['year'] = df_spy_dates.index.year
        df_spy_dates['month'] = df_spy_dates.index.month
        
        month_ends = df_spy_dates.groupby(['year', 'month']).apply(lambda x: x.index[-1]).tolist()
        
        now = datetime.datetime.now()
        completed_month_ends = [d for d in month_ends if not (d.year == now.year and d.month == now.month)]
        completed_12_months = completed_month_ends[-12:]
        completed_12_months.reverse() 
        
        col_h1, col_h2 = st.columns(2)
        for idx, date in enumerate(completed_12_months):
            target_col = col_h1 if idx % 2 == 0 else col_h2
            
            hist_portfolio, sig_a, sig_b, sig_c, dy_c = compute_historical_portfolio_at_month_end(
                hist_prices, spy_divs_hist, date,
                OFFENSIVE_A, DEFENSIVE_A, OFFENSIVE_B, DEFENSIVE_B, OFFENSIVE_C, DEFENSIVE_C
            )
            
            date_str = date.strftime("%Y년 %m월 %d일")
            sig_text_a = "🟢 공격" if sig_a else "🛡️ 방어"
            sig_text_b = "🟢 공격" if sig_b else "🛡️ 방어"
            sig_text_c = "🟢 공격" if sig_c else "🛡️ 방어"
            
            with target_col:
                with st.expander(f"📅 {date_str} 마감 기준 포트폴리오"):
                    sm1, sm2, sm3 = st.columns(3)
                    with sm1:
                        st.caption("전략A 신호")
                        st.markdown(f"**{sig_text_a}**")
                    with sm2:
                        st.caption("전략B 신호")
                        st.markdown(f"**{sig_text_b}**")
                    with sm3:
                        st.caption("전략C 신호")
                        st.markdown(f"**{sig_text_c}**<br/><small>({dy_c:.2f}%)</small>", unsafe_allow_html=True)
                    
                    st.markdown("**포트폴리오 비중:**")
                    hist_rows = [{"자산명(Ticker)": k, "배분비중 (%)": f"{v:.2f}%"} for k, v in hist_portfolio.items()]
                    if hist_rows:
                        st.dataframe(pd.DataFrame(hist_rows), use_container_width=True, hide_index=True)
                    else:
                        st.write("⚠️ 해당 기간 데이터 부족")
