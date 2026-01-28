import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Lager-Scanner", page_icon="📦")

# --- FUNKTIONEN ---
def load_initial_data():
    df = pd.read_excel("Lagerbestand.xlsx")
    # WICHTIG: Spalten flexibel machen, um Text/Daten speichern zu können
    df["Status"] = df["Status"].astype(str)
    df["Datum_Ausgang"] = df["Datum_Ausgang"].astype(object) 
    return df

# --- INITIALISIERUNG ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_initial_data()

# --- HAUPTPROGRAMM ---
st.title("📦 Mein Lager-Prototyp")

# Aktuellen Bestand filtern (nur "Eingang")
df = st.session_state.lager_daten
lager_aktuell = df[df["Status"] == "Eingang"]

st.subheader("Aktueller Lagerbestand")
st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)

st.divider()
st.subheader("QR-Scanner Simulation")
scan_input = st.text_input("ID einscannen/tippen:", key="scanner_input").strip()

if scan_input:
    # Suche in der Spalte QR_ID
    treffer_index = df.index[df["QR_ID"].astype(str) == scan_input].tolist()
    
    if treffer_index:
        idx = treffer_index[0]
        material = df.at[idx, "Material"]
        status = df.at[idx, "Status"]
        
        if status == "Eingang":
            st.success(f"Gefunden: **{material}**")
            
            if st.button(f"✅ {material} als VERBRAUCHT markieren"):
                # Status und Datum im Kurzzeitgedächtnis ändern
                st.session_state.lager_daten.at[idx, "Status"] = "Verbraucht"
                st.session_state.lager_daten.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                
                st.balloons()
                st.success(f"{material} wurde aus dem Bestand ausgebucht!")
                # Kurze Pause, dann neu laden
                st.rerun()
        else:
            ausgangs_datum = df.at[idx, 'Datum_Ausgang']
            st.warning(f"Achtung: **{material}** wurde bereits am {ausgangs_datum} verbraucht!")
    else:
        st.error("ID unbekannt.")
