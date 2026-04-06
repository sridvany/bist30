import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="BIST Analiz", layout="wide", initial_sidebar_state="expanded")

# Arayüzü güzelleştirmek ve scroll özelliklerini yönetmek için CSS
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; font-weight: bold; }
    /* Sayfanın genel akışını ve scroll özelliğini koru */
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    /* Giriş kutusunu otomatik büyük harf yap */
    input { text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 BIST Profesyonel Günlük Trade Paneli")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Analiz Ayarları")
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
        with st.spinner(f'{symbol_raw} verileri analiz ediliyor...'):
            ticker = format_bist(symbol_raw)
            comp_ticker = format_bist(compare_raw)
            
            # Veri Çekme
            df = yf.download(ticker, period="60d", interval="1d")
            df_comp = yf.download(comp_ticker, period="60d", interval="1d")

            if df.empty or len(df) < 5:
                st.error(f"❌ {symbol_raw} için veri bulunamadı. Lütfen sembolü (Örn: THYAO) kontrol et.")
            else:
                # Sütunları düzleştir (MultiIndex hatasını önlemek için)
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if isinstance(df_comp.columns, pd.MultiIndex): df_comp.columns = df_comp.columns.get_level_values(0)

                # --- 1. GRAFİK VE VOLUME PROFILE ---
                col_left, col_right = st.columns([3, 1])
                
                with col_left:
                    st.subheader(f"📊 {symbol_raw} Teknik Görünüm")
                    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, 
                                        column_widths=[0.85, 0.15], horizontal_spacing=0.01)

                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'], 
                        low=df['Low'], close=df['Close'], name=symbol_raw
                    ), row=1, col=1)

                    # Hacim Profili Hesaplama
                    bins = 20
                    df['PriceBin'] = pd.cut(df['Close'], bins=bins)
                    vprofile = df.groupby('PriceBin', observed=True)['Volume'].sum()
                    bin_centers = [i.mid for i in vprofile.index]

                    fig.add_trace(go.Bar(
                        x=vprofile.values, y=bin_centers, orientation='h',
                        marker_color='rgba(100, 150, 250, 0.4)', name="Hacim"
                    ), row=1, col=2)

                    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark", showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                with col_right:
                    # KİMLER KORELE OLMUŞ BURADA YAZIYOR
                    st.subheader("🔗 Korelasyon Analizi")
                    st.write(f"**{symbol_raw}** vs **{compare_raw}**")
                    
                    combined = pd.concat([df['Close'], df_comp['Close']], axis=1).dropna().tail(30)
                    combined.columns = ['Hisse', 'Kiyas']
                    
                    if not combined.empty:
                        p_corr = combined['Hisse'].corr(combined['Kiyas'], method='pearson')
                        s_corr = combined['Hisse'].corr(combined['Kiyas'], method='spearman')
                        
                        st.metric(f"Pearson ({symbol_raw})", f"{p_corr:.2f}")
                        st.metric(f"Spearman ({compare_raw})", f"{s_corr:.2f}")
                        st.caption("Son 30 günlük kapanış fiyatları baz alınmıştır.")
                    else:
                        st.warning("Kıyaslama verisi bulunamadı.")

                # --- 2. LİSTE (SCROLL ÖZELLİĞİ İLE) ---
                st.divider()
                st.subheader(f"📅 {symbol_raw} - Son 30 Günlük Fiyat Listesi")
                
                res_df = df.tail(30).copy()
                # Değişim hesaplama
                pct_change = df['Close'].pct_change() * 100
                res_df['Değişim %'] = pct_change.tail(30).values.round(2)
                
                def color_sign(val):
                    if val > 0: return f"🟢 +%{val}"
                    if val < 0: return f"🔴 -%{abs(val)}"
                    return "⚪ 0.00"

                res_df['Durum'] = res_df['Değişim %'].apply(color_sign)
                
                # Tablo Görünümü (Height parametresi dikey scroll sağlar)
                final_table = res_df[['Open', 'High', 'Low', 'Close', 'Volume', 'Durum']].sort_index(ascending=False)
                st.dataframe(final_table, use_container_width=True, height=450)

else:
    st.info("👈 Analiz için sol menüden sembolleri girip butona tıklayın.")
    st.image("https://images.unsplash.com/photo-1611974717482-98aa03509162?q=80&w=1000", caption="BIST Data Analysis Environment")
