import streamlit as st
import pandas as pd

st.set_page_config(page_title="Lager-Scanner", page_icon="📦")

st.title("📦 Mein Lager-Prototyp")

# Daten laden
@st.cache_data # Das macht die App schneller
def load_data():
    return pd.read_excel("Lagerbestand.xlsx")

try:
    df = load_data()
    
    # Anzeige des aktuellen Bestands
    st.subheader("Aktueller Lagerbestand")
    # Wir zeigen nur Gebinde an, die noch nicht verbraucht sind
    lager_aktuell = df[df["Status"] == "Eingang"]
    st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)

    # Der Scanner Bereich
    st.divider()
    st.subheader("Barcode/QR Scan Simulation")
    scan_input = st.text_input("ID hier einscannen (oder tippen):").strip()

    if scan_input:
        treffer = df[df["QR_ID"].astype(str) == scan_input]
        
        if not treffer.empty:
            material = treffer["Material"].values[0]
            st.success(f"Gefunden: **{material}**")
            
            if st.button(f"✅ {material} verbrauchen"):
                st.balloons()
                st.info("Logik zum Speichern bauen wir als Nächstes!")
        else:
            st.error("ID nicht gefunden.")

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")
