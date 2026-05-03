import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation # Cambiato componente

# Configurazione Pagina
st.set_page_config(page_title="Gestione Flotta Live", layout="wide")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="5s")

st.sidebar.title("Sistema Trasporti")
ruolo = st.sidebar.radio("Ruolo:", ["💻 Ufficio", "📱 Autista"])

# --- LATO AUTISTA ---
if ruolo == "📱 Autista":
    st.header("📍 Aggiorna la tua posizione")
    
    # Questo pulsante è nativo e molto più stabile
    st.write("Clicca sul tasto sotto per attivare il GPS:")
    location = streamlit_geolocation()
    
    # Se il sensore restituisce i dati
    if location and location.get('latitude'):
        lat_gps = location['latitude']
        lon_gps = location['longitude']
        
        st.success(f"✅ Posizione bloccata: {lat_gps}, {lon_gps}")
        
        if not df.empty and 'autista' in df.columns:
            nome = st.selectbox("Seleziona il tuo nome:", df['autista'].unique())
            
            st.write("---")
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
                    st.balloons()
                    st.toast(f"Aggiornato con successo come {stato}!")
                except Exception as e:
                    st.error(f"Errore di rete: {e}")

            with c1:
                if st.button("🟢 SEGNALA COME LIBERO", use_container_width=True):
                    salva_tutto("Libero")
            with c2:
                if st.button("🔴 SEGNALA COME OCCUPATO", use_container_width=True):
                    salva_tutto("Occupato")
    else:
        st.warning("⚠️ Il GPS non è ancora attivo. Clicca sul simbolo della posizione sopra.")

# --- LATO UFFICIO ---
else:
    st.header("Monitoraggio Flotta")
    # Pulizia dati per sicurezza prima della mappa
    df_clean = df.copy()
    df_clean['lat'] = pd.to_numeric(df_clean['lat'].astype(str).str.replace(",", "."), errors='coerce')
    df_clean['lon'] = pd.to_numeric(df_clean['lon'].astype(str).str.replace(",", "."), errors='coerce')
    
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
