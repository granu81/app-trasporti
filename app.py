import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import pytz  # <-- NUOVO: Gestione fusi orari
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation

# Configurazione Pagina
st.set_page_config(page_title="Gestione Flotta Live", layout="wide")

# Funzione per ottenere l'orario italiano attuale
def get_it_time():
    tz_italy = pytz.timezone('Europe/Rome')
    return datetime.now(tz_italy).strftime("%H:%M:%S")

# Connessione e lettura dati
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
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
        
        df = get_data()
        
        if not df.empty:
            nome = st.selectbox("Chi sei?", df['autista'].unique())
            c1, c2 = st.columns(2)
            
            def salva(stato):
                with st.spinner("Invio dati in corso..."):
                    new_df = df.copy()
                    mask = new_df['autista'] == nome
                    # Usiamo la funzione get_it_time() per l'orario corretto
                    ora_esatta = get_it_time()
                    
                    new_df.loc[mask, ['stato', 'ultimo_aggiornamento', 'lat', 'lon']] = [
                        stato, ora_esatta, lat_gps, lon_gps
                    ]
                    conn.update(data=new_df)
                    st.success(f"Inviato alle {ora_esatta} - Stato: {stato}")
                    st.rerun()

            with c1:
                if st.button("🟢 LIBERO", use_container_width=True): salva("Libero")
            with c2:
                if st.button("🔴 OCCUPATO", use_container_width=True): salva("Occupato")
    else:
        st.warning("⚠️ Attiva il GPS cliccando sul tasto tondo sopra.")

# --- LATO UFFICIO ---
else:
    st.header("Monitoraggio Flotta Live")
    
    col_tasto, col_info = st.columns([1, 3])
    with col_tasto:
        if st.button("🔄 AGGIORNA ORA", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with col_info:
        # Anche qui mostriamo l'orario italiano per coerenza
        st.write(f"⏱️ Ultimo controllo (Roma): **{get_it_time()}**")

    # Refresh automatico ogni 15 secondi
    st.components.v1.html(
        f"""
        <script>
        setTimeout(function(){{ window.location.reload(); }}, 15000);
        </script>
        """,
        height=0,
    )

    df = get_data()
    st.subheader("Dati in tempo reale")
    st.dataframe(df, use_container_width=True)

    # Mappa (Resto del codice invariato)
    df_mappa = df.copy()
    df_mappa['lat'] = pd.to_numeric(df_mappa['lat'].astype(str).str.replace(",", "."), errors='coerce')
    df_mappa['lon'] = pd.to_numeric(df_mappa['lon'].astype(str).str.replace(",", "."), errors='coerce')
    df_mappa = df_mappa.dropna(subset=['lat', 'lon'])

    if not df_mappa.empty:
        m = folium.Map(location=[df_mappa['lat'].mean(), df_mappa['lon'].mean()], zoom_start=6)
        for _, row in df_mappa.iterrows():
            col = "green" if str(row['stato']).lower() == "libero" else "red"
            folium.Marker([row['lat'], row['lon']], tooltip=row['autista'], 
                          icon=folium.Icon(color=col, icon="car", prefix="fa")).add_to(m)
        folium_static(m, width=1100, height=500)
