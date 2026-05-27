import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 모바일 화면에 최적화된 레이아웃 설정
st.set_page_config(page_title="동적 자산배분 통합 대시보드", layout="centered", initial_sidebar_state="collapsed")

st.title("📈 동적 자산배분 통합 대시보드")
st.caption("야후 파이낸스 실시간 데이터 기반 수시 리밸런싱 가이드 (2026년 전략 포함)")

# --- 1. 자산군 정의 ---
# 전략A 자산군 (최신 리스트)
OFFENSIVE_A = ["QQQ", "SPY", "IYM", "IBB", "SMH", "EEM", "XLK", "LIT", "XLE", "FEZ", "XLV", "XLU", "QTUM"]
DEFENSIVE_A = ["GLD", "TLT", "XLV", "UBT"]

# 전략B 자산군 (레버리지/인버스)
OFFENSIVE_B = ["TYD", "UPRO", "VNQ"]
DEFENSIVE_B = ["DOG", "RWM", "TBF"]

# 전략C (섹터로테이션) 자산군
OFFENSIVE_C = ["FDN", "LIT", "SMH", "XLE"]  # 4대 주도 섹터
DEFENSIVE_C = ["GLD", "PDBC", "OILK"]       # 3대 원자재 방어자산

# 중복 없는 전체 티커 추출
ALL_TICKERS = list(set(["TIP", "SPY"] + OFFENSIVE_A + DEFENSIVE_A + OFFENSIVE_B + DEFENSIVE_B + OFFENSIVE_C + DEFENSIVE_C))

# S&P 500 배당수익률 구하는 헬퍼 함수
def get_sp500_dividend_yield():
    try:
        spy = yf.Ticker("SPY")
        # 1. info API에서 직접 배당수익률 획득 시도 (있을 경우 소수점 형태로 반환됨, 예: 0.0132)
        dy = spy.info.get('dividendYield')
        if dy is not None:
            return float(dy) * 100
        
        # 2. 실패 시 실시간 분배금 기록 기반 직접 역산 연산 (최근 1개년 배당금 합산 / 현재가)
        divs = spy.dividends
        if not divs.empty:
            utc_tz = divs.index.tz
            end_dt = pd.Timestamp.now(tz=utc_tz)
            start_dt = end_dt - pd.Timedelta(days=365)
            last_year_divs = divs.loc[start_dt:end_dt]
            sum_divs = last_year_divs.sum()
            
            hist = spy.history(period="1mo")
            if not hist.empty:
                curr_price = hist['Close'].iloc[-1]
                return (sum_divs / curr_price) * 100
    except Exception as e:
        pass
    return 1.32  # 외부 차단 등 최악의 API 상황을 대비한 합리적인 기본값 백업

# 캐시 꼬임 방지를 위해 함수명을 get_all_financial_data_v2로 변경하여 과거 캐시 강제 무효화
@st.cache_data(ttl=3600)  
def get_all_financial_data_v2(tickers):
    data_list = []
    now = datetime.datetime.now()
    # 13개월 이상의 안정적인 데이터 확보를 위해 450일 전부터 가져옴
    start_date = (now - datetime.timedelta(days=450)).strftime('%Y-%m-%d')
    
    for ticker in tickers:
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(start=start_date, interval="1mo")
            if len(hist) < 12:
                continue
            
            # 가장 최근 종가 및 과거 종가 추출
            current_price = hist['Close'].iloc[-1]
            p1 = hist['Close'].iloc[-2] if len(hist) >= 2 else current_price
            p3 = hist['Close'].iloc[-4] if len(hist) >= 4 else current_price
            p5 = hist['Close'].iloc[-6] if len(hist) >= 6 else current_price # 전략B/C 방어용 5개월 가격
            p6 = hist['Close'].iloc[-7] if len(hist) >= 7 else current_price
            p9 = hist['Close'].iloc[-10] if len(hist) >= 10 else current_price
            p12 = hist['Close'].iloc[-13] if len(hist) >= 13 else hist['Close'].iloc[0]
            
            # 수익률 계산 (%)
            r1 = ((current_price - p1) / p1) * 100
            r3 = ((current_price - p3) / p3) * 100
            r5 = ((current_price - p5) / p5) * 100
            r6 = ((current_price - p6) / p6) * 100
            r9 = ((current_price - p9) / p9) * 100
            r12 = ((current_price - p12) / p12) * 100
            
            # 전략 A / C 공격용 스코어 계산 (1, 3, 6, 12 단순평균)
            score_a_off = (r1 + r3 + r6 + r12) / 4
            
            # 전략 A / C 방어용 스코어 계산 (1, 3, 6, 9, 12 단순평균)
            score_a_def = (r1 + r3 + r6 + r9 + r12) / 5
            
            # 전략 B용 스코어 계산 (가중평균 및 단순평균)
            score_b_off = (r1 * 12 + r3 * 4 + r6 * 2 + r12 * 1) / 19
            score_b_def_simple = (r1 + r3 + r6 + r9 + r12) / 5  # 전략B 방어자산 마이너스 필터링용 단순 모멘텀
            
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
                "raw_closes": hist['Close'].tolist()
            })
        except Exception as e:
            st.error(f"{ticker} 데이터를 가져오는 중 오류 발생: {e}")
            
    return pd.DataFrame(data_list)

# 데이터 한 번에 가져오기 (새로운 함수명 호출)
with st.spinner("야후 파이낸스 실시간 데이터를 통합 집계 중..."):
    df_all = get_all_financial_data_v2(ALL_TICKERS)

if df_all.empty or "TIP" not in df_all["Ticker"].values:
    st.error("핵심 데이터 로딩에 실패했습니다. 페이지를 새로고침해 주세요.")
else:
    # ------------------ 데이터 안전 조회를 위한 사전 래핑 (IndexError 완벽 방지) ------------------
    data_dict = df_all.set_index("Ticker").to_dict(orient="index")
    
    # TIP 데이터 추출 (.get을 사용하여 구조가 누락되었더라도 에러 방지)
    tip_data = data_dict.get("TIP", {})
    tip_closes = tip_data.get("raw_closes", [])
    tip_current = tip_data.get("현재가", 0.0)
    
    # 최근 11개 월간 종가 평균 계산
    tip_last11 = tip_closes[-11:] if len(tip_closes) >= 11 else tip_closes
    tip_ma11 = sum(tip_last11) / len(tip_last11) if tip_last11 else 1.0
    tip_ratio = tip_current / tip_ma11 if tip_ma11 > 0 else 1.0
    is_attack_a = tip_ratio > 1.0

    # 전략 B 카나리아 신호 계산
    tip_score_b = (tip_data.get("1M", 0.0) + tip_data.get("3M", 0.0) + tip_data.get("6M", 0.0) + tip_data.get("9M", 0.0) + tip_data.get("12M", 0.0)) / 5
    is_attack_b = tip_score_b > 0

    # S&P 500 실시간 배당수익률 산출
    realtime_dy = get_sp500_dividend_yield()
    
    # 사이드바를 통한 배당률 시뮬레이션 지원
    st.sidebar.header("⚙️ 실시간 시뮬레이터 옵션")
    dy_input = st.sidebar.number_input(
        "S&P 500 배당수익률 (%) 수동 조절",
        min_value=0.0,
        max_value=10.0,
        value=realtime_dy,
        step=0.01,
        help="S&P 500의 배당수익률을 임의로 변경하여 모의 시뮬레이션을 해볼 수 있습니다."
    )
    is_attack_c = dy_input > 1.33

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

    # ==================== 2026년 전략 (동일비중 혼합) 통합 연산 ====================
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

    # ------------------ 탭 구성 (2026년 전략을 첫 번째로 배치) ------------------
    tab_2026, tab_a, tab_b, tab_c = st.tabs([
        "🏆 2026년 통합 혼합 전략", 
        "🛡️ 전략 A (안정형)", 
        "⚡ 전략 B (공격형)", 
        "🔄 전략 C (섹터로테이션)"
    ])

    # ==================== TAB 1: 2026년 통합 혼합 전략 ====================
    with tab_2026:
        st.header("🏆 2026년 통합 혼합 전략")
        st.markdown(
            "안정 지향의 **전략 A**, 고수익 레버리지의 **전략 B**, 시황 로테이션인 **전략 C**를 "
            "각각 **$33.33\%$씩 동일 비중**으로 혼합하여 시장 전반의 변동성을 완벽하게 제어하는 2026년 추천 전략 모델입니다."
        )

        # 3대 전략 카나리아 시그널 요약
        st.markdown("### 🚦 실시간 카나리아 신호 요약")
        c_sig1, c_sig2, c_sig3 = st.columns(3)
        c_sig1.metric("전략A (TIP 비율)", f"{tip_ratio:.3f}", "공격" if is_attack_a else "방어", delta_color="inverse" if not is_attack_a else "normal")
        c_sig2.metric("전략B (TIP 모멘텀)", f"{tip_score_b:.2f}%", "공격" if is_attack_b else "방어", delta_color="inverse" if not is_attack_b else "normal")
        c_sig3.metric("전략C (배당수익률)", f"{dy_input:.2f}%", "공격" if is_attack_c else "방어", delta_color="inverse" if not is_attack_c else "normal")

        # 추천 포트폴리오 자산 리스트
        st.markdown("### 📝 2026년 통합 최종 자산 배분 비중")
        st.dataframe(df_mix, use_container_width=True, hide_index=True)

    # ==================== TAB 2: 전략 A ====================
    with tab_a:
        st.header("🛡️ 전략 A (안정형)")
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
    with tab_b:
        st.header("⚡ 전략 B (공격형)")
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
    with tab_c:
        st.header("🔄 전략 C (섹터로테이션)")
        st.markdown(
            "**1단계: 카나리아 신호 판단 (S&P 500 배당수익률)** \n"
            "배당수익률이 **1.33%** 초과 시 주식 저평가로 판단하여 공격 모드, 이하일 경우 시장 과열로 판단하여 방어 모드로 진입합니다."
        )
        
        col_c1, col_c2 = st.columns(2)
        col_c1.metric("S&P 500 배당수익률", f"{dy_input:.2f}%")
        col_c2.metric("기준 배당수익률", "1.33%")
        
        if is_attack_c:
            st.success(f"🔥 **현재 모드: 공격 자산 모드** (배당수익률 {dy_input:.2f}% > 1.33%) - 시장 저평가 국면으로 주식을 매수합니다.")
            
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
            st.warning(f"🛡️ **현재 모드: 방어 자산 모드** (배당수익률 {dy_input:.2f}% <= 1.33%) - 시장 과열 국면으로 원자재 자산으로 대피합니다.")
            
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
