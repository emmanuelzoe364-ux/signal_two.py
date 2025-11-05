import yfinance as yf
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Crypto Portfolio Signals (Confirmation-Based)", layout="wide")
st.title("📈 BTC & ETH Portfolio Tracker – Confirmation-Based Signals")

# -------------------------------
# User input
# -------------------------------
days = st.slider("Days to track:", min_value=7, max_value=180, value=60)

# -------------------------------
# Fetch historical daily prices
# -------------------------------
tickers = ['BTC-USD', 'ETH-USD']
data = yf.download(tickers, period=f'{days}d', interval='1d')['Close']
data = data.ffill().bfill()

# -------------------------------
# Compute portfolio cumulative returns
# -------------------------------
initial_capital = 1
portfolio = pd.DataFrame({
    '100% BTC': initial_capital * (data['BTC-USD'] / data['BTC-USD'].iloc[0]),
    '100% ETH': initial_capital * (data['ETH-USD'] / data['ETH-USD'].iloc[0]),
    '50% BTC + 50% ETH': initial_capital * (
        0.5 * (data['BTC-USD'] / data['BTC-USD'].iloc[0]) +
        0.5 * (data['ETH-USD'] / data['ETH-USD'].iloc[0])
    )
})

# -------------------------------
# Select portfolio
# -------------------------------
choice = st.selectbox("Select Portfolio:", portfolio.columns)
df = portfolio[[choice]].rename(columns={choice: 'cum'})

# -------------------------------
# Compute EMAs
# -------------------------------
df['EMA_10'] = df['cum'].ewm(span=10, adjust=False).mean()
df['EMA_30'] = df['cum'].ewm(span=30, adjust=False).mean()

# -------------------------------
# Confirmation-based signal logic
# -------------------------------
df['trend_up'] = df['EMA_10'] > df['EMA_30']
df['trend_down'] = df['EMA_10'] < df['EMA_30']

df['cum_above'] = df['cum'] > df['EMA_30']
df['cum_below'] = df['cum'] < df['EMA_30']

# Initialize signal column
df['signal'] = 0

# BUY: after uptrend established, cumulative dips below EMA_30 then crosses back above
df['buy_signal'] = (df['trend_up']) & (df['cum_below'].shift(1)) & (df['cum_above'])
# SELL: after downtrend established, cumulative spikes above EMA_30 then crosses back below
df['sell_signal'] = (df['trend_down']) & (df['cum_above'].shift(1)) & (df['cum_below'])

df.loc[df['buy_signal'], 'signal'] = 1
df.loc[df['sell_signal'], 'signal'] = -1

# Extract signal points
buy_signals = df[df['signal'] == 1]
sell_signals = df[df['signal'] == -1]

# -------------------------------
# Plot everything
# -------------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(x=df.index, y=df['cum'], name='Cumulative', line=dict(color='blue')))
fig.add_trace(go.Scatter(x=df.index, y=df['EMA_10'], name='EMA 10', line=dict(color='orange')))
fig.add_trace(go.Scatter(x=df.index, y=df['EMA_30'], name='EMA 30', line=dict(color='red')))

# Buy/Sell markers
fig.add_trace(go.Scatter(
    x=buy_signals.index, y=buy_signals['cum'],
    mode='markers', marker_symbol='triangle-up', marker_color='green', marker_size=10, name='Buy Signal'
))
fig.add_trace(go.Scatter(
    x=sell_signals.index, y=sell_signals['cum'],
    mode='markers', marker_symbol='triangle-down', marker_color='red', marker_size=10, name='Sell Signal'
))

fig.update_layout(
    title=f"{choice} – Cumulative Return & Confirmation-Based Signals",
    xaxis_title="Date",
    yaxis_title="Cumulative Return",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# -------------------------------
# Summary metrics
# -------------------------------
latest_value = df['cum'].iloc[-1]
last_signal = df['signal'].iloc[-1]
signal_text = "BUY 🟢" if last_signal == 1 else "SELL 🔴" if last_signal == -1 else "NEUTRAL ⚪"

st.markdown("### 📊 Latest Summary")
col1, col2 = st.columns(2)
col1.metric("Latest Portfolio Value", f"{latest_value:.4f}")
col2.metric("Current Signal", signal_text)

# -------------------------------
# Average signal duration tracker
# -------------------------------
df['signal_change'] = df['signal'].diff().fillna(0).ne(0)
signal_durations = df[df['signal_change']].index.to_series().diff().dropna()

if not signal_durations.empty:
    avg_hold = signal_durations.mean()
    st.write(f"⏱️ Average Signal Hold Duration: {avg_hold.days:.1f} days")
else:
    st.write("⏱️ Not enough signals yet to calculate average hold duration.")

st.caption("Signals are generated only after a confirmed realignment between cumulative performance and EMAs — not at the first crossover.")
