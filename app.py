import streamlit as st
import pandas as pd
from datetime import datetime
import io
import cv2
import numpy as np
from github import Github

# --- KONFIGURATION ---
st.set_page_config(page_title="Lager-Profi", page_icon="📦", layout="wide")

GITHUB_REPO_PATH = "eh-des/mein-lager" 
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- HILFSFUNKTIONEN ---

def save_to_github(df):
    try:
        if "GITHUB_TOKEN" not in st.secrets:
            st.error("❌ GITHUB_TOKEN fehlt!")
            return False
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        try:
            contents = repo.get_contents(GITHUB_FILENAME)
            repo.update_file(path=GITHUB_FILENAME, message="Update", content=excel_data, sha=contents.sha)
            return True
        except:
            repo.create_file(path=GITHUB_FILENAME, message="Initial", content=excel_data)
            return True
    except Exception as e:
        st.error(f"GitHub-Fehler: {e}")
        return False

def load_data():
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH)
        contents = repo.get_contents(GITHUB_FILENAME)
        return pd.read_excel(io.BytesIO(contents.decoded_content))
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

# --- INITIALISIERUNG ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- SIDEBAR ---
st.sidebar.title("📦 Lager-Optionen")

if st.sidebar.button("🔄 Daten neu laden"):
    st.session_state.lager_daten = load_data()
    st.rerun()

# Export
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    st.session_state.lager_daten.to_excel(writer, index=False)
st.sidebar.download_button("📥 Excel Logbuch (Eingang & Ausgang)", buf.getvalue(), f"Logbuch_{datetime.now().strftime('%d-%m')}.xlsx")

if st.sidebar.button("🗑️ Gesamte Liste löschen"):
    empty_df = pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])
    if save_to_github(empty_df):
        st.session_state.lager_daten = empty_df
        st.rerun()

st.sidebar.divider()
menu = st.sidebar.radio("Menü:", ["📥 Annahme", "📤 Ausgang", "📊 Bestand"])

# --- SCANNER FUNKTION ---
def scan():
    img = st.camera_input("Scanner")
    if img:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cv2.imdecode(np.asarray(bytearray(img.read()), dtype=np.uint8), 1))
        return data
    return None

# --- LOGIK ---

if menu == "📥 Annahme":
    st.header("Wareneingang")
    data = scan()
    if data:
        p = data.split(";")
        if len(p) >= 2:
            s_id, s_mat = p[0].strip(), p[1].strip()
            
            # WICHTIG: Wir prüfen im aktuellen Session-State
            df = st.session_state.lager_daten
            ist_vorhanden = not df[(df["QR_ID"] == s_id) & (df["Status"] == "Eingang")].empty
            
            if ist_vorhanden:
                st.error(f"❌ '{s_mat}' ist bereits im Lager!")
            else:
                st.success(f"Gelesen: {s_mat}")
                if st.button("Speichern"):
                    nz = {
                        "QR_ID": s_id, "Material": s_mat, 
                        "Lieferant": p[2] if len(p)>2 else "", 
                        "Status": "Eingang", 
                        "Datum_Eingang": datetime.now().strftime("%d.%m.%Y %H:%M:%S"), 
                        "Datum_Ausgang": "", 
                        "Preis": float(p[3]) if len(p)>3 else 0.0
                    }
                    st.session_state.lager_daten = pd.concat([st.session_state.lager_daten, pd.DataFrame([nz])], ignore_index=True)
                    if save_to_github(st.session_state.lager_daten):
                        st.success("Gespeichert!")
                        st.rerun() # Sofortiger Neustart, damit die Fehlermeldung nicht erscheint
        else:
            st.error("QR-Format fehlerhaft!")

elif menu == "📤 Ausgang":
    st.header("Warenausgang")
    sid = scan()
    if sid:
        clean_id = sid.split(";")[0].strip()
        df = st.session_state.lager_daten
        t_index = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")].index
        
        if not t_index.empty:
            st.warning(f"Material: {df.at[t_index[0], 'Material']}")
            if st.button("Abbuchung Bestätigen"):
                # Wir bearbeiten direkt den Session State
                st.session_state.lager_daten.at[t_index[0], "Status"] = "Ausgang"
                st.session_state.lager_daten.at[t_index[0], "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                
                if save_to_github(st.session_state.lager_daten):
                    st.rerun() # Neustart verhindert die "ID nicht gefunden" Meldung
        else:
            # Diese Meldung kommt nur, wenn wirklich nichts gefunden wurde
            st.error("ID nicht im Bestand.")

elif menu == "📊 Bestand":
    st.header("Aktueller Ist-Stand")
    # Hier zeigen wir nur die aktiven Bestände
    df_ist = st.session_state.lager_daten[st.session_state.lager_daten["Status"] == "Eingang"]
    st.dataframe(df_ist, use_container_width=True)
