import streamlit as st
import pandas as pd
import os
st.write("Ich sehe folgende Dateien im Ordner:", os.listdir())
st.set_page_config(page_title="Lager-Scanner", page_icon="📦")

st.title("📦 Mein Lager-Prototyp")

# 1. Daten laden
try:
    # Wir lesen die Excel-Datei ein
    df = pd.read_excel("Lagerbestand.xlsx")
except Exception as e:
    st.error("Datei 'Lagerbestand.xlsx' wurde nicht gefunden. Bitte hochladen!")
    st.stop()

# 2. Anzeige des aktuellen Bestands (nur was noch im 'Eingang' ist)
st.subheader("Aktueller Lagerbestand")
lager_aktuell = df[df["Status"] == "Eingang"]
st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)

# 3. Der "Scanner" Bereich
st.divider()
st.subheader("Barcode/QR Scan Simulation")
scan_input = st.text_input("ID hier einscannen (oder tippen):").strip()

if scan_input:
    # Suche in der Tabelle nach der ID
    treffer = df[df["QR_ID"] == scan_input]
    
    if not treffer.empty:
        material_name = treffer["Material"].values[0]
        status_jetzt = treffer["Status"].values[0]
        
        st.success(f"Gefunden: **{material_name}**")
        st.info(f"Aktueller Status: {status_jetzt}")
        
        if status_jetzt == "Eingang":
            if st.button(f"✅ {material_name} als VERBRAUCHT markieren"):
                st.balloons()
                st.write("*(Hier würden wir im nächsten Schritt die Excel-Datei speichern)*")
        else:
            st.warning("Dieses Gebinde wurde bereits verbraucht!")
    else:
        st.error("ID nicht im System gefunden. Bitte Stammdaten prüfen.")
