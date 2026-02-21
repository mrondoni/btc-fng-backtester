import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from data_loader import get_merged_data
from backtester import run_backtest, calculate_yearly_metrics, run_multi_start_analysis, optimize_thresholds
import datetime

# Page config
st.set_page_config(
    page_title="BTC Fear & Greed Backtester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium Styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    /* Metric Card Styling */
    [data-testid="stMetricValue"] {
        color: #f0f2f6 !important;
        font-weight: 700;
        font-size: 1.5rem !important; /* Smaller font to fit on iPad */
    }
    [data-testid="stMetricLabel"] {
        color: #9ca3af !important;
        font-size: 0.8rem;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 10px 15px; /* More compact padding */
        border-radius: 12px;
        border: 1px solid #3e4251;
    }
    h1, h2, h3 {
        color: #f0f2f6;
        font-family: 'Inter', sans-serif;
    }
    h1 {
        text-align: center;
        padding-bottom: 20px;
    }
    /* Table Styling - Remove background fill */
    .stTable, .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("🚀 Bitcoin Fear & Greed Strategy Dashboard")
    st.markdown("---")

    # Sidebar
    st.sidebar.header("⚙️ Configuración")
    initial_capital = st.sidebar.number_input("Capital Inicial (USD)", value=10000, step=1000)
    buy_threshold = st.sidebar.slider("Umbral de Compra (FNG Indice <= X)", 0, 100, 50)
    sell_threshold = st.sidebar.slider("Umbral de Venta (FNG Indice >= X)", 0, 100, 90)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔍 Optimizar Parámetros"):
        st.session_state.optimize = True
    else:
        if 'optimize' not in st.session_state:
            st.session_state.optimize = False

    st.sidebar.info("""
    **Estrategia:**
    - Compra BTC con el 100% del USD cuando Indice ≤ Umbral de Compra.
    - Vende el 100% del BTC por USD cuando Indice ≥ Umbral de Venta.
    """)

    # Data Fetching
    with st.spinner("Descargando datos actualizados de APIs..."):
        df = get_merged_data()

    if df is not None:
        # Run Backtests
        stats_df, trades_df = run_backtest(df, initial_capital, buy_threshold, sell_threshold)
        yearly_df = calculate_yearly_metrics(stats_df)
        multi_start_df = run_multi_start_analysis(df, initial_capital, buy_threshold, sell_threshold)

        # Top Metrics
        total_profit = stats_df.iloc[-1]['equity'] - initial_capital
        total_roi = (total_profit / initial_capital) * 100
        current_equity = stats_df.iloc[-1]['equity']

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Equity Final", f"{int(current_equity):,}", f"{total_roi:.0f}%")
        col2.metric("Beneficio Total", f"{int(total_profit):,}")
        col3.metric("Operaciones", f"{len(trades_df)}")
        col4.metric("Días Analizados", f"{len(stats_df)}")

        # Main Charts
        st.markdown("### 📊 Evolución del Mercado e Índice")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=stats_df['date'], y=stats_df['price'], name="Precio BTC", line=dict(color="#FF9900", width=2)), secondary_y=False)
        fig.add_trace(go.Scatter(x=stats_df['date'], y=stats_df['fng_value'], name="Fear & Greed Index", line=dict(color="rgba(100, 149, 237, 0.4)", width=1), fill='tozeroy'), secondary_y=True)
        
        if not trades_df.empty:
            buys = trades_df[trades_df['action'] == 'BUY']
            sells = trades_df[trades_df['action'] == 'SELL']
            fig.add_trace(go.Scatter(x=buys['date'], y=buys['price'], mode='markers', name='Compra', marker=dict(symbol='triangle-up', size=12, color='#00FF00')), secondary_y=False)
            fig.add_trace(go.Scatter(x=sells['date'], y=sells['price'], mode='markers', name='Venta', marker=dict(symbol='triangle-down', size=12, color='#FF0000')), secondary_y=False)

        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📈 Crecimiento del Capital")
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(x=stats_df['date'], y=stats_df['equity'], name="Equity", line=dict(color="#00D4FF", width=3), fill='tozeroy'))
        fig_equity.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_equity, use_container_width=True)

        # Multi-Start Analysis Table (AS PER IMAGE)
        st.markdown("### 📅 Análisis de Rendimiento (Inversion Independiente)")
        st.markdown("> Cada columna representa una inversión de $10,000 iniciando el 1 de Enero de ese año.")
        
        # Formatting the multi-start table to look like the image
        def format_dynamic(val):
            if isinstance(val, (int, float)):
                return f"{int(val):,}" if abs(val) > 10 else f"{val:,.1f}"
            return val

        st.table(multi_start_df.style.format(format_dynamic))
        
        # Also clean up the dataframe display below it - Removed highlight
        st.dataframe(multi_start_df.T.style.format("{:,.0f}"), use_container_width=True)

        # Yearly Breakdown
        st.markdown("### 🗓️ Resumen Anual (Estrategia Continua)")
        st.dataframe(yearly_df.style.format({
            "Starting Equity": "{:,.0f}",
            "Ending Equity": "{:,.0f}",
            "Profit/Loss": "{:,.0f}",
            "ROI (%)": "{:,.1f}%"
        }), use_container_width=True)

        # Optimization Section
        if st.session_state.optimize:
            st.markdown("### 🎯 Optimización de Umbrales por Año")
            with st.spinner("Calculando mejores parámetros..."):
                opt_df = optimize_thresholds(df, initial_capital)
                st.table(opt_df.style.format({
                    "Best Buy Threshold": "{:.0f}",
                    "Best Sell Threshold": "{:.0f}",
                    "Max ROI (%)": "{:,.1f}%"
                }))
                st.info("💡 Consejo: Los umbrales que maximizan el ROI cambian según la volatilidad de cada año.")

        # Trade History
        st.markdown("### 📝 Historial de Operaciones")
        if not trades_df.empty:
            st.dataframe(trades_df.style.format({
                "price": "{:,.0f}",
                "amount_usd": "{:,.0f}",
                "amount_btc": "{:,.3f}", 
                "fng": "{:.0f}"
            }), use_container_width=True)
        else:
            st.write("No se ejecutaron operaciones con los parámetros actuales.")

    else:
        st.error("No se pudieron obtener o fusionar los datos.")
        st.info("Esto puede deberse a que una de las APIs (Binance o Fear & Greed) está bloqueada en tu región o tiene problemas de conexión.")
        st.markdown("---")
        st.subheader("Depuración de Datos")
        
        # Testing individual components
        from data_loader import get_fng_data, get_btc_data_from_binance
        
        fng_test = get_fng_data()
        btc_test = get_btc_data_from_binance()
        
        if fng_test is not None:
            st.success("✅ Fear & Greed Index: OK")
        else:
            st.error("❌ Fear & Greed Index: Falló")
            
        if btc_test is not None:
            st.success("✅ Precio Bitcoin (Binance): OK")
        else:
            st.error("❌ Precio Bitcoin (Binance): Falló")
            st.info("Si Binance está fallando, intenta usar una VPN o revisa si Streamlit Cloud tiene acceso a api.binance.com.")

if __name__ == "__main__":
    main()
