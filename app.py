import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from github import Github

st.set_page_config(page_title="Lager-Master v3.5", page_icon="📦", layout="wide")

GITHUB_REPO = "mein-lager"
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- GITHUB FUNKTIONEN ---
def save_to_github(df):
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_user().get_repo(GITHUB_REPO)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        contents = repo.get_contents(GITHUB_FILENAME)
        repo.update_file(path=GITHUB_FILENAME, message=f"Update {datetime.now()}", content=output.getvalue(), sha=contents.sha)
        return True
    except:
        return False

def load_data():
    try:
        df = pd.read_excel(GITHUB_FILENAME)
        for col in ["QR_ID", "Status", "Material"]:
            if col in df.columns: 
                df[col] = df[col].astype(str).replace("nan", "")
        return df
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- SIDEBAR & EXPORT ---
st.sidebar.title("📦 Lager-Menü")
df_current = st.session_state.lager_daten
lager_bestand = df_current[df_current["Status"] == "Eingang"]

# Export-Vorbereitung
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    lager_bestand.to_excel(writer, index=False)
st.sidebar.download_button("📥 Inventur-Export (Excel)", buf.getvalue(), f"Bestand_{datetime.now().strftime('%d-%m')}.xlsx")

st.sidebar.divider()
menu = st.sidebar.radio("Aktion:", ["📥 Warenannahme", "📤 Warenausgang", "📊 Bestandsliste", "🖨 QR-Druck"])

# --- SCANNER FUNKTION MIT FEEDBACK ---
def scan_with_feedback():
    img = st.camera_input("Scanner (Bitte Code mittig & nah)")
    if img:
        try:
            # Bild konvertieren
            file_bytes = np.asarray(bytearray(img.read()), dtype=np.uint8)
            opencv_image = cv2.imdecode(file_bytes, 1)
            
            # Detektor
            detector = cv2.QRCodeDetector()
            data, points, _ = detector.detectAndDecode(opencv_image)
            
            if data:
                return data
            else:
                st.warning("⚠️ Bild aufgenommen, aber kein QR-Code gefunden. Bitte näher ran oder besser beleuchten.")
                return None
        except Exception as e:
            st.error(f"Fehler bei der Bildverarbeitung: {e}")
            return None
    return None

# --- WARENANNAHME ---
if menu == "📥 Warenannahme":
    st.header("Wareneingang buchen")
    data = scan_with_feedback()
    
    if data:
        p = data.split(";")
        if len(p) >= 2:
            s_id, s_mat = p[0].strip(), p[1].strip()
            st.success(f"✅ Code erkannt: **{s_mat}** (ID: {s_id})")
            
            if st.button("Jetzt fest einlagern"):
                df = st.session_state.lager_daten
                # Dubletten-Check
                if not df.empty and ((df["QR_ID"] == s_id) & (df["Status"] == "Eingang")).any():
                    st.error("❌ Diese ID liegt bereits im Lager!")
                else:
                    nz = {
                        "QR_ID": s_id, "Material": s_mat, 
                        "Lieferant": p[2] if len(p)>2 else "Unbekannt", 
                        "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"), 
                        "Datum_Ausgang": "", "Preis": float(p[3]) if len(p)>3 else 0.0
                    }
                    st.session_state.lager_daten = pd.concat([df, pd.DataFrame([nz])], ignore_index=True)
                    if save_to_github(st.session_state.lager_daten):
                        st.success(f"🔥 {s_mat} wurde dauerhaft gespeichert!")
                        st.balloons()
                        # Wir verzichten auf rerun, damit die Meldung stehen bleibt
        else:
            st.error(f"❌ Falsches Format! Gelesen wurde: '{data}'. Erwartet wird: ID;Name;Lieferant;Preis")

# --- WARENAUSGANG ---
elif menu == "📤 Warenausgang":
    st.header("Warenausgang buchen")
    data = scan_with_feedback()
    if data:
        clean_id = data.split(";")[0].strip()
        df = st.session_state.lager_daten
        t = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")]
        
        if not t.empty:
            st.warning(f"Gefunden: **{df.at[t.index[0], 'Material']}**")
            if st.button("Verbrauch bestätigen"):
                df.at[t.index[0], "Status"] = "Verbraucht"
                df.at[t.index[0], "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                if save_to_github(df):
                    st.success("Ausgebucht!")
                    st.rerun()
        else:
            st.error("ID nicht im Bestand (oder Code falsch).")

# --- LISTE ---
elif menu == "📊 Bestandsliste":
    st.header("Aktueller Bestand")
    st.dataframe(lager_bestand, use_container_width=True)

# --- DRUCK ---
else:
    st.header("QR-Drucker")
    id_in = st.text_input("ID")
    ma_in = st.text_input("Material")
    if id_in and ma_in:
        code = f"{id_in};{ma_in};Intern;0.0"
        buf = io.BytesIO()
        qrcode.make(code).save(buf, format="PNG")
        st.image(buf.getvalue(), width=200)
