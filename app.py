import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium

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
    st.header("Aggiorna il tuo stato")
    
    if not df.empty and 'autista' in df.columns:
        nome = st.selectbox("Chi sei?", df['autista'].unique())
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🟢 IMPOSTA LIBERO", use_container_width=True):
                df.loc[df['autista'] == nome, ['stato', 'ultimo_aggiornamento']] = ["Libero", datetime.now().strftime("%H:%M:%S")]
                conn.update(data=df)
                st.success(f"{nome} ora è LIBERO")
        with c2:
            if st.button("🔴 IMPOSTA OCCUPATO", use_container_width=True):
                df.loc[df['autista'] == nome, ['stato', 'ultimo_aggiornamento']] = ["Occupato", datetime.now().strftime("%H:%M:%S")]
                conn.update(data=df)
                st.warning(f"{nome} ora è OCCUPATO")
    else:
        st.error("Errore: La colonna 'autista' non è stata trovata nel foglio Google.")

# --- LATO UFFICIO ---
else:
    st.header("Monitoraggio Flotta")
    
    # Mostriamo la tabella per controllo
    st.dataframe(df)

    st.subheader("Mappa Geolocalizzazione")

    # PULIZIA DATI "BLINDATA" PER LA MAPPA
    if not df.empty:
        # Creiamo una copia per non sporcare il dataframe originale
        df_mappa = df.copy()
        
        # Trasformiamo lat e lon in numeri. Se c'è un errore (es. una virgola o testo), diventa NaN
        df_mappa['lat'] = pd.to_numeric(df_mappa['lat'], errors='coerce')
        df_mappa['lon'] = pd.to_numeric(df_mappa['lon'], errors='coerce')
        
        # Eliminiamo tutte le righe che hanno NaN in lat o lon
        df_mappa = df_mappa.dropna(subset=['lat', 'lon'])

        if not df_mappa.empty:
            try:
                # Calcolo del centro mappa (media delle posizioni valide)
                centro_lat = df_mappa['lat'].mean()
                centro_lon = df_mappa['lon'].mean()
                
                # Creazione mappa
                m = folium.Map(location=[centro_lat, centro_lon], zoom_start=6)

                for index, row in df_mappa.iterrows():
                    # Gestione colore dinamico
                    stato_testo = str(row['stato']).strip().lower()
                    colore = "green" if stato_testo == "libero" else "red"
                    
                    folium.Marker(
                        location=[row['lat'], row['lon']], 
                        popup=f"<b>{row['autista']}</b><br>Stato: {row['stato']}<br>Aggiornato: {row['ultimo_aggiornamento']}",
                        tooltip=row['autista'],
                        icon=folium.Icon(color=colore, icon="car", prefix="fa")
                    ).add_to(m)

                # Rendering mappa - returned_objects=[] evita ricaricamenti inutili
                st_folium(m, width=1100, height=500, returned_objects=[])
            
            except Exception as e:
                st.error(f"Errore tecnico nella creazione della mappa: {e}")
        else:
            st.warning("⚠️ Nessuna coordinata valida trovata nel foglio Google. Assicurati che le colonne 'lat' e 'lon' contengano numeri col PUNTO (es: 45.46).")
    else:
        st.info("Il foglio Google sembra vuoto. Aggiungi i dati degli autisti.")
