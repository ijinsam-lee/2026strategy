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
        color: #475569 !important; /* 슬레이트 그레이 폰트 */
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    /* 마우스 호버 시 자연스러운 그레이톤 변화 */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f1f5f9 !important;
        color: #1e293b !important;
    }
    
    /* 선택된 활성 탭은 선명한 화이트 카드로 도출 */
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f172a !important; /* 딥 차콜 */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
    }
    
    /* 불필요한 기본 하단 언더라인 제거 */
    .stTabs [data-baseweb="tab-highlight-id"] {
        display: none !important;
    }
    
    /* 시황판 및 메인 정보 카드 디자인 */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        margin-bottom: 12px;
    }
    
    /* 정보 팁 카드 및 하단 요약 */
    .summary-card {
        background-color: #f1f5f9;
        border-left: 4px solid #475569;
        padding: 16px;
        border-radius: 0 12px 12px 0;
        margin-top: 15px;
        font-size: 13.5px;
        color: #334155;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. 데이터 가져오기 (시황판용)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=1800)  # 30분 캐싱
def get_market_data():
    tickers = {
        "S&P 500 (SPY)": "SPY",
        "나스닥 100 (QQQ)": "QQQ",
        "다우 존스 (DIA)": "DIA",
        "러셀 2000 (IWM)": "IWM",
        "미 장기채 (TLT)": "TLT",
        "금 (GLD)": "GLD",
        "원유 (USO)": "USO",
        "비트코인 (BTC-USD)": "BTC-USD"
    }
    
    data = {}
    for name, ticker in tickers.items():
        try:
            t = yf.Ticker(ticker)
            # 최근 5일 데이터 가져오기
            hist = t.history(period="5d")
            if len(hist) >= 2:
                # 마지막 거래일과 그 전 거래일 종가
                close_today = hist['Close'].iloc[-1]
                close_prev = hist['Close'].iloc[-2]
                pct_change = ((close_today - close_prev) / close_prev) * 100
                data[name] = {
                    "price": close_today,
                    "change": pct_change,
                    "ticker": ticker
                }
            else:
                data[name] = None
        except Exception as e:
            data[name] = None
    return data

# -----------------------------------------------------------------------------
# 2. 동적 자산배분 엔진 및 백테스트 관련 함수들
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # 자산배분용 데이터는 1시간 캐시
def fetch_historical_prices(tickers, start_date, end_date):
    """지정한 여러 티커들의 일별 수정종가(Adj Close)를 다운로드하여 하나의 DataFrame으로 결합합니다."""
    df = yf.download(tickers, start=start_date, end=end_date)
    if 'Adj Close' in df.columns:
        return df['Adj Close']
    elif 'Close' in df.columns:
        return df['Close']
    return df

@st.cache_data(ttl=3600)
def fetch_spy_dividends(start_date, end_date):
    """SPY 배당 데이터를 가져옵니다 (전략C에서 연배당수익률 계산용)"""
    try:
        spy = yf.Ticker("SPY")
        divs = spy.dividends
        if divs is None or divs.empty:
            return pd.Series(dtype=float)
            
        # index 및 시간대(tz) 검증 방어 로직 강화
        if hasattr(divs, 'index') and hasattr(divs.index, 'tz') and divs.index.tz is not None:
            divs.index = divs.index.tz_localize(None)
            
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        divs_filtered = divs[(divs.index >= start_dt) & (divs.index <= end_dt)]
        return divs_filtered
    except Exception as e:
        return pd.Series(dtype=float)

def compute_historical_portfolio_at_month_end(df_prices, spy_divs_hist, target_date, 
                                              off_a, def_a, off_b, def_b, off_c, def_c):
    """
    특정 target_date(대개 월말 기준)에서의 자산별 모멘텀 신호 및 포트폴리오 비중을 계산합니다.
    """
    if isinstance(target_date, datetime.date) and not isinstance(target_date, datetime.datetime):
        target_date = datetime.datetime.combine(target_date, datetime.time.min)
        
    df_filtered = df_prices[df_prices.index <= target_date]
    if df_filtered.empty:
        return {}, False, False, False, 0.0
        
    last_date = df_filtered.index[-1]
    
    # ---------------------------------------------------------
    # 전략 A (듀얼 모멘텀 전략 예시 - SPY vs BIL 모멘텀)
    # ---------------------------------------------------------
    sig_a = False
    date_12m_ago = last_date - datetime.timedelta(days=365)
    df_12m = df_filtered[df_filtered.index >= date_12m_ago]
    if len(df_12m) >= 20 and "SPY" in df_filtered.columns and "BIL" in df_filtered.columns:
        spy_ret_12m = (df_filtered["SPY"].iloc[-1] / df_filtered["SPY"].asof(date_12m_ago)) - 1
        bil_ret_12m = (df_filtered["BIL"].iloc[-1] / df_filtered["BIL"].asof(date_12m_ago)) - 1
        if spy_ret_12m > bil_ret_12m and spy_ret_12m > 0:
            sig_a = True
            
    # ---------------------------------------------------------
    # 전략 B (VAA 전략 간소화 예시 - SPY, EFA, EEM, AGG 가중 모멘텀)
    # ---------------------------------------------------------
    sig_b = False
    vaa_tickers = ["SPY", "EFA", "EEM", "AGG"]
    if all(t in df_filtered.columns for t in vaa_tickers):
        def get_weighted_momentum(ticker, ref_date):
            p_now = df_filtered[ticker].iloc[-1]
            p_1m = df_filtered[ticker].asof(ref_date - datetime.timedelta(days=30))
            p_3m = df_filtered[ticker].asof(ref_date - datetime.timedelta(days=90))
            p_6m = df_filtered[ticker].asof(ref_date - datetime.timedelta(days=180))
            p_12m = df_filtered[ticker].asof(ref_date - datetime.timedelta(days=365))
            
            r1 = (p_now / p_1m - 1) if pd.notna(p_1m) else 0
            r3 = (p_now / p_3m - 1) if pd.notna(p_3m) else 0
            r6 = (p_now / p_6m - 1) if pd.notna(p_6m) else 0
            r12 = (p_now / p_12m - 1) if pd.notna(p_12m) else 0
            return 12*r1 + 4*r3 + 2*r6 + 1*r12
            
        scores = {t: get_weighted_momentum(t, last_date) for t in vaa_tickers}
        if scores["SPY"] > 0 and scores["EFA"] > 0 and scores["EEM"] > 0:
            sig_b = True
            
    # ---------------------------------------------------------
    # 전략 C (LAA 전략 예시)
    # ---------------------------------------------------------
    sig_c = False
    dy_c = 0.0
    if "SPY" in df_filtered.columns:
        spy_p = df_filtered["SPY"].iloc[-1]
        divs_1y = spy_divs_hist[(spy_divs_hist.index <= last_date) & (spy_divs_hist.index >= last_date - datetime.timedelta(days=365))]
        total_div_1y = divs_1y.sum()
        dy_c = (total_div_1y / spy_p) * 100 if spy_p > 0 else 0.0
        
        p_200 = df_filtered["SPY"].rolling(200).mean().iloc[-1] if len(df_filtered) >= 200 else df_filtered["SPY"].iloc[0]
        if spy_p > p_200:
            sig_c = True

    p_a = off_a if sig_a else def_a
    p_b = off_b if sig_b else def_b
    p_c = off_c if sig_c else def_c
    
    combined = {}
    for asset, wt in p_a.items():
        combined[asset] = combined.get(asset, 0.0) + wt * (1/3)
    for asset, wt in p_b.items():
        combined[asset] = combined.get(asset, 0.0) + wt * (1/3)
    for asset, wt in p_c.items():
        combined[asset] = combined.get(asset, 0.0) + wt * (1/3)
        
    combined = {k: round(v, 4) for k, v in combined.items() if round(v, 4) > 0}
    return combined, sig_a, sig_b, sig_c, dy_c


# -----------------------------------------------------------------------------
# 3. 레이아웃 및 뷰포트 구성
# -----------------------------------------------------------------------------

st.title("🛡️ 동적 자산배분 및 실시간 시황 대시보드")
st.caption("실시간 금융 데이터 기반 동적 자산배분 (Powered by yfinance)")

# -----------------------------------------------------------------------------
# 3.1. 실시간 시황판 출력 (기존 정통 글로벌 시황 레이아웃 완벽 유지)
# -----------------------------------------------------------------------------
st.subheader("📊 실시간 주요 지수 시황")
market_data = get_market_data()

cols = st.columns(4)
col_idx = 0

if market_data:
    for name, item in market_data.items():
        if item is not None:
            with cols[col_idx % 4]:
                color = "#ef4444" if item["change"] >= 0 else "#3b82f6"
                sign = "+" if item["change"] >= 0 else ""
                
                st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size: 11px; color: #64748b; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{name}</div>
                        <div style="font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 4px;">${item["price"]:.2f}</div>
                        <div style="font-size: 12px; font-weight: 600; color: {color}; margin-top: 2px;">
                            {sign}{item["change"]:.2f}%
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            col_idx += 1
else:
    st.info("실시간 시황 데이터를 불러오는 중이거나 장외 시간입니다.")

# -----------------------------------------------------------------------------
# 4. 전략 세부 설정 (사이드바)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 전략 자산배분 매개변수")
    
    st.subheader("전략 A (듀얼 모멘텀)")
    st.write("공격: SPY (S&P500)")
    st.write("방어: BIL (초단기 국채)")
    
    st.subheader("전략 B (VAA)")
    st.write("공격: SPY, EFA, EEM")
    st.write("방어: AGG (종합 채권)")
    
    st.subheader("전략 C (LAA)")
    st.write("공격: SPY, GLD, IEF, IWM")
    st.write("방어: SHY (단기 국채)")

# 각 전략별 포트폴리오 비중 정의
OFFENSIVE_A = {"SPY": 1.0}
DEFENSIVE_A = {"BIL": 1.0}

OFFENSIVE_B = {"SPY": 0.4, "EFA": 0.3, "EEM": 0.3}
DEFENSIVE_B = {"AGG": 1.0}

OFFENSIVE_C = {"SPY": 0.25, "GLD": 0.25, "IEF": 0.25, "IWM": 0.25}
DEFENSIVE_C = {"SHY": 0.25, "GLD": 0.25, "IEF": 0.25, "IWM": 0.25}


# -----------------------------------------------------------------------------
# 5. 백테스트 및 시그널 계산 메인 탭 구성
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs(["🎯 현재 포트폴리오 신호", "📈 전략 백테스트 히스토리"])

# 백테스트에 필요한 전체 자산 목록 다운로드
all_required_tickers = ["SPY", "BIL", "EFA", "EEM", "AGG", "GLD", "IEF", "IWM", "SHY"]

# 오늘 기준 데이터 다운로드 범위 설정 (안정적으로 2년치 가격 정보 로드)
end_dt = datetime.datetime.now()
start_dt = end_dt - datetime.timedelta(days=730)

with st.spinner("백테스트 데이터를 다운로드하는 중..."):
    hist_prices = fetch_historical_prices(all_required_tickers, start_dt, end_dt)
    spy_divs_hist = fetch_spy_dividends(start_dt, end_dt)

# 안전하게 시간대(Timezone) 정보 제거 및 인덱스 정밀 검증
if not hist_prices.empty and hasattr(hist_prices, 'index') and isinstance(hist_prices.index, pd.DatetimeIndex):
    try:
        if hist_prices.index.tz is not None:
            hist_prices.index = hist_prices.index.tz_localize(None)
    except Exception:
        pass

with tab1:
    st.subheader("📌 오늘 자 기준 병합 포트폴리오 신호")
    
    if not hist_prices.empty:
        latest_date = hist_prices.index[-1]
        st.info(f"마지막 데이터 수집 시각: **{latest_date.strftime('%Y년 %m월 %d일')}**")
        
        # 최신 상태 포트폴리오 연산
        combined_portfolio, sig_a, sig_b, sig_c, dy_c = compute_historical_portfolio_at_month_end(
            hist_prices, spy_divs_hist, latest_date,
            OFFENSIVE_A, DEFENSIVE_A, OFFENSIVE_B, DEFENSIVE_B, OFFENSIVE_C, DEFENSIVE_C
        )
        
        # 개별 전략 신호 출력
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("전략A (듀얼 모멘텀)", "공격형 (SPY 100%)" if sig_a else "방어형 (BIL 100%)")
        with col2:
            st.metric("전략B (VAA)", "공격형" if sig_b else "방어형 (AGG 100%)")
        with col3:
            st.metric("전략C (LAA)", "공격형 (IWM 포함)" if sig_c else "방어형 (SHY 포함)", f"SPY 배당률: {dy_c:.2f}%")
            
        st.markdown("---")
        st.subheader("💼 최종 병합 추천 포트폴리오 비중")
        st.write("각 전략의 추천 비중을 1/3씩 균등 결합한 자산배분 가이드라인입니다.")
        
        # 포트폴리오 비중 시각화 테이블 및 차트
        if combined_portfolio:
            pf_df = pd.DataFrame(list(combined_portfolio.items()), columns=["자산군(티커)", "추천 비중"])
            pf_df["추천 비중"] = pf_df["추천 비중"] * 100
            pf_df = pf_df.sort_values(by="추천 비중", ascending=False).reset_index(drop=True)
            
            sc1, sc2 = st.columns([1, 1])
            with sc1:
                st.dataframe(pf_df.style.format({"추천 비중": "{:.1f}%"}))
            with sc2:
                st.bar_chart(data=pf_df.set_index("자산군(티커)")["추천 비중"])
        else:
            st.warning("포트폴리오 비중 연산에 실패했습니다.")
    else:
        st.error("데이터를 불러오지 못했습니다. 네트워크 상황을 확인해 주세요.")

with tab2:
    st.subheader("⏳ 지난 6개월간의 월말 신호 및 비중 히스토리")
    st.write("최근 6개월간 각 월말 영업일 기준 신호 현황과 포트폴리오 변화 이력을 확인합니다.")
    
    if not hist_prices.empty:
        # 월말 날짜 추출 (Pandas 구버전 및 신버전 호환용 예외 처리)
        try:
            df_month_ends = hist_prices.resample('ME').last()
        except ValueError:
            try:
                df_month_ends = hist_prices.resample('M').last()
            except Exception:
                df_month_ends = hist_prices
            
        last_6_months = df_month_ends.index[-6:].tolist() if len(df_month_ends) >= 6 else df_month_ends.index.tolist()
        if hist_prices.index[-1] not in last_6_months:
            if (hist_prices.index[-1] - last_6_months[-1]).days > 3:
                last_6_months.append(hist_prices.index[-1])
                
        last_6_months.reverse() # 최신순으로 정렬
        
        for idx, date in enumerate(last_6_months):
            target_col = st.container()
            
            # 히스토리 시그널 역동 연산
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
                    hist_pf_df = pd.DataFrame(list(hist_portfolio.items()), columns=["자산", "비중"])
                    hist_pf_df["비중"] = hist_pf_df["비중"].map(lambda x: f"{x*100:.1f}%")
                    st.dataframe(hist_pf_df.T, hide_index=True)
    else:
        st.error("백테스트 데이터를 가져오지 못했습니다.")
