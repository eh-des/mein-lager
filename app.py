import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Lager-Scanner", page_icon="📦")

# --- FUNKTIONEN ---
def load_initial_data():
    try:
        df = pd.read_excel("Lagerbestand.xlsx")
        df["Status"] = df["Status"].astype(str)
        df["Datum_Ausgang"] = df["Datum_Ausgang"].astype(object) 
        return df
    except:
        # Falls die Datei mal fehlt, erstellen wir eine leere Struktur
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lagerbestand')
    return output.getvalue()

# --- INITIALISIERUNG ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_initial_data()

# --- NAVIGATION ---
st.title("📦 Mein Lager-Prototyp")
menu = st.sidebar.radio("Menü", ["Lagerbestand & Scanner", "Wareneingang (Neu aufnehmen)"])

# --- SEITE 1: SCANNER & BESTAND ---
if menu == "Lagerbestand & Scanner":
    df = st.session_state.lager_daten
    lager_aktuell = df[df["Status"] == "Eingang"]

    st.subheader("Aktueller Lagerbestand")
    st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)

    st.divider()
    st.subheader("QR-Scanner (Verbrauch)")
    scan_input = st.text_input("ID einscannen/tippen:", key="scanner_input").strip()

    if scan_input:
        treffer_index = df.index[df["QR_ID"].astype(str) == scan_input].tolist()
        if treffer_index:
            idx = treffer_index[0]
            material = df.at[idx, "Material"]
            if df.at[idx, "Status"] == "Eingang":
                st.success(f"Gefunden: **{material}**")
                if st.button(f"✅ {material} verbrauchen"):
                    st.session_state.lager_daten.at[idx, "Status"] = "Verbraucht"
                    st.session_state.lager_daten.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                    st.rerun()
            else:
                st.warning(f"Schon am {df.at[idx, 'Datum_Ausgang']} verbraucht!")
        else:
            st.error("ID unbekannt.")

# --- SEITE 2: WARENEINGANG ---
else:
    st.subheader("Neues Gebinde aufnehmen")
    
    with st.form("neues_material_form"):
        neu_id = st.text_input("QR-ID (scannen oder vergeben)")
        neu_name = st.text_input("Material Name")
        neu_lieferant = st.text_input("Lieferant")
        neu_preis = st.number_input("Preis pro Gebinde", min_value=0.0, step=0.01)
        
        submitted = st.form_submit_button("In den Bestand aufnehmen")
        
        if submitted:
            if neu_id and neu_name:
                # Prüfen, ob ID schon existiert
                if neu_id in st.session_state.lager_daten["QR_ID"].astype(str).values:
                    st.error("Fehler: Diese ID existiert bereits im System!")
                else:
                    neue_zeile = {
                        "QR_ID": neu_id,
                        "Material": neu_name,
                        "Lieferant": neu_lieferant,
                        "Status": "Eingang",
                        "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"),
                        "Datum_Ausgang": "",
                        "Preis": neu_preis
                    }
                    st.session_state.lager_daten = pd.concat([st.session_state.lager_daten, pd.DataFrame([neue_zeile])], ignore_index=True)
                    st.success(f"{neu_name} wurde erfolgreich hinzugefügt!")
            else:
                st.warning("Bitte ID und Name ausfüllen.")

# --- EXPORT ---
st.sidebar.divider()
excel_data = to_excel(st.session_state.lager_daten)
st.sidebar.download_button(label="📥 Inventur-Liste Exportieren", data=excel_data, file_name="Lager_Update.xlsx")
