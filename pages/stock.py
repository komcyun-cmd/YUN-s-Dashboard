import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# -----------------------------------------------------------------------------
# 1. Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Quant Scenario Trading System",
    page_icon="📈",
    layout="wide"
)

# Custom CSS for financial dashboard look
st.markdown("""
<style>
    .metric-container {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 10px;
        border-radius: 5px;
    }
    .stAlert {
        background-color: #262730;
        color: #fafafa;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Data Acquisition Engine (Error Handled)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)  # Cache data for 5 minutes
def get_stock_data(ticker):
    """
    Fetches 1 year of OHLCV data with robust error handling.
    """
    try:
        # Download data
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        
        if df.empty:
            return None
            
        # Standardize column names (Handle MultiIndex if necessary)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Calculate Moving Averages
        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        
        # Calculate ATR (14) for Stop Loss
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(14).mean()

        return df
    except Exception as e:
        st.error(f"Error fetching data for {ticker}: {e}")
        return None

# -----------------------------------------------------------------------------
# 3. Price Target Engine (Analysis Logic)
# -----------------------------------------------------------------------------
def calculate_scenarios(df):
    """
    Computes Support, Resistance, Pivots, Demark, Fibonacci, and Wave Targets.
    """
    try:
        if len(df) < 60:
            return None

        last_row = df.iloc[-1]       # Today (Current)
        prev_row = df.iloc[-2]       # Yesterday (Completed)

        # A. Pivot Points (Based on Yesterday)
        P = (prev_row['High'] + prev_row['Low'] + prev_row['Close']) / 3
        R1 = (2 * P) - prev_row['Low']
        S1 = (2 * P) - prev_row['High']
        R2 = P + (prev_row['High'] - prev_row['Low'])
        S2 = P - (prev_row['High'] - prev_row['Low'])

        # B. Demark Analysis
        if prev_row['Close'] < prev_row['Open']:    # Bearish Candle Yesterday
            X = prev_row['High'] + (2 * prev_row['Low']) + prev_row['Close']
        elif prev_row['Close'] > prev_row['Open']:  # Bullish Candle Yesterday
            X = (2 * prev_row['High']) + prev_row['Low'] + prev_row['Close']
        else:                                       # Doji
            X = prev_row['High'] + prev_row['Low'] + (2 * prev_row['Close'])
        
        demark_high = X / 2 - prev_row['Low']
        demark_low = X / 2 - prev_row['High']

        # C. Fibonacci Retracement & Extension (6-month Window)
        lookback = 126 # approx 6 months
        recent_data = df.tail(lookback)
        max_price = recent_data['High'].max()
        min_price = recent_data['Low'].min()
        range_price = max_price - min_price
        
        fib_0382 = max_price - (range_price * 0.382)
        fib_0500 = max_price - (range_price * 0.5)
        fib_0618 = max_price - (range_price * 0.618)
        
        # Extension for Breakout Target
        fib_ext_1618 = max_price + (range_price * 0.618) # 1.618 extension from low

        # D. Ichimoku E-Value (Wave Target)
        # Assuming current trend is Up, Target = Recent Low + (Recent High - Recent Low) * 2 or Breakout logic
        # Implementation: E-Value = High + Height of Wave (Aggressive Target)
        e_value = max_price + range_price

        # E. Stop Loss (ATR Based)
        stop_loss = last_row['Close'] - (2 * last_row['ATR'])

        return {
            "current_price": last_row['Close'],
            "pivot": {"P": P, "R1": R1, "S1": S1, "R2": R2, "S2": S2},
            "demark": {"high": demark_high, "low": demark_low},
            "fib": {"max": max_price, "min": min_price, "0.382": fib_0382, "0.5": fib_0500, "0.618": fib_0618, "ext_1.618": fib_ext_1618},
            "wave": {"e_value": e_value},
            "stop_loss": stop_loss,
            "atr": last_row['ATR']
        }

    except Exception as e:
        st.error(f"Error calculating scenarios: {e}")
        return None

# -----------------------------------------------------------------------------
# 4. Visualization Engine
# -----------------------------------------------------------------------------
def plot_chart(df, ticker, levels):
    """
    Draws Candlestick chart with dynamic Support/Resistance lines.
    """
    fig = go.Figure()

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Price'
    ))

    # Moving Averages
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='orange', width=1), name='MA 20'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='blue', width=1), name='MA 60'))

    # Helper to add horizontal lines
    def add_level(price, color, label, style="dash"):
        fig.add_hline(
            y=price, 
            line_dash=style, 
            line_color=color, 
            annotation_text=f"{label}: {price:.2f}", 
            annotation_position="top right"
        )

    # Add Key Levels
    # 1. Immediate Resistance (Upside)
    add_level(levels['pivot']['R1'], "rgba(0, 255, 0, 0.5)", "Pivot R1")
    add_level(levels['demark']['high'], "rgba(0, 200, 200, 0.5)", "Demark High")
    
    # 2. Breakout Targets (Sky)
    add_level(levels['fib']['ext_1.618'], "green", "Fib Ext 1.618 (Target)")
    add_level(levels['wave']['e_value'], "lime", "Wave E-Value (Max Target)")

    # 3. Support Levels (Downside)
    add_level(levels['pivot']['S1'], "rgba(255, 0, 0, 0.5)", "Pivot S1")
    add_level(levels['fib']['0.618'], "rgba(255, 165, 0, 0.7)", "Fib 0.618 (Golden Pocket)")
    
    # 4. Stop Loss
    add_level(levels['stop_loss'], "red", "ATR Stop Loss", style="solid")

    fig.update_layout(
        title=f"{ticker} Analysis & Scenarios",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=600,
        margin=dict(l=0, r=0, t=50, b=0)
    )

    return fig

# -----------------------------------------------------------------------------
# 5. Main Application Logic
# -----------------------------------------------------------------------------
def main():
    st.title("⚡ Quant Scenario Trading System")
    st.caption("Wall St. Grade Analysis: Pivot, Demark, Fibonacci & Ichimoku Wave")

    # Sidebar
    with st.sidebar:
        st.header("Settings")
        ticker = st.text_input("Ticker Symbol", value="AAPL").upper()
        
        st.info("""
        **Strategy Guide:**
        - **Upside:** 돌파 시 목표가 (E-Value, Fib Ext)
        - **Downside:** 조정 시 매수 타점 (Fib 0.618)
        - **Stop Loss:** 2*ATR 이탈 시 손절
        """)

    if ticker:
        with st.spinner('Analyzing Market Data...'):
            df = get_stock_data(ticker)

        if df is not None:
            # Calculate Levels
            levels = calculate_scenarios(df)
            
            if levels:
                # Top Metrics
                curr_price = levels['current_price']
                prev_close = df.iloc[-2]['Close']
                change = curr_price - prev_close
                pct_change = (change / prev_close) * 100
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Current Price", f"${curr_price:.2f}", f"{pct_change:.2f}%")
                col2.metric("Trend (MA20)", "Bullish" if curr_price > df.iloc[-1]['MA20'] else "Bearish")
                col3.metric("Volatility (ATR)", f"{levels['atr']:.2f}")
                col4.metric("Stop Loss", f"${levels['stop_loss']:.2f}")

                # --- SCENARIO GENERATION (TEXT) ---
                st.subheader("📋 AI Trading Scenarios")
                
                # Logic for scenario text
                trend_status = "상승 추세" if curr_price > df.iloc[-1]['MA60'] else "하락/조정 추세"
                upside_room = ((levels['pivot']['R1'] - curr_price) / curr_price) * 100
                
                c1, c2 = st.columns(2)
                
                with c1:
                    st.success(f"**Scenario 1: Bullish Breakout (상승 시나리오)**")
                    st.markdown(f"""
                    현재 주가는 **{trend_status}**에 위치해 있습니다.
                    - **단기 저항:** Pivot 1차 저항선인 **${levels['pivot']['R1']:.2f}** 돌파 여부가 핵심입니다.
                    - **돌파 목표:** 신고가 영역 진입 시, Fibonacci 확장 레벨인 **${levels['fib']['ext_1.618']:.2f}**와 파동 목표치(E-Value) **${levels['wave']['e_value']:.2f}**까지 상승 여력이 있습니다.
                    """)
                
                with c2:
                    st.warning(f"**Scenario 2: Bearish/Pullback (조정/하락 시나리오)**")
                    st.markdown(f"""
                    하락 시 강력한 매수 대기 구간(Confluence Zone)을 확인하세요.
                    - **1차 방어:** Pivot S1 (**${levels['pivot']['S1']:.2f}**)
                    - **핵심 지지(눌림목):** 최근 상승분의 61.8% 되돌림 지점인 **${levels['fib']['0.618']:.2f}**는 기술적 반등 확률이 매우 높은 구간입니다.
                    - **위험 신호:** **${levels['stop_loss']:.2f}** 이탈 시 추세 훼손으로 간주, 리스크 관리가 필요합니다.
                    """)

                # --- CHART VISUALIZATION ---
                st.subheader("📊 Technical Analysis Chart")
                fig = plot_chart(df, ticker, levels)
                st.plotly_chart(fig, use_container_width=True)

                # --- RAW DATA (Expandable) ---
                with st.expander("Show Raw Data & Calculation Details"):
                    st.write("Recent OHLCV Data:", df.tail())
                    st.write("Calculated Levels:", levels)

            else:
                st.error("데이터가 충분하지 않아 분석할 수 없습니다. (최소 60일 이상의 데이터 필요)")
        else:
            st.warning("유효하지 않은 티커이거나 데이터를 가져올 수 없습니다.")

if __name__ == "__main__":
    main()