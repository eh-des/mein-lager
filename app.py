import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from github import Github

st.set_page_config(page_title="Lager-Diagnose", page_icon="📦", layout="wide")

GITHUB_REPO_PATH = "eh-des/mein-lager" 
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- SPEICHER-FUNKTION ---
def save_to_github(df):
    try:
        if "GITHUB_TOKEN" not in st.secrets:
            st.error("❌ Schlüssel fehlt: 'GITHUB_TOKEN' nicht gefunden!")
            return False
            
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        
        contents = repo.get_contents(GITHUB_FILENAME)
        repo.update_file(
            path=GITHUB_FILENAME,
            message=f"Lager-Update {datetime.now().strftime('%H:%M:%S')}",
            content=excel_data,
            sha=contents.sha
        )
        return True
    except Exception as e:
        st.error(f"❌ GitHub-Fehler: {e}")
        return False

def load_data():
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH)
        contents = repo.get_contents(GITHUB_FILENAME)
        return pd.read_excel(io.BytesIO(contents.decoded_content))
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

# --- SESSION STATE ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- SIDEBAR & EXPORT ---
st.sidebar.title("📦 Lager-Profi")
if st.sidebar.button("🔄 Daten neu laden"):
    st.session_state.lager_daten = load_data()
    st.rerun()

# 1) WICHTIG: Hier bereiten wir ZWEI Versionen der Daten vor
df_all = st.session_state.lager_daten  # Die komplette Historie für Excel
df_ist = df_all[df_all["Status"] == "Eingang"]  # Nur der Ist-Stand für die App

# 2) FEHLERBEHEBUNG EXPORT: Wir exportieren df_all (inkl. Ausgänge/Verbraucht)
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    df_all.to_excel(writer, index=False)
st.sidebar.download_button("📥 Komplettes Logbuch (Excel)", buf.getvalue(), f"Lager_Historie_{datetime.now().strftime('%d-%m')}.xlsx")

st.sidebar.divider()
menu = st.sidebar.radio("Menü:", ["📥 Annahme", "📤 Ausgang", "📊 Bestand"])

# --- SCANNER ---
def scan():
    img = st.camera_input("Kamera")
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
            
            # --- FEHLERBEHEBUNG DUPLIKATE ---
            # Wir prüfen, ob diese ID bereits mit Status "Eingang" im System ist
            bereits_da = not df_all[(df_all["QR_ID"] == s_id) & (df_all["Status"] == "Eingang")].empty
            
            if bereits_da:
                st.error(f"❌ Fehler: Der Code '{s_id}' ({s_mat}) ist bereits im Bestand!")
            else:
                st.success(f"Bereit zum Speichern: {s_mat}")
                if st.button("Speichern"):
                    nz = {
                        "QR_ID": s_id, 
                        "Material": s_mat, 
                        "Lieferant": p[2] if len(p)>2 else "", 
                        "Status": "Eingang", 
                        "Datum_Eingang": datetime.now().strftime("%d.%m.%Y %H:%M:%S"), 
                        "Datum_Ausgang": "", 
                        "Preis": float(p[3]) if len(p)>3 else 0.0
                    }
                    st.session_state.lager_daten = pd.concat([st.session_state.lager_daten, pd.DataFrame([nz])], ignore_index=True)
                    if save_to_github(st.session_state.lager_daten):
                        st.success("Erfolgreich aufgenommen!")
                        st.balloons()
                        st.rerun()
        else:
            st.error("QR-Format falsch!")

elif menu == "📤 Ausgang":
    st.header("Warenausgang")
    sid = scan()
    if sid:
        clean_id = sid.split(";")[0].strip()
        df = st.session_state.lager_daten
        # Wir suchen nur Teile, die aktuell im "Eingang" sind
        t = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")]
        
        if not t.empty:
            st.warning(f"Material gefunden: {df.at[t.index[0], 'Material']}")
            if st.button("Abbuchung Bestätigen"):
                # Hier ändern wir den Status auf "Ausgang" (oder Verbraucht)
                df.at[t.index[0], "Status"] = "Ausgang"
                df.at[t.index[0], "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                if save_to_github(df):
                    st.success("Abgebucht!")
                    st.rerun()
        else:
            st.error("ID nicht im Bestand oder bereits abgebucht.")

elif menu == "📊 Bestand":
    st.header("Aktueller Ist-Stand")
    # Hier zeigen wir NUR die Sachen an, die im Status "Eingang" sind
    st.dataframe(df_ist, use_container_width=True)
