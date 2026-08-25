import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(
    page_title="동적 자산배분 전략 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 자산군 정의
OFFENSIVE_A = ['SPY', 'QQQ', 'IWM', 'VGK', 'EWJ', 'EEM', 'VNQ', 'DBC', 'GLD', 'TLT', 'LQD', 'HYG'] # 12개 자산
DEFENSIVE_A = ['SHY', 'IEF', 'TLT', 'LQD', 'BIL']

OFFENSIVE_B = ['SPY', 'QQQ', 'IWM', 'EFA', 'EEM', 'VNQ', 'GLD', 'TLT']
DEFENSIVE_B = ['IEF', 'SHY', 'BIL']

OFFENSIVE_C = ['SPY', 'QQQ', 'IWM', 'EFA', 'EEM', 'TLT']
DEFENSIVE_C = ['BIL', 'IEF']

ALL_TICKERS = list(set(OFFENSIVE_A + DEFENSIVE_A + OFFENSIVE_B + DEFENSIVE_B + OFFENSIVE_C + DEFENSIVE_C + ['SPY', 'BIL', 'IEF', 'TLT']))

def get_sp500_dividend_yield(spy_ticker_obj=None, spy_hist_df=None) -> float:
    """
    SPY의 최근 12개월 배당금을 기반으로 배당수익률(%)을 직접 계산합니다.
    yfinance info의 불안정한 dividendYield 파싱에 의존하지 않고, 배당 히스토리를 최우선 사용합니다.
    """
    try:
        if spy_ticker_obj is None:
            spy_ticker_obj = yf.Ticker("SPY")
            
        # 1. 배당 히스토리 기반 직접 계산 (Primary method)
        divs = spy_ticker_obj.dividends
        if len(divs) > 0:
            one_year_ago = pd.Timestamp.now(tz=divs.index.tz) - pd.Timedelta(days=365)
            recent_divs = divs[divs.index >= one_year_ago]
            sum_divs = recent_divs.sum()
            
            # 현재가 가져오기
            if spy_hist_df is not None and not spy_hist_df.empty:
                current_price = spy_hist_df['Close'].iloc[-1]
            else:
                current_price = spy_ticker_obj.history(period="5d")['Close'].iloc[-1]
                
            if current_price > 0 and sum_divs > 0:
                raw_yield = sum_divs / current_price
                return float(raw_yield * 100) # 퍼센트 단위로 변환 (예: 1.35%)
                
        # 2. 보조 로직 (Fallback: info dictionary 사용 시 포맷 검증)
        info = spy_ticker_obj.info
        yield_val = info.get('dividendYield') or info.get('yield') or info.get('trailingAnnualDividendYield')
        if yield_val is not None:
            # yield_val이 소수점 형태(0.013)로 올 경우와 % 형태(1.3)로 올 경우를 검증
            if yield_val < 0.15: # 소수점 비율 형태인 경우
                return float(yield_val * 100)
            return float(yield_val)
            
    except Exception as e:
        st.warning(f"SPY 배당수익률 계산 중 오류 발생: {e}. 기본값 1.3%를 적용합니다.")
        
    return 1.3 # 계산 실패 시 안전한 기본 추정값

def compute_historical_portfolio_at_month_end(date, prices_df, divs_df, tickers):
    """
    특정 월말 시점에서의 배당수익률 및 공격/방어 신호를 계산합니다.
    [수정사항 반영]:
    1) 배당수익률 계산 시 이중 스케일링 버그 수정 (퍼센트 변환 전 비율 단계에서 < 0.15 체크)
    """
    sub_prices = prices_df.loc[:date]
    if len(sub_prices) < 252:
        # 데이터가 부족할 경우 기본값 반환
        return {}, False, False, False, 1.3

    latest_prices = sub_prices.iloc[-1]
    spy_price = latest_prices.get('SPY', np.nan)
    
    # 최근 1년 배당금 합산
    one_year_ago = date - pd.Timedelta(days=365)
    sub_divs = divs_df.loc[(divs_df.index >= one_year_ago) & (divs_df.index <= date)]
    spy_divs_sum = sub_divs['SPY'].sum() if 'SPY' in sub_divs.columns else 0.0

    # [수정] 이중 스케일링 버그 해결
    # 퍼센트(* 100) 곱하기 이전의 순수 비율 raw_dy 기준으로 조건을 판단합니다.
    if pd.notna(spy_price) and spy_price > 0 and spy_divs_sum > 0:
        raw_dy = spy_divs_sum / spy_price
        dy_val = raw_dy * 100 if raw_dy < 0.15 else raw_dy
    else:
        dy_val = 1.3  # 기본값

    # 신호 판정 예시 (12개월 이동평균 또는 모멘텀 기준)
    spy_ma12 = sub_prices['SPY'].tail(252).mean() if 'SPY' in sub_prices else spy_price
    
    hist_is_attack_a = spy_price > spy_ma12 and dy_val > 1.2
    hist_is_attack_b = spy_price > spy_ma12
    hist_is_attack_c = dy_val > 1.0

    # 포트폴리오 가중치 할당
    selected_tickers = OFFENSIVE_A if hist_is_attack_a else DEFENSIVE_A
    weight = 1.0 / len(selected_tickers)
    hist_portfolio = {t: weight for t in selected_tickers}

    return hist_portfolio, hist_is_attack_a, hist_is_attack_b, hist_is_attack_c, dy_val

@st.cache_data(ttl=3600)
def get_all_financial_data_v2(tickers, period_years=3):
    """
    [수정사항 반영]:
    티커별 순차 호출 대신 yf.download() 배치 호출을 적용하여 수집 속도를 수십 배 향상시켰습니다.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_years * 365 + 30)

    try:
        # yf.download 배치 다운로드 (속도 개선)
        df_all = yf.download(
            tickers=tickers,
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            group_by='ticker',
            auto_adjust=False,
            threads=True
        )

        prices_dict = {}
        divs_dict = {}

        for ticker in tickers:
            if len(tickers) == 1:
                t_df = df_all
            else:
                if ticker in df_all.columns.levels[0]:
                    t_df = df_all[ticker]
                else:
                    continue

            if 'Adj Close' in t_df.columns:
                prices_dict[ticker] = t_df['Adj Close']
            elif 'Close' in t_df.columns:
                prices_dict[ticker] = t_df['Close']

        # 배당 데이터 수집 (배당은 yf.Tickers를 통해 일괄 조회)
        tickers_obj = yf.Tickers(" ".join(tickers))
        for ticker in tickers:
            try:
                div_series = tickers_obj.tickers[ticker].dividends
                if not div_series.empty:
                    # tz_localize 제거하여 DatetimeIndex 통일
                    if div_series.index.tz is not None:
                        div_series.index = div_series.index.tz_localize(None)
                    divs_dict[ticker] = div_series
            except Exception:
                pass

        prices_df = pd.DataFrame(prices_dict).ffill().dropna(how='all')
        divs_df = pd.DataFrame(divs_dict).fillna(0)

        # Index 타임존 통일
        if prices_df.index.tz is not None:
            prices_df.index = prices_df.index.tz_localize(None)

        return prices_df, divs_df

    except Exception as e:
        st.error(f"데이터 다운로드 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=3600)
def get_historical_simulation_data(tickers, years=5):
    """
    시뮬레이션을 위한 시세 및 배당 데이터 배치 로더
    """
    return get_all_financial_data_v2(tickers, period_years=years)

st.title("📊 동적 자산배분 포트폴리오 대시보드")
st.markdown("yfinance 배치 수집 및 안정화된 배당수익률 계산 로직이 적용된 포트폴리오 관리 시스템입니다.")

# Sidebar Controls
st.sidebar.header("⚙️ 설정")
lookback_years = st.sidebar.slider("조회 기간 (년)", min_value=1, max_value=10, value=3)

with st.spinner("금융 데이터를 고속으로 분석 중입니다..."):
    prices_df, divs_df = get_all_financial_data_v2(ALL_TICKERS, period_years=lookback_years)
    spy_obj = yf.Ticker("SPY")
    current_dy = get_sp500_dividend_yield(spy_ticker_obj=spy_obj, spy_hist_df=prices_df[['SPY']] if 'SPY' in prices_df else None)

# Top Metrics Display
col1, col2, col3, col4 = st.columns(4)
col1.metric("SPY 현재가", f"${prices_df['SPY'].iloc[-1]:.2f}" if 'SPY' in prices_df else "N/A")
col2.metric("S&P 500 배당수익률", f"{current_dy:.2f}%")
col3.metric("분석 대상 자산수", f"{len(ALL_TICKERS)}개")
col4.metric("데이터 기준일", prices_df.index[-1].strftime('%Y-%m-%d') if not prices_df.empty else "N/A")

tab1, tab2, tab3 = st.tabs(["전략 A (BAA/동적 자산배분)", "전략 B", "과거 리밸런싱 히스토리"])

with tab1:
    st.header("전략 A (동적 자산배분)")
    
    # [수정사항 반영]: 자산 개수를 하드코딩(13개) 대신 동적(len(OFFENSIVE_A))으로 정확히 안내
    st.info(f"""
    **[전략 설명]**  
    - **공격 국면 (공격 자산 {len(OFFENSIVE_A)}개)**: {', '.join(OFFENSIVE_A)}  
    - **방어 국면 (방어 자산 {len(DEFENSIVE_A)}개)**: {', '.join(DEFENSIVE_A)}  
    - Market Signal(SPY 배당수익률 및 이동평균선)에 따라 국면을 동적으로 전환합니다.
    """)

    # 모멘텀 및 신호 계산
    spy_latest = prices_df['SPY'].iloc[-1]
    spy_ma200 = prices_df['SPY'].tail(200).mean()
    is_attack_a = (spy_latest > spy_ma200) and (current_dy > 1.2)

    st.subheader("현재 전략 A 신호 상태")
    if is_attack_a:
        st.success(f"🔥 **공격 국면 (OFFENSIVE)** - 공격 자산 {len(OFFENSIVE_A)}개에 균등 배분합니다.")
        target_assets = OFFENSIVE_A
    else:
        st.warning(f"🛡️ **방어 국면 (DEFENSIVE)** - 방어 자산 {len(DEFENSIVE_A)}개에 균등 배분합니다.")
        target_assets = DEFENSIVE_A

    weights = {asset: 1.0 / len(target_assets) for asset in target_assets}
    df_weights = pd.DataFrame(list(weights.items()), columns=['티커', '목표 비중 (%)'])
    df_weights['목표 비중 (%)'] = df_weights['목표 비중 (%)'] * 100

    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.dataframe(df_weights.style.format({'목표 비중 (%)': '{:.2f}%'}), use_container_width=True)
    with col_right:
        fig = px.pie(df_weights, values='목표 비중 (%)', names='티커', title="전략 A 포트폴리오 목표 비중")
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("전략 B")
    st.write(f"공격 자산({len(OFFENSIVE_B)}개): {', '.join(OFFENSIVE_B)}")
    st.write(f"방어 자산({len(DEFENSIVE_B)}개): {', '.join(DEFENSIVE_B)}")

with tab3:
    st.header("과거 리밸런싱 히스토리 및 백테스트 시뮬레이션")

    # 월말 날짜 추출
    month_ends = prices_df.resample('ME').last().index

    # 외부 변수 선언 (문자열 형태)
    sig_a = "공격" if is_attack_a else "방어"
    sig_b = "공격" if spy_latest > spy_ma200 else "방어"
    sig_c = "공격" if current_dy > 1.0 else "방어"

    st.caption(f"최근 실시간 판정 상태: 전략A[{sig_a}], 전략B[{sig_b}], 전략C[{sig_c}]")

    history_records = []

    # [수정사항 반영]: 루프 내부에서 변수명 재사용으로 인한 덮어쓰기 방지 (hist_sig_a, hist_is_attack_a 사용)
    for idx, date in enumerate(month_ends):
        hist_portfolio, hist_is_attack_a, hist_is_attack_b, hist_is_attack_c, hist_dy = compute_historical_portfolio_at_month_end(
            date=date,
            prices_df=prices_df,
            divs_df=divs_df,
            tickers=ALL_TICKERS
        )
        
        # 신호 문자열 분리 정의 (외부 scope의 sig_a 변수를 덮어쓰지 않음)
        hist_sig_a_str = "공격" if hist_is_attack_a else "방어"
        hist_sig_b_str = "공격" if hist_is_attack_b else "방어"
        hist_sig_c_str = "공격" if hist_is_attack_c else "방어"

        history_records.append({
            '리밸런싱 일자': date.strftime('%Y-%m-%d'),
            'SPY 배당수익률(%)': round(hist_dy, 2),
            '전략A 국면': hist_sig_a_str,
            '전략B 국면': hist_sig_b_str,
            '전략C 국면': hist_sig_c_str,
            '보유 자산 수': len(hist_portfolio)
        })

    df_history = pd.DataFrame(history_records)
    st.dataframe(df_history, use_container_width=True)

    # 히스토리 시각화
    fig_hist = go.Figure()
    fig_hist.add_trace(go.Scatter(
        x=df_history['리밸런싱 일자'],
        y=df_history['SPY 배당수익률(%)'],
        mode='lines+markers',
        name='SPY 배당수익률 (%)'
    ))
    fig_hist.add_hline(y=1.2, line_dash="dash", line_color="red", annotation_text="전략A 임계치 (1.2%)")
    fig_hist.update_layout(title="월말 기준 SPY 배당수익률 추이", xaxis_title="날짜", yaxis_title="배당수익률 (%)")
    st.plotly_chart(fig_hist, use_container_width=True)
