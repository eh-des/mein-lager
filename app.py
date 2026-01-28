import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Lager-Scanner", page_icon="📦")

# --- FUNKTIONEN ---
def load_initial_data():
    df = pd.read_excel("Lagerbestand.xlsx")
    df["Status"] = df["Status"].astype(str)
    df["Datum_Ausgang"] = df["Datum_Ausgang"].astype(object) 
    return df

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Lagerbestand')
    return output.getvalue()

# --- INITIALISIERUNG ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_initial_data()

# --- HAUPTPROGRAMM ---
st.title("📦 Mein Lager-Prototyp")

# Aktuellen Bestand filtern
df = st.session_state.lager_daten
lager_aktuell = df[df["Status"] == "Eingang"]
lager_verbraucht = df[df["Status"] == "Verbraucht"]

st.subheader("Aktueller Lagerbestand")
st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)

st.divider()
st.subheader("QR-Scanner Simulation")
scan_input = st.text_input("ID einscannen/tippen:", key="scanner_input").strip()

if scan_input:
    treffer_index = df.index[df["QR_ID"].astype(str) == scan_input].tolist()
    
    if treffer_index:
        idx = treffer_index[0]
        material = df.at[idx, "Material"]
        status = df.at[idx, "Status"]
        
        if status == "Eingang":
            st.success(f"Gefunden: **{material}**")
            if st.button(f"✅ {material} verbrauchen"):
                st.session_state.lager_daten.at[idx, "Status"] = "Verbraucht"
                st.session_state.lager_daten.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                st.balloons()
                st.rerun()
        else:
            st.warning(f"Bereits am {df.at[idx, 'Datum_Ausgang']} verbraucht!")
    else:
        st.error("ID unbekannt.")

# --- EXPORT BEREICH ---
st.sidebar.divider()
st.sidebar.subheader("Daten sichern")
st.sidebar.write("Lade hier den aktuellen Stand als Excel-Datei herunter:")

excel_data = to_excel(st.session_state.lager_daten)
st.sidebar.download_button(
    label="📥 Inventur-Liste Exportieren",
    data=excel_data,
    file_name=f"Lagerbestand_Update_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

if not lager_verbraucht.empty:
    st.sidebar.divider()
    st.sidebar.write(f"Heute bereits {len(lager_verbraucht)} Teile verbraucht.")
