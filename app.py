import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation

# 1. Configurazione Pagina
st.set_page_config(page_title="Gestione Flotta Live", layout="wide", page_icon="🚚")

# 2. Funzioni di Utilità
def get_it_time():
    """Restituisce l'orario attuale in Italia"""
    tz_italy = pytz.timezone('Europe/Rome')
    return datetime.now(tz_italy).strftime("%H:%M:%S")

def color_stato(val):
    """Assegna colori alla tabella in base allo stato"""
    if val == "Libero":
        return 'background-color: #d4edda; color: #155724; font-weight: bold'
    elif val == "Occupato":
        return 'background-color: #f8d7da; color: #721c24; font-weight: bold'
    return ''

# 3. Connessione e Lettura Dati
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    # Svuota la cache interna prima di leggere per garantire dati freschi
    st.cache_data.clear()
    return conn.read(ttl=0)

# 4. Sidebar e Navigazione
st.sidebar.title("🚚 Sistema Trasporti")
ruolo = st.sidebar.radio("Seleziona Ruolo:", ["💻 Ufficio", "📱 Autista"])

# --- LATO AUTISTA ---
if ruolo == "📱 Autista":
    st.header("📍 Pannello Autista")
    st.info("Attiva il GPS e seleziona il tuo stato attuale.")
    
    location = streamlit_geolocation()
    
    if location and location.get('latitude'):
        lat_gps = location['latitude']
        lon_gps = location['longitude']
        st.success(f"✅ GPS Attivo (Lat: {round(lat_gps,4)}, Lon: {round(lon_gps,4)})")
        
        df = get_data()
        
        if not df.empty:
            nome = st.selectbox("Chi sta guidando?", df['autista'].unique())
            st.write("---")
            c1, c2 = st.columns(2)
            
            def salva(stato):
                with st.spinner("Aggiornamento foglio in corso..."):
                    new_df = df.copy()
                    mask = new_df['autista'] == nome
                    ora_esatta = get_it_time()
                    
                    new_df.loc[mask, ['stato', 'ultimo_aggiornamento', 'lat', 'lon']] = [
                        stato, ora_esatta, lat_gps, lon_gps
                    ]
                    conn.update(data=new_df)
                    st.toast(f"Stato aggiornato: {stato} alle {ora_esatta}")
                    st.rerun()

            with c1:
                if st.button("🟢 SEGNALA LIBERO", use_container_width=True): salva("Libero")
            with c2:
                if st.button("🔴 SEGNALA OCCUPATO", use_container_width=True): salva("Occupato")
    else:
        st.warning("📡 In attesa del segnale GPS... Clicca sul tasto 'Get Location' se presente.")

# --- LATO UFFICIO ---
else:
    st.header("💻 Monitoraggio Flotta Live")
    
    # Barra controlli superiore
    col_tasto, col_info = st.columns([1, 3])
    with col_tasto:
        if st.button("🔄 FORZA AGGIORNAMENTO", use_container_width=True):
            st.rerun()
    with col_info:
        st.write(f"⏱️ Ultima sincronizzazione Roma: **{get_it_time()}**")

    # Script Refresh Automatico (15 secondi)
    st.components.v1.html(
        f"<script>setTimeout(function(){{ window.location.reload(); }}, 15000);</script>",
        height=0,
    )

    # Caricamento dati
    df = get_data()
    
    if not df.empty:
        # Tabella Stilizzata
        st.subheader("Stato Mezzi")
        st.dataframe(
        try:
            styled_df = df.style.map(color_stato, subset=['stato'])
        except AttributeError:
            styled_df = df.style.applymap(color_stato, subset=['stato'])
            
        st.dataframe(
            styled_df, 
            use_container_width=True,
            hide_index=True
        )    

        st.write("---")
        
        # Filtro per la mappa
        st.subheader("Mappa Geolocalizzazione")
        filtro = st.multiselect("Filtra per stato:", ["Libero", "Occupato"], default=["Libero", "Occupato"])
        
        # Elaborazione dati per mappa
        df_mappa = df.copy()
        df_mappa['lat'] = pd.to_numeric(df_mappa['lat'].astype(str).str.replace(",", "."), errors='coerce')
        df_mappa['lon'] = pd.to_numeric(df_mappa['lon'].astype(str).str.replace(",", "."), errors='coerce')
        df_mappa = df_mappa.dropna(subset=['lat', 'lon'])
        
        # Applica filtro
        df_mappa = df_mappa[df_mappa['stato'].isin(filtro)]

        if not df_mappa.empty:
            m = folium.Map(location=[df_mappa['lat'].mean(), df_mappa['lon'].mean()], zoom_start=6)
            for _, row in df_mappa.iterrows():
                col = "green" if str(row['stato']).lower() == "libero" else "red"
                folium.Marker(
                    [row['lat'], row['lon']], 
                    popup=f"<b>{row['autista']}</b><br>Stato: {row['stato']}<br>Aggiornato: {row['ultimo_aggiornamento']}",
                    tooltip=f"{row['autista']} ({row['stato']})",
                    icon=folium.Icon(color=col, icon="truck", prefix="fa")
                ).add_to(m)
            folium_static(m, width=1100, height=500)
        else:
            st.info("Nessun autista da mostrare sulla mappa con i filtri selezionati.")
    else:
        st.error("Il foglio Google sembra vuoto o non raggiungibile.")
