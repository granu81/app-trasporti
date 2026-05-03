import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation

# Configurazione Pagina
st.set_page_config(page_title="Gestione Flotta Live", layout="wide")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Lettura dati (ttl=0 forza il caricamento dei dati nuovi ogni volta)
df = conn.read(ttl=0)

st.sidebar.title("Sistema Trasporti")
ruolo = st.sidebar.radio("Ruolo:", ["💻 Ufficio", "📱 Autista"])

# --- AGGIORNAMENTO AUTOMATICO NATIVO (Solo per Ufficio) ---
if ruolo == "💻 Ufficio":
    # Questo comando dice a Streamlit di ricaricare la pagina tra 10 secondi
    # Non richiede installazioni esterne!
    st.info(f"Monitor attivo - Prossimo aggiornamento automatico tra 10 secondi...")
    st.empty() # Crea uno spazio vuoto per forzare il refresh
    
    # JavaScript per forzare il refresh della pagina ogni 10 secondi
    st.components.v1.html(
        """
        <script>
        window.parent.document.dispatchEvent(new CustomEvent("st_autorefresh", {detail: 10000}));
        setTimeout(function(){ window.location.reload(); }, 10000);
        </script>
        """,
        height=0,
    )

# --- LATO AUTISTA ---
if ruolo == "📱 Autista":
    st.header("📍 Aggiorna la tua posizione")
    
    location = streamlit_geolocation()
    
    if location and location.get('latitude'):
        lat_gps = location['latitude']
        lon_gps = location['longitude']
        
        st.success(f"✅ Posizione acquisita")
        
        if not df.empty and 'autista' in df.columns:
            nome = st.selectbox("Chi sei?", df['autista'].unique())
            
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
                    st.success(f"Dati inviati! Stato attuale: {stato}")
                except Exception as e:
                    st.error(f"Errore: {e}")

            with c1:
                if st.button("🟢 SEGNALA LIBERO", use_container_width=True):
                    salva_tutto("Libero")
            with c2:
                if st.button("🔴 SEGNALA OCCUPATO", use_container_width=True):
                    salva_tutto("Occupato")
    else:
        st.warning("⚠️ Clicca sul tasto GPS sopra per trasmettere.")

# --- LATO UFFICIO ---
else:
    st.header(f"Monitoraggio Flotta - {datetime.now().strftime('%H:%M:%S')}")
    
    # Pulizia dati per la mappa
    df_clean = df.copy()
    df_clean['lat'] = pd.to_numeric(df_clean['lat'].astype(str).str.replace(",", "."), errors='coerce')
    df_clean['lon'] = pd.to_numeric(df_clean['lon'].astype(str).str.replace(",", "."), errors='coerce')
    
    st.dataframe(df_clean, use_container_width=True)

    if not df_clean.dropna(subset=['lat', 'lon']).empty:
        try:
            m = folium.Map(location=[df_clean['lat'].mean(), df_clean['lon'].mean()], zoom_start=6)
            for _, row in df_clean.dropna(subset=['lat', 'lon']).iterrows():
                color = "green" if str(row['stato']).lower() == "libero" else "red"
                folium.Marker(
                    location=[row['lat'], row['lon']], 
                    popup=f"{row['autista']} - {row['stato']}",
                    icon=folium.Icon(color=color, icon="car", prefix="fa")
                ).add_to(m)
            folium_static(m, width=1100, height=500)
        except:
            st.error("Errore nel caricamento della mappa.")
