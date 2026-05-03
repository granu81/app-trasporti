import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import folium_static
from streamlit_geolocation import streamlit_geolocation

# Configurazione Pagina
st.set_page_config(page_title="Gestione Flotta Live", layout="wide")

# Svuota la cache di Streamlit per forzare il download dei dati nuovi
st.cache_data.clear()

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Lettura dati SENZA CACHE (ttl=0)
df = conn.read(ttl=0)

st.sidebar.title("Sistema Trasporti")
ruolo = st.sidebar.radio("Ruolo:", ["💻 Ufficio", "📱 Autista"])

# --- REFRESH AUTOMATICO (Solo Ufficio) ---
if ruolo == "💻 Ufficio":
    # JavaScript per ricaricare la pagina ogni 10 secondi
    st.components.v1.html(
        """
        <script>
        setTimeout(function(){ window.location.reload(); }, 10000);
        </script>
        """,
        height=0,
    )
    st.caption(f"Ultimo aggiornamento dati: {datetime.now().strftime('%H:%M:%S')}")

# --- LATO AUTISTA ---
if ruolo == "📱 Autista":
    st.header("📍 Aggiorna la tua posizione")
    location = streamlit_geolocation()
    
    if location and location.get('latitude'):
        lat_gps = location['latitude']
        lon_gps = location['longitude']
        st.success("✅ GPS Pronto")
        
        if not df.empty:
            nome = st.selectbox("Chi sei?", df['autista'].unique())
            c1, c2 = st.columns(2)
            
            def salva(stato):
                # Creiamo il dataframe aggiornato
                new_df = df.copy()
                mask = new_df['autista'] == nome
                new_df.loc[mask, ['stato', 'ultimo_aggiornamento', 'lat', 'lon']] = [
                    stato, datetime.now().strftime("%H:%M:%S"), lat_gps, lon_gps
                ]
                # Sovrascriviamo il foglio Google
                conn.update(data=new_df)
                st.success(f"Inviato: {stato}!")
                # Forza il ricaricamento immediato dopo l'invio
                st.rerun()

            with c1:
                if st.button("🟢 LIBERO", use_container_width=True): salva("Libero")
            with c2:
                if st.button("🔴 OCCUPATO", use_container_width=True): salva("Occupato")
    else:
        st.warning("⚠️ Attiva il GPS cliccando sul tasto sopra.")

# --- LATO UFFICIO ---
else:
    st.header("Monitoraggio Flotta Live")
    
    # Visualizzazione Tabella
    st.dataframe(df, use_container_width=True)

    # Mappa
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
