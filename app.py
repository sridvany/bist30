import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="BIST Gelişmiş Analiz", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; background-color: #ff4b4b; color: white; font-weight: bold; }
    input { text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 BIST Profesyonel Trade & Likidite Terminali")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Parametreler")
    symbol_raw = st.text_input("Sembol", placeholder="Örn: THYAO").strip().upper()
    compare_raw = st.text_input("Korelasyon Sembolü", value="XU100").strip().upper()
    st.divider()
    run_analysis = st.button("ANALİZİ BAŞLAT")

def format_bist(s):
    if not s: return None
    return f"{s}.IS" if not s.endswith(".IS") else s

if run_analysis:
    if not symbol_raw:
        st.warning("⚠️ Lütfen önce bir sembol giriniz.")
    else:
        with st.spinner(f'{symbol_raw} verileri işleniyor...'):
            ticker = format_bist(symbol_raw)
            comp_ticker = format_bist(compare_raw)
            
            df = yf.download(ticker, period="1y", interval="1d")
            df_comp = yf.download(comp_ticker, period="1y", interval="1d")

            if df.empty or len(df) < 5:
                st.error(f"❌ {symbol_raw} verisi bulunamadı.")
            else:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if isinstance(df_comp.columns, pd.MultiIndex): df_comp.columns = df_comp.columns.get_level_values(0)

                # --- HESAPLAMALAR ---
                df['Daily Range'] = (df['High'] - df['Low']).round(2)
                df['Pct_Change'] = df['Close'].pct_change() * 100
                df['Amihud'] = (df['Pct_Change'].abs() / (df['Volume'] / 1000000)).round(4)
                plot_data = df.tail(30) # Grafikler için son 30 gün

                # --- 1. ANA FİYAT GRAFİĞİ VE TABLO ---
                col_left, col_right = st.columns([3, 1])
                with col_left:
                    st.subheader(f"🕯️ {symbol_raw} Fiyat & Hacim Profili")
                    fig_main = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.85, 0.15], horizontal_spacing=0.01)
                    fig_main.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Fiyat"), row=1, col=1)
                    
                    df_vrp = df.tail(30).copy()
                    df_vrp['PriceBin'] = pd.cut(df_vrp['Close'], bins=15)
                    vprofile = df_vrp.groupby('PriceBin', observed=True)['Volume'].sum()
                    fig_main.add_trace(go.Bar(x=vprofile.values, y=[i.mid for i in vprofile.index], orientation='h', marker_color='rgba(255, 75, 75, 0.3)', name="Hacim"), row=1, col=2)
                    fig_main.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark", showlegend=False, xaxis=dict(range=[df.index[-60], df.index[-1]]), dragmode='pan')
                    st.plotly_chart(fig_main, use_container_width=True, config={'scrollZoom': True})

                with col_right:
                    st.subheader("🔗 İlişki Verileri")
                    combined = pd.concat([df['Close'], df_comp['Close']], axis=1).dropna().tail(30)
                    combined.columns = ['Hisse', 'Endeks']
                    if not combined.empty:
                        st.metric(f"Pearson ({symbol_raw})", f"{combined['Hisse'].corr(combined['Endeks']):.2f}")
                        st.write(f"**Ort. Amihud:** {df['Amihud'].tail(30).mean():.4f}")
                        st.write(f"**Ort. Range:** {df['Daily Range'].tail(30).mean():.2f}")

                st.divider()
                st.subheader("📅 Detay Veri Listesi")
                res_df = df.tail(30).copy()
                res_df['Değişim %'] = res_df['Pct_Change'].apply(lambda x: f"🟢 +%{x:.2f}" if x > 0 else f"🔴 -%{abs(x):.2f}" if x < 0 else "⚪ 0.00")
                st.dataframe(res_df[['Open', 'High', 'Low', 'Close', 'Volume', 'Daily Range', 'Amihud', 'Değişim %']].sort_index(ascending=False), use_container_width=True, height=350)

                # --- 3. DUAL AXIS GRAFİKLER (ALT ALTA) ---
                st.divider()
                
                # GRAFİK A: Amihud vs Daily Range
                st.subheader(f"📉 {symbol_raw} Amihud (Sol) vs Daily Range (Sağ)")
                fig_dual_1 = go.Figure()
                fig_dual_1.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Amihud'], name="Amihud", line=dict(color='#00FFCC', width=3), yaxis="y1"))
                fig_dual_1.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Daily Range'], name="Daily Range", line=dict(color='#FFD700', width=3, dash='dot'), yaxis="y2"))
                fig_dual_1.update_layout(template="plotly_dark", height=450, 
                                         yaxis=dict(title=dict(text="Amihud", font=dict(color="#00FFCC")), tickfont=dict(color="#00FFCC")),
                                         yaxis2=dict(title=dict(text="Daily Range", font=dict(color="#FFD700")), tickfont=dict(color="#FFD700"), anchor="x", overlaying="y", side="right"),
                                         hovermode="x unified", dragmode='pan')
                st.plotly_chart(fig_dual_1, use_container_width=True, config={'scrollZoom': True})

                # GRAFİK B: Daily Range vs Close
                st.subheader(f"📈 {symbol_raw} Close (Sol) vs Daily Range (Sağ)")
                fig_dual_2 = go.Figure()
                fig_dual_2.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Close'], name="Close", line=dict(color='#FFFFFF', width=2), yaxis="y1"))
                fig_dual_2.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Daily Range'], name="Daily Range", line=dict(color='#FFD700', width=3), yaxis="y2"))
                fig_dual_2.update_layout(template="plotly_dark", height=450,
                                         yaxis=dict(title=dict(text="Close Fiyat", font=dict(color="#FFFFFF")), tickfont=dict(color="#FFFFFF")),
                                         yaxis2=dict(title=dict(text="Daily Range", font=dict(color="#FFD700")), tickfont=dict(color="#FFD700"), anchor="x", overlaying="y", side="right"),
                                         hovermode="x unified", dragmode='pan')
                st.plotly_chart(fig_dual_2, use_container_width=True, config={'scrollZoom': True})

                # GRAFİK C: Amihud vs Close
                st.subheader(f"🧪 {symbol_raw} Close (Sol) vs Amihud (Sağ)")
                fig_dual_3 = go.Figure()
                fig_dual_3.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Close'], name="Close", line=dict(color='#FFFFFF', width=2), yaxis="y1"))
                fig_dual_3.add_trace(go.Scatter(x=plot_data.index, y=plot_data['Amihud'], name="Amihud", line=dict(color='#00FFCC', width=3), yaxis="y2"))
                fig_dual_3.update_layout(template="plotly_dark", height=450,
                                         yaxis=dict(title=dict(text="Close Fiyat", font=dict(color="#FFFFFF")), tickfont=dict(color="#FFFFFF")),
                                         yaxis2=dict(title=dict(text="Amihud (Likidite)", font=dict(color="#00FFCC")), tickfont=dict(color="#00FFCC"), anchor="x", overlaying="y", side="right"),
                                         hovermode="x unified", dragmode='pan')
                st.plotly_chart(fig_dual_3, use_container_width=True, config={'scrollZoom': True})

else:
    st.info("👈 Analiz için bir sembol girin ve 'ANALİZİ BAŞLAT'a basın.")
