import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh  # <-- NUOVO: Per aggiornamento automatico

# Configurazione Pagina
st.set_page_config(page_title="Gestione Flotta Live", layout="wide")

# --- AGGIORNAMENTO AUTOMATICO ---
# Se siamo nel ruolo Ufficio, la pagina si ricarica da sola ogni 10 secondi
ruolo = st.sidebar.radio("Ruolo:", ["💻 Ufficio", "📱 Autista"])

if ruolo == "💻 Ufficio":
    st_autorefresh(interval=10 * 1000, key="datarefresh") # 10000ms = 10 secondi

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# IMPORTANTE: Mettiamo ttl=0 per forzare Streamlit a leggere i dati reali dal foglio ogni volta
df = conn.read(ttl=0) 

# --- LATO AUTISTA ---
if ruolo == "📱 Autista":
    st.header("📍 Aggiorna la tua posizione")
    
    location = streamlit_geolocation()
    
    if location and location.get('latitude'):
        lat_gps = location['latitude']
        lon_gps = location['longitude']
        
        st.success(f"✅ Posizione acquisita correttamente")
        
        if not df.empty and 'autista' in df.columns:
            nome = st.selectbox("Seleziona il tuo nome:", df['autista'].unique())
            
            c1, c2 = st.columns(2)
            
            def salva_tutto(stato):
                try:
                    updated_df = df.copy()
                    mask = updated_df['autista'] == nome
                    updated_df.loc[mask, 'stato'] = stato
                    updated_df.loc[mask, 'ultimo_aggiornamento'] = datetime.now().strftime("%H:%M:%S")
                    updated_df.loc[mask, 'lat'] = lat_gps
                    updated_df.loc[mask, 'lon'] = lon_gps
                    
                    conn.update(data=updated_df)
                    st.toast(f"Inviato: {stato}")
                    st.success("Dati salvati! Puoi chiudere o cambiare stato.")
                except Exception as e:
                    st.error(f"Errore: {e}")

            with c1:
                if st.button("🟢 SEGNALA LIBERO", use_container_width=True):
                    salva_tutto("Libero")
            with c2:
                if st.button("🔴 SEGNALA OCCUPATO", use_container_width=True):
                    salva_tutto("Occupato")
    else:
        st.warning("⚠️ Clicca sul tasto GPS per trasmettere la posizione.")

# --- LATO UFFICIO ---
else:
    st.header("Monitoraggio Flotta in Tempo Reale")
    
    # Pulizia dati
    df_clean = df.copy()
    df_clean['lat'] = pd.to_numeric(df_clean['lat'].astype(str).str.replace(",", "."), errors='coerce')
    df_clean['lon'] = pd.to_numeric(df_clean['lon'].astype(str).str.replace(",", "."), errors='coerce')
    
    # Mostra l'ultimo aggiornamento generale per sicurezza
    st.write(f"Ultimo aggiornamento monitor: {datetime.now().strftime('%H:%M:%S')}")
    
    st.dataframe(df_clean, use_container_width=True)

    if not df_clean.dropna(subset=['lat', 'lon']).empty:
        m = folium.Map(location=[df_clean['lat'].mean(), df_clean['lon'].mean()], zoom_start=6)
        for _, row in df_clean.dropna(subset=['lat', 'lon']).iterrows():
            color = "green" if str(row['stato']).lower() == "libero" else "red"
            folium.Marker(
                location=[row['lat'], row['lon']], 
                popup=f"{row['autista']} - {row['stato']}",
                icon=folium.Icon(color=color, icon="car", prefix="fa")
            ).add_to(m)
        folium_static(m, width=1100, height=500)
