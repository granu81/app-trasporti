import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Gestione Flotta Live", layout="wide")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Lettura dati
df = conn.read(ttl="10s") # Aggiorna ogni 10 secondi

st.sidebar.title("Sistema Trasporti")
ruolo = st.sidebar.radio("Ruolo:", ["💻 Ufficio", "📱 Autista"])

if ruolo == "📱 Autista":
    st.header("Aggiorna il tuo stato")
    nome = st.selectbox("Chi sei?", df['autista'].unique())
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🟢 IMPOSTA LIBERO"):
            df.loc[df['autista'] == nome, ['stato', 'ultimo_aggiornamento']] = ["Libero", datetime.now().strftime("%H:%M:%S")]
            conn.update(data=df)
            st.success("Sei Libero!")
    with c2:
        if st.button("🔴 IMPOSTA OCCUPATO"):
            df.loc[df['autista'] == nome, ['stato', 'ultimo_aggiornamento']] = ["Occupato", datetime.now().strftime("%H:%M:%S")]
            conn.update(data=df)
            st.warning("Sei Occupato!")

else:
    st.header("Monitoraggio Flotta")
    st.dataframe(df) # Tabella con i dati reali dal foglio
    
    # Mappa
    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=6)
    for index, row in df.iterrows():
        color = "green" if row['stato'] == "Libero" else "red"
        folium.Marker([row['lat'], row['lon']], popup=row['autista'], icon=folium.Icon(color=color)).add_to(m)
    
    st_folium(m, width=1000)
