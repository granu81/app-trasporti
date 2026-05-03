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

# Funzione per leggere i dati (definita qui per poterla richiamare col tasto)
def get_data():
    # ttl=0 evita che Streamlit legga dati vecchi salvati in memoria
    return conn.read(ttl=0)

st.sidebar.title("Sistema Trasporti")
ruolo = st.sidebar.radio("Ruolo:", ["💻 Ufficio", "📱 Autista"])

# --- LATO AUTISTA ---
if ruolo == "📱 Autista":
    st.header("📍 Aggiorna la tua posizione")
    location = streamlit_geolocation()
    
    if location and location.get('latitude'):
        lat_gps = location['latitude']
        lon_gps = location['longitude']
        st.success("✅ GPS Pronto")
        
        # Carichiamo i dati attuali
        df = get_data()
        
        if not df.empty:
            nome = st.selectbox("Chi sei?", df['autista'].unique())
            c1, c2 = st.columns(2)
            
            def salva(stato):
                with st.spinner("Invio dati in corso..."):
                    new_df = df.copy()
                    mask = new_df['autista'] == nome
                    new_df.loc[mask, ['stato', 'ultimo_aggiornamento', 'lat', 'lon']] = [
                        stato, datetime.now().strftime("%H:%M:%S"), lat_gps, lon_gps
                    ]
                    conn.update(data=new_df)
                    st.success(f"Stato impostato su: {stato}")
                    st.balloons()
                    # Dopo l'invio, resettiamo per evitare invii doppi
                    st.rerun()

            with c1:
                if st.button("🟢 LIBERO", use_container_width=True): salva("Libero")
            with c2:
                if st.button("🔴 OCCUPATO", use_container_width=True): salva("Occupato")
    else:
        st.warning("⚠️ Attiva il GPS cliccando sul tasto tondo sopra per trasmettere la posizione.")

# --- LATO UFFICIO ---
else:
    st.header("Monitoraggio Flotta Live")
    
    # --- BARRA DI CONTROLLO AGGIORNAMENTO ---
    col_tasto, col_info = st.columns([1, 3])
    
    with col_tasto:
        if st.button("🔄 AGGIORNA DATI ORA", use_container_width=True):
            st.cache_data.clear() # Svuota la cache interna
            st.rerun()            # Ricarica l'app
            
    with col_info:
        st.write(f"⏱️ Ultimo controllo: **{datetime.now().strftime('%H:%M:%S')}**")
        st.caption("La pagina si ricarica automaticamente ogni 15 secondi.")

    # JavaScript per refresh automatico (ogni 15 secondi)
    st.components.v1.html(
        """
        <script>
        setTimeout(function(){ window.location.reload(); }, 15000);
        </script>
        """,
        height=0,
    )

    # Lettura dati effettiva
    df = get_data()

    # Visualizzazione Tabella
    st.subheader("Dati in tempo reale")
    st.dataframe(df, use_container_width=True)

    # Elaborazione Mappa
    st.subheader("Mappa Geolocalizzazione")
    df_mappa = df.copy()
    
    # Pulizia coordinate: gestisce sia punti che virgole
    df_mappa['lat'] = pd.to_numeric(df_mappa['lat'].astype(str).str.replace(",", "."), errors='coerce')
    df_mappa['lon'] = pd.to_numeric(df_mappa['lon'].astype(str).str.replace(",", "."), errors='coerce')
    df_mappa = df_mappa.dropna(subset=['lat', 'lon'])

    if not df_mappa.empty:
        # Centra la mappa sulla media delle posizioni
        centro_lat = df_mappa['lat'].mean()
        centro_lon = df_mappa['lon'].mean()
        
        m = folium.Map(location=[centro_lat, centro_lon], zoom_start=6)
        
        for _, row in df_mappa.iterrows():
            # Colore dinamico in base allo stato
            stato_pulito = str(row['stato']).strip().lower()
            colore_marker = "green" if stato_pulito == "libero" else "red"
            
            folium.Marker(
                [row['lat'], row['lon']], 
                popup=f"<b>{row['autista']}</b><br>Stato: {row['stato']}<br>Ore: {row['ultimo_aggiornamento']}",
                tooltip=row['autista'], 
                icon=folium.Icon(color=colore_marker, icon="car", prefix="fa")
            ).add_to(m)
        
        folium_static(m, width=1100, height=500)
    else:
        st.info("Nessun dato GPS valido trovato nel foglio per mostrare la mappa.")
