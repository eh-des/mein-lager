import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Lager-Scanner", page_icon="📦")

# --- FUNKTIONEN ---
def load_data():
    file_path = "Lagerbestand.xlsx"
    try:
        df = pd.read_excel(file_path)
        # Spaltennamen säubern
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except:
        # Wenn Datei nicht da oder kaputt: Erstelle eine saubere neue Struktur
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# --- INITIALISIERUNG ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION ---
st.title("📦 Lager-Verwaltung v2.1")
menu = st.sidebar.radio("Menü", ["Bestand & Scanner", "Wareneingang"])

# --- SEITE 1: BESTAND & SCANNER ---
if menu == "Bestand & Scanner":
    df = st.session_state.lager_daten
    # Filter: Nur was im Eingang ist
    lager_aktuell = df[df["Status"] == "Eingang"]

    st.subheader("Aktueller Lagerbestand")
    if not lager_aktuell.empty:
        st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)
    else:
        st.info("Das Lager ist aktuell leer.")

    st.divider()
    st.subheader("QR-Scanner (Verbrauch)")
    scan_input = st.text_input("ID einscannen/tippen:", key="scanner_input").strip()

    if scan_input:
        # Suche ID (als String vergleichen)
        idx_list = df.index[df["QR_ID"].astype(str) == scan_input].tolist()
        if idx_list:
            idx = idx_list[0]
            if df.at[idx, "Status"] == "Eingang":
                st.success(f"Gefunden: {df.at[idx, 'Material']}")
                if st.button("Verbrauch bestätigen"):
                    st.session_state.lager_daten.at[idx, "Status"] = "Verbraucht"
                    st.session_state.lager_daten.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                    st.rerun()
            else:
                st.warning("Dieses Gebinde ist bereits verbraucht.")
        else:
            st.error("ID nicht gefunden.")

# --- SEITE 2: WARENEINGANG ---
else:
    st.subheader("Neues Material aufnehmen")
    with st.form("input_form", clear_on_submit=True):
        f_id = st.text_input("QR-ID")
        f_name = st.text_input("Material Name")
        f_lief = st.text_input("Lieferant")
        f_preis = st.number_input("Preis", min_value=0.0, format="%.2f")
        
        btn = st.form_submit_button("Speichern")
        
        if btn:
            if f_id and f_name:
                neue_daten = {
                    "QR_ID": str(f_id),
                    "Material": str(f_name),
                    "Lieferant": str(f_lief),
                    "Status": "Eingang",
                    "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"),
                    "Datum_Ausgang": "",
                    "Preis": float(f_preis)
                }
                # Hinzufügen zum Speicher
                st.session_state.lager_daten = pd.concat([st.session_state.lager_daten, pd.DataFrame([neue_daten])], ignore_index=True)
                st.success(f"{f_name} wurde vorgemerkt!")
            else:
                st.error("ID und Name sind Pflichtfelder!")

# --- EXPORT ---
st.sidebar.divider()
st.sidebar.subheader("Speichern & Download")
st.sidebar.write("Änderungen gehen beim Neuladen der Seite verloren, wenn du nicht exportierst!")
excel_data = to_excel(st.session_state.lager_daten)
st.sidebar.download_button("📥 Excel Herunterladen", data=excel_data, file_name="Lager_Aktuell.xlsx")
