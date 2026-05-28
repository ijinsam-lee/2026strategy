import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 모바일 화면에 최적화된 레이아웃 설정
st.set_page_config(page_title="동적 자산배분 대시보드", layout="centered", initial_sidebar_state="collapsed")

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
        color: #64748b !important; /* 슬레이트 그레이 기본 텍스트 */
        border: none !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    /* 선택된 탭 활성화 디자인 */
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important; /* 완전한 흰색 카드로 분리 효과 */
        color: #0f172a !important; /* 깊은 네이비블랙으로 대비 극대화 */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04) !important;
    }
    
    /* 탭 아래 라인 제거 */
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    
    /* 프리미엄 카드 레이아웃 */
    .premium-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03), 0 2px 4px -1px rgba(0, 0, 0, 0.02);
        margin-bottom: 16px;
    }
    
    /* 정보 헤더 가벼운 파스텔블루 박스 */
    .info-box {
        background-color: #f1f5f9;
        border-left: 4px solid #64748b;
        padding: 12px 16px;
        border-radius: 0 12px 12px 0;
        font-size: 13px;
        color: #475569;
        line-height: 1.5;
        margin-bottom: 16px;
    }
    
    /* ETF 랭킹 카드 */
    .etf-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 1. 자산배분용 데이터 캐싱 및 연산 함수군
# -------------------------------------------------------------

@st.cache_data(ttl=86400)  # 자산배분 기본 정보용 캐싱 (하루 보관)
def get_historical_prices(tickers, start_date, end_date):
    """지정한 여러 티커의 일별 종가 데이터를 다운로드해 데이터프레임으로 반환합니다."""
    try:
        data = yf.download(tickers, start=start_date, end=end_date, progress=False)
        if 'Adj Close' in data:
            prices = data['Adj Close']
        else:
            prices = data['Close']
        prices = prices.ffill().bfill()
        return prices
    except Exception as e:
        st.error(f"주가 데이터 수집 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def get_dividend_history(ticker, start_date, end_date):
    """SPY 등 특정 자산의 분배금(배당) 히스토리를 가져옵니다."""
    try:
        ticker_obj = yf.Ticker(ticker)
        divs = ticker_obj.dividends
        if not divs.empty:
            divs = divs.loc[start_date:end_date]
            return pd.Series(divs)
    except Exception as e:
        pass
    return pd.Series(dtype=float)

def compute_historical_portfolio_at_month_end(prices, divs_hist, date_val, off_a, def_a, off_b, def_b, off_c, def_c):
    """
    특정 연월 마감 시점 기준으로 자산배분 전략 신호와 최적 포트폴리오 비중을 연산합니다.
    """
    end_dt = pd.to_datetime(date_val)
    hist_prices = prices.loc[:end_dt]
    
    if hist_prices.empty or len(hist_prices) < 250:
        return {}, False, False, False, 0.0

    current_prices = hist_prices.iloc[-1]
    
    # 1. 12개월 모멘텀 스코어 (또는 수익률) 계산
    # 최근 거래일 대비 약 252영업일(1년) 전의 누적수익률로 간주
    p_now = current_prices
    p_12m = hist_prices.iloc[-250] if len(hist_prices) >= 250 else hist_prices.iloc[0]
    
    ret_12m = (p_now - p_12m) / p_12m
    
    # ------------------
    # 전략 A 신호 산출 (공격자산 vs 방어자산 절대모멘텀)
    # ------------------
    avg_offensive_ret_a = sum(ret_12m.get(tk, 0) for tk in off_a) / len(off_a) if off_a else 0
    sig_a = avg_offensive_ret_a > 0
    portfolio_a = {}
    if sig_a:
        for tk in off_a:
            portfolio_a[tk] = round(1.0 / len(off_a), 3)
    else:
        for tk in def_a:
            portfolio_a[tk] = round(1.0 / len(def_a), 3)
            
    # ------------------
    # 전략 B 신호 산출
    # ------------------
    avg_offensive_ret_b = sum(ret_12m.get(tk, 0) for tk in off_b) / len(off_b) if off_b else 0
    sig_b = avg_offensive_ret_b > 0.02  # 문턱값 2% 가정
    portfolio_b = {}
    if sig_b:
        for tk in off_b:
            portfolio_b[tk] = round(1.0 / len(off_b), 3)
    else:
        for tk in def_b:
            portfolio_b[tk] = round(1.0 / len(def_b), 3)

    # ------------------
    # 전략 C 신호 산출 (배당 매칭 동적모멘텀)
    # ------------------
    spy_divs_12m = 0.0
    if not divs_hist.empty:
        spy_divs_12m = divs_hist.loc[end_dt - pd.DateOffset(years=1):end_dt].sum()
    
    spy_price = current_prices.get("SPY", 1.0)
    dy_c = (spy_divs_12m / spy_price) * 100 if spy_price > 0 else 1.5
    
    avg_offensive_ret_c = sum(ret_12m.get(tk, 0) for tk in off_c) / len(off_c) if off_c else 0
    sig_c = avg_offensive_ret_c > (dy_c / 100.0)
    portfolio_c = {}
    if sig_c:
        for tk in off_c:
            portfolio_c[tk] = round(1.0 / len(off_c), 3)
    else:
        for tk in def_c:
            portfolio_c[tk] = round(1.0 / len(def_c), 3)

    hist_portfolio = {
        "A": portfolio_a,
        "B": portfolio_b,
        "C": portfolio_c
    }
    
    return hist_portfolio, sig_a, sig_b, sig_c, dy_c

# -------------------------------------------------------------
# 2. 미국 ETF 랭킹용 데이터 수집 및 연산 (새로 추가)
# -------------------------------------------------------------

# 대표적인 미국 ETF 목록 및 메타데이터 정의
RANK_ETFS = {
    "SPY": {"name": "S&P 500 Index (미국 대형주)", "category": "주식 (Equity)"},
    "QQQ": {"name": "NASDAQ 100 (미국 기술주)", "category": "주식 (Equity)"},
    "IWM": {"name": "Russell 2000 (미국 중소형주)", "category": "주식 (Equity)"},
    "DIA": {"name": "Dow Jones (미국 우량주)", "category": "주식 (Equity)"},
    "SOXX": {"name": "Semiconductor (반도체)", "category": "주식 (Equity)"},
    "XLK": {"name": "Technology (정보기술)", "category": "주식 (Equity)"},
    "XLF": {"name": "Financials (금융 섹터)", "category": "주식 (Equity)"},
    "XLV": {"name": "Healthcare (헬스케어)", "category": "주식 (Equity)"},
    "XLE": {"name": "Energy (에너지)", "category": "주식 (Equity)"},
    "VEA": {"name": "Developed Markets (선진국 주식)", "category": "주식 (Equity)"},
    "VWO": {"name": "Emerging Markets (신흥국 주식)", "category": "주식 (Equity)"},
    "TLT": {"name": "20+ Year Treasury (미 장기채)", "category": "채권 (Fixed Income)"},
    "IEF": {"name": "7-10 Year Treasury (미 중기채)", "category": "채권 (Fixed Income)"},
    "SHY": {"name": "1-3 Year Treasury (미 단기채)", "category": "채권 (Fixed Income)"},
    "BIL": {"name": "1-3 Month T-Bill (초단기 국채/현금)", "category": "채권 (Fixed Income)"},
    "LQD": {"name": "Investment Grade (회사채)", "category": "채권 (Fixed Income)"},
    "HYG": {"name": "High Yield (고금리 회사채)", "category": "채권 (Fixed Income)"},
    "GLD": {"name": "Gold Trust (금)", "category": "대체자산 (Alternatives)"},
    "DBC": {"name": "Commodity Index (원자재)", "category": "대체자산 (Alternatives)"},
    "VNQ": {"name": "US Real Estate (리츠)", "category": "대체자산 (Alternatives)"}
}

@st.cache_data(ttl=3600)  # API 속도를 높이기 위해 1시간 동안 결과물 캐싱
def get_etf_rankings():
    """대표 미국 ETF들의 기간별 수익률 및 모멘텀 스코어를 계산하여 데이터프레임으로 변환합니다."""
    tickers = list(RANK_ETFS.keys())
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=500)
    
    # 한번에 데이터 다운로드
    data = yf.download(tickers, start=start_date, end=end_date, progress=False)
    
    prices = data['Adj Close'] if 'Adj Close' in data else data['Close']
    prices = prices.ffill().bfill()
    
    results = []
    now_date = prices.index[-1]
    
    for ticker in tickers:
        if ticker not in prices.columns:
            continue
            
        series = prices[ticker]
        current_price = series.iloc[-1]
        
        # 특정 기준일 시점의 근사 가격 구하기
        t_1m = now_date - pd.DateOffset(months=1)
        t_3m = now_date - pd.DateOffset(months=3)
        t_6m = now_date - pd.DateOffset(months=6)
        t_1y = now_date - pd.DateOffset(years=1)
        t_ytd = pd.Timestamp(year=now_date.year, month=1, day=1)
        
        p_1m = series.asof(t_1m) if t_1m >= series.index[0] else series.iloc[0]
        p_3m = series.asof(t_3m) if t_3m >= series.index[0] else series.iloc[0]
        p_6m = series.asof(t_6m) if t_6m >= series.index[0] else series.iloc[0]
        p_1y = series.asof(t_1y) if t_1y >= series.index[0] else series.iloc[0]
        p_ytd = series.asof(t_ytd) if t_ytd >= series.index[0] else series.iloc[0]
        
        # 수익률(%) 연산
        r_1m = ((current_price - p_1m) / p_1m) * 100 if p_1m else 0.0
        r_3m = ((current_price - p_3m) / p_3m) * 100 if p_3m else 0.0
        r_6m = ((current_price - p_6m) / p_6m) * 100 if p_6m else 0.0
        r_1y = ((current_price - p_1y) / p_1y) * 100 if p_1y else 0.0
        r_ytd = ((current_price - p_ytd) / p_ytd) * 100 if p_ytd else 0.0
        
        # 가중 모멘텀 스코어 공식: (12 * 1M) + (4 * 3M) + (2 * 6M) + 12M
        mom_score = (12 * r_1m) + (4 * r_3m) + (2 * r_6m) + r_1y
        
        results.append({
            "티커": ticker,
            "이름": RANK_ETFS[ticker]["name"],
            "카테고리": RANK_ETFS[ticker]["category"],
            "현재가 ($)": round(current_price, 2),
            "1개월 (%)": round(r_1m, 2),
            "3개월 (%)": round(r_3m, 2),
            "6개월 (%)": round(r_6m, 2),
            "1년 (%)": round(r_1y, 2),
            "YTD (%)": round(r_ytd, 2),
            "모멘텀 스코어": round(mom_score, 2)
        })
        
    return pd.DataFrame(results)


# -------------------------------------------------------------
# 3. 사이드바 및 공통 파라미터 영역
# -------------------------------------------------------------

st.title("🎯 동적 자산배분 & ETF 트렌드")

# 사이드바 설정 영역
st.sidebar.header("⚙️ 대시보드 글로벌 설정")

# 자산배분용 티커 리스트 구성
st.sidebar.subheader("1) 전략별 편입 자산군")

OFFENSIVE_A = st.sidebar.text_input("전략A 공격자산 (쉼표구분)", "SPY,QQQ,IWM,VGK,EWJ,EEM,VNQ,GLD,DBC,HYG,LQD").split(",")
DEFENSIVE_A = st.sidebar.text_input("전략A 방어자산 (쉼표구분)", "BIL,IEF,TLT,SHY").split(",")

OFFENSIVE_B = st.sidebar.text_input("전략B 공격자산 (쉼표구분)", "SPY,QQQ,VNQ,GLD").split(",")
DEFENSIVE_B = st.sidebar.text_input("전략B 방어자산 (쉼표구분)", "BIL,IEF").split(",")

OFFENSIVE_C = st.sidebar.text_input("전략C 공격자산 (쉼표구분)", "SPY,QQQ").split(",")
DEFENSIVE_C = st.sidebar.text_input("전략C 방어자산 (쉼표구분)", "BIL,IEF").split(",")

# 깔끔한 공백 정리
OFFENSIVE_A = [t.strip().upper() for t in OFFENSIVE_A if t.strip()]
DEFENSIVE_A = [t.strip().upper() for t in DEFENSIVE_A if t.strip()]
OFFENSIVE_B = [t.strip().upper() for t in OFFENSIVE_B if t.strip()]
DEFENSIVE_B = [t.strip().upper() for t in DEFENSIVE_B if t.strip()]
OFFENSIVE_C = [t.strip().upper() for t in OFFENSIVE_C if t.strip()]
DEFENSIVE_C = [t.strip().upper() for t in DEFENSIVE_C if t.strip()]

# 중복 없는 전체 티커 추출
all_tickers = list(set(OFFENSIVE_A + DEFENSIVE_A + OFFENSIVE_B + DEFENSIVE_B + OFFENSIVE_C + DEFENSIVE_C + ["SPY"]))

# -------------------------------------------------------------
# 4. 상단 세그먼트형 메인 탭바 구성 (ETF 랭킹 탭 추가)
# -------------------------------------------------------------
tab_a, tab_b, tab_c, tab_rank = st.tabs(["📈 전략 A", "📉 전략 B", "🛡️ 전략 C", "🏆 ETF 랭킹"])

# 연산용 주가 미리 다운로드 (자산배분 탭 공통)
today = datetime.date.today()
start_date = today - datetime.timedelta(days=550)
hist_prices = get_historical_prices(all_tickers, start_date, today)
spy_divs_hist = get_dividend_history("SPY", start_date, today)

# 백테스트/최근 신호 조회 일자 선정 (최근 3달 말일)
dates_to_check = []
if not hist_prices.empty:
    # 월말 영업일 필터링을 위한 다운샘플링
    monthly_prices = hist_prices.resample('ME').last()
    dates_to_check = monthly_prices.index[-3:].tolist()
    dates_to_check.reverse()  # 최신순 정렬

# --- [공통 화면 그리기 도우미 함수] ---
def render_strategy_view(tab_obj, strategy_letter, off_list, def_list):
    with tab_obj:
        st.markdown(f"### 📊 동적 자산배분 전략 {strategy_letter}")
        
        # 상단 핵심 구성 요약
        st.markdown(f"""
        <div class="info-box">
            <b>전략 구조 안내</b><br/>
            • <b>공격자산:</b> {", ".join(off_list)}<br/>
            • <b>방어자산:</b> {", ".join(def_list)}<br/>
            • 매달 말일 기준으로 가중 모멘텀 스코어를 계산하여 공/방 신호를 도출하고 비중을 결정합니다.
        </div>
        """, unsafe_allow_html=True)
        
        if hist_prices.empty:
            st.warning("데이터가 준비되지 않았습니다.")
            return

        # 최신 월말 신호 및 비중 계산
        for idx, date in enumerate(dates_to_check):
            # 전략별 시그널 역동 연산
            hist_portfolio, sig_a, sig_b, sig_c, dy_c = compute_historical_portfolio_at_month_end(
                hist_prices, spy_divs_hist, date,
                OFFENSIVE_A, DEFENSIVE_A, OFFENSIVE_B, DEFENSIVE_B, OFFENSIVE_C, DEFENSIVE_C
            )
            
            date_str = date.strftime("%Y년 %m월 %d일")
            sig_state = sig_a if strategy_letter == "A" else (sig_b if strategy_letter == "B" else sig_c)
            sig_text = "🟢 공격 (Offensive)" if sig_state else "🛡️ 방어 (Defensive)"
            current_portfolio = hist_portfolio.get(strategy_letter, {})
            
            # 첫 번째(가장 최신)인 경우 헤더를 더 돋보이게 카드형태로 노출
            if idx == 0:
                st.markdown(f"#### 📅 현재 유지 포트폴리오 (최근 {date_str} 마감 기준)")
                st.markdown(f"""
                <div class="premium-card">
                    <p style='margin:0; font-size:14px; color:#64748b; font-weight:600;'>현재 포트폴리오 상태</p>
                    <h3 style='margin:8px 0 16px 0; color:#0f172a;'>{sig_text}</h3>
                    <p style='margin:0; font-size:14px; font-weight:600; color:#1e293b; border-bottom:1px solid #f1f5f9; padding-bottom:8px;'>보유 자산 비중안내</p>
                    <div style='margin-top:10px;'>
                        {"".join([f"<div style='display:flex; justify-content:space-between; margin-bottom:6px; font-size:14px;'><span style='font-weight:bold; color:#0f172a;'>• {tk}</span><span style='color:#475569;'>{val*100:.1f}%</span></div>" for tk, val in current_portfolio.items()])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("#### 📜 과거 월별 신호 히스토리")
            else:
                # 과거 히스토리는 Expander로 처리
                with st.expander(f"📅 {date_str} 마감 기준 포트폴리오"):
                    st.write(f"**진입 신호**: {sig_text}")
                    st.write("**비중 배분:**")
                    for tk, val in current_portfolio.items():
                        st.markdown(f"- **{tk}**: {val*100:.1f}%")

# 각 전략 탭 렌더링
render_strategy_view(tab_a, "A", OFFENSIVE_A, DEFENSIVE_A)
render_strategy_view(tab_b, "B", OFFENSIVE_B, DEFENSIVE_B)
render_strategy_view(tab_c, "C", OFFENSIVE_C, DEFENSIVE_C)


# -------------------------------------------------------------
# 5. 미국 ETF 실시간 랭킹 탭 구현 (새로 추가된 영역)
# -------------------------------------------------------------
with tab_rank:
    st.markdown("### 🏆 미국 주요 ETF 실시간 랭킹")
    
    st.markdown("""
    <div class="info-box">
        <b>모멘텀 스코어 산출 방식</b><br/>
        • 공식: <b>(12 * 1M 수익률) + (4 * 3M 수익률) + (2 * 6M 수익률) + 1Y 수익률</b><br/>
        • 단기 트렌드(1개월)에 더 높은 가중치를 주어 현재 시장을 선도하는 트렌드를 신속하게 감지합니다.
    </div>
    """, unsafe_allow_html=True)
    
    # 랭킹 데이터 로드
    with st.spinner("미국 주요 ETF 데이터를 로드하는 중입니다..."):
        try:
            df_rank = get_etf_rankings()
        except Exception as e:
            st.error("ETF 랭킹 데이터를 수집하는 동안 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
            df_rank = pd.DataFrame()
            
    if not df_rank.empty:
        # 데이터 정렬 및 필터 컨트롤 영역
        c1, c2 = st.columns([1, 1])
        with c1:
            category_filter = st.selectbox("📂 자산군 분류", ["전체", "주식 (Equity)", "채권 (Fixed Income)", "대체자산 (Alternatives)"])
        with c2:
            sort_metric = st.selectbox("📊 정렬 기준", ["모멘텀 스코어", "1개월 (%)", "3개월 (%)", "6개월 (%)", "1년 (%)", "YTD (%)"])
            
        search_query = st.text_input("🔍 티커 혹은 한글명 검색 (예: SPY, 반도체)", "").strip().upper()
        
        # 필터링 적용
        df_filtered = df_rank.copy()
        if category_filter != "전체":
            df_filtered = df_filtered[df_filtered["카테고리"] == category_filter]
            
        if search_query:
            df_filtered = df_filtered[
                df_filtered["티커"].str.contains(search_query) | 
                df_filtered["이름"].str.contains(search_query, case=False)
            ]
            
        # 선택된 기준에 따라 내림차순 정렬
        df_filtered = df_filtered.sort_values(by=sort_metric, ascending=False).reset_index(drop=True)
        
        # 상단 Top 3 하이라이트 노출 (전체 혹은 해당 조건 내 최상위 3개)
        if not df_filtered.empty:
            st.markdown("#### 🔥 현재 트렌드 선도 Top 3 ETF")
            top_cols = st.columns(min(3, len(df_filtered)))
            for i, col in enumerate(top_cols):
                if i < len(df_filtered):
                    row = df_filtered.iloc[i]
                    medals = ["🥇", "🥈", "🥉"]
                    
                    with col:
                        st.markdown(f"""
                        <div class="etf-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span style="font-size:24px;">{medals[i]}</span>
                                <span style="font-size:12px; font-weight:600; padding:2px 8px; background-color:#f1f5f9; border-radius:12px; color:#475569;">
                                    {row['카테고리'].split()[0]}
                                </span>
                            </div>
                            <h4 style="margin:8px 0 4px 0; color:#0f172a;">{row['티커']}</h4>
                            <p style="margin:0; font-size:12px; color:#64748b; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{row['이름']}</p>
                            <hr style="margin:8px 0; border:none; border-top:1px solid #f1f5f9;"/>
                            <div style="display:flex; justify-content:space-between; font-size:13px;">
                                <span style="color:#64748b;">현재가</span>
                                <span style="font-weight:bold; color:#0f172a;">${row['현재가 ($)']}</span>
                            </div>
                            <div style="display:flex; justify-content:space-between; font-size:13px; margin-top:2px;">
                                <span style="color:#64748b;">모멘텀</span>
                                <span style="font-weight:bold; color:#dc2626;">{row['모멘텀 스코어']:.1f}점</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
            st.markdown("---")
            st.markdown("#### 📋 실시간 미국 ETF 랭킹 테이블")
            
            # Interactive Streamlit Dataframe 활용
            st.dataframe(
                df_filtered,
                column_config={
                    "티커": st.column_config.TextColumn("티커", width="small"),
                    "이름": st.column_config.TextColumn("이름(한글명)", width="medium"),
                    "카테고리": st.column_config.TextColumn("구분"),
                    "현재가 ($)": st.column_config.NumberColumn("현재가", format="$%.2f"),
                    "1개월 (%)": st.column_config.NumberColumn("1M", format="%+.2f%%"),
                    "3개월 (%)": st.column_config.NumberColumn("3M", format="%+.2f%%"),
                    "6개월 (%)": st.column_config.NumberColumn("6M", format="%+.2f%%"),
                    "1년 (%)": st.column_config.NumberColumn("1Y", format="%+.2f%%"),
                    "YTD (%)": st.column_config.NumberColumn("YTD", format="%+.2f%%"),
                    "모멘텀 스코어": st.column_config.NumberColumn("모멘텀", format="%.1f")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("검색 조건에 일치하는 ETF가 없습니다.")
            
        # 새로고침 처리
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🔄 실시간 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
    else:
        st.warning("ETF 가격 데이터를 야후 파이낸스로부터 받아오지 못했습니다. 잠시 후 새로고침해 주세요.")

# -------------------------------------------------------------
# 6. 하단 푸터 영역
# -------------------------------------------------------------
st.markdown("<br/><br/>", unsafe_allow_html=True)
st.markdown("""
    <div style='text-align: center; color: #94a3b8; font-size: 11px; padding: 20px 0; border-top: 1px solid #e2e8f0;'>
        © 2026 동적 자산배분 & ETF 랭킹 대시보드 • Data from Yahoo Finance
    </div>
""", unsafe_allow_html=True)
