import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import folium_static
from streamlit_js_eval import get_geolocation # IMPORTANTE: Serve per il GPS

# Configurazione Pagina
st.set_page_config(page_title="Gestione Flotta Live", layout="wide")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Lettura dati (aggiornamento ogni 5 secondi)
df = conn.read(ttl="5s")

st.sidebar.title("Sistema Trasporti")
ruolo = st.sidebar.radio("Ruolo:", ["💻 Ufficio", "📱 Autista"])

# --- LATO AUTISTA ---
if ruolo == "📱 Autista":
    st.header("📍 Aggiorna Posizione e Stato")
    
    # Rilevamento GPS Automatico
    loc = get_geolocation()
    
    if not df.empty and 'autista' in df.columns:
        nome = st.selectbox("Chi sei?", df['autista'].unique())
        
        # Se il GPS rileva la posizione, pre-compiliamo i campi
        gps_lat = ""
        gps_lon = ""
        if loc:
            gps_lat = str(loc['coords']['latitude'])
            gps_lon = str(loc['coords']['longitude'])
            st.success(f"✅ GPS Attivo: Posizione rilevata con successo!")
        else:
            st.warning("📡 In attesa del GPS... (Assicurati di aver cliccato 'Consenti' sul browser)")

        st.write("Conferma o inserisci le coordinate:")
        c_lat, c_lon = st.columns(2)
        with c_lat:
            nuova_lat = st.text_input("Latitudine", value=gps_lat, key="lat_input")
        with c_lon:
            nuova_lon = st.text_input("Longitudine", value=gps_lon, key="lon_input")
        
        st.write("---")
        
        c1, c2 = st.columns(2)
        
        def aggiorna_dati(nuovo_stato):
            if not nuova_lat or not nuova_lon:
                st.error("⚠️ Errore: Coordinate mancanti!")
                return
            
            try:
                updated_df = df.copy()
                mask = updated_df['autista'] == nome
                
                # Aggiornamento campi
                updated_df.loc[mask, 'stato'] = nuovo_stato
                updated_df.loc[mask, 'ultimo_aggiornamento'] = datetime.now().strftime("%H:%M:%S")
                updated_df.loc[mask, 'lat'] = str(nuova_lat).replace(",", ".")
                updated_df.loc[mask, 'lon'] = str(nuova_lon).replace(",", ".")
                
                conn.update(data=updated_df)
                st.balloons()
                st.success(f"Dati inviati correttamente per {nome}!")
            except Exception as e:
                st.error(f"Errore durante l'invio al foglio: {e}")

        with c1:
            if st.button("🟢 IMPOSTA LIBERO", use_container_width=True):
                aggiorna_dati("Libero")
        
        with c2:
            if st.button("🔴 IMPOSTA OCCUPATO", use_container_width=True):
                aggiorna_dati("Occupato")
                
    else:
        st.error("Errore: Tabella dati non valida.")

# --- LATO UFFICIO ---
else:
    st.header("Monitoraggio Flotta")
    st.dataframe(df, use_container_width=True)

    st.subheader("Mappa Geolocalizzazione")

    if not df.empty:
        df_mappa = df.copy()
        df_mappa['lat'] = pd.to_numeric(df_mappa['lat'], errors='coerce')
        df_mappa['lon'] = pd.to_numeric(df_mappa['lon'], errors='coerce')
        df_mappa = df_mappa.dropna(subset=['lat', 'lon'])

        if not df_mappa.empty:
            try:
                centro_lat = df_mappa['lat'].mean()
                centro_lon = df_mappa['lon'].mean()
                m = folium.Map(location=[centro_lat, centro_lon], zoom_start=6)

                for index, row in df_mappa.iterrows():
                    colore = "green" if str(row['stato']).lower() == "libero" else "red"
                    folium.Marker(
                        location=[row['lat'], row['lon']], 
                        popup=f"{row['autista']} - {row['stato']}",
                        tooltip=row['autista'],
                        icon=folium.Icon(color=colore, icon="car", prefix="fa")
                    ).add_to(m)

                folium_static(m, width=1100, height=500)
            except Exception as e:
                st.error(f"Errore mappa: {e}")
        else:
            st.warning("⚠️ Nessun autista ha ancora inviato la posizione.")
