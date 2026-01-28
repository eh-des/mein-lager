import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from github import Github

st.set_page_config(page_title="Lager-Master", page_icon="📦", layout="wide")

# --- KONFIGURATION ---
GITHUB_REPO = "mein-lager"
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- FUNKTIONEN ---
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
    except Exception as e:
        st.error(f"Speicherfehler: {e}")
        return False

def load_data():
    try:
        df = pd.read_excel(GITHUB_FILENAME)
        # Alle Spalten sicherheitshalber als flexible Objekte/Strings behandeln
        for col in ["QR_ID", "Status", "Material", "Datum_Ausgang", "Datum_Eingang"]:
            if col in df.columns:
                df[col] = df[col].astype(str).replace("nan", "")
        return df
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

# Session State initialisieren
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION ---
st.sidebar.title("Lager-Steuerung")
menu = st.sidebar.radio("Aktion wählen:", ["📥 Warenannahme", "📤 Warenausgang", "📊 Bestandsliste", "🖨 QR-Druck"])

# --- SCANNER LOGIK ---
def qr_scanner_logic(label):
    img_file = st.camera_input(label)
    if img_file:
        file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        opencv_image = cv2.imdecode(file_bytes, 1)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(opencv_image)
        return data
    return None

# --- SEITE: WARENANNAHME ---
if menu == "📥 Warenannahme":
    st.header("Ware einscannen & einlagern")
    scanned_data = qr_scanner_logic("Kamera für ANNAHME")
    
    if scanned_data:
        parts = scanned_data.split(";")
        if len(parts) >= 2:
            s_id, s_mat = parts[0], parts[1]
            s_lief = parts[2] if len(parts) > 2 else "Unbekannt"
            s_preis = parts[3] if len(parts) > 3 else 0.0
            
            st.success(f"Gelesen: {s_mat} (ID: {s_id})")
            
            if st.button("Jetzt EINLAGERN"):
                df = st.session_state.lager_daten
                # Wir prüfen nur, ob DIESE ID aktuell schon als "Eingang" existiert
                if ((df["QR_ID"] == s_id) & (df["Status"] == "Eingang")).any():
                    st.error("Dieses Gebinde liegt bereits im Lager!")
                else:
                    neue_zeile = {
                        "QR_ID": str(s_id), "Material": str(s_mat), "Lieferant": str(s_lief),
                        "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"),
                        "Datum_Ausgang": "", "Preis": float(s_preis)
                    }
                    df = pd.concat([df, pd.DataFrame([neue_zeile])], ignore_index=True)
                    if save_to_github(df):
                        st.session_state.lager_daten = df
                        st.success("Erfolgreich eingebucht!")
                        st.balloons()
        else:
            st.error("Format ungültig. Erwarte: ID;Name;Lieferant;Preis")

# --- SEITE: WARENAUSGANG ---
elif menu == "📤 Warenausgang":
    st.header("Ware verbrauchen")
    scanned_full = qr_scanner_logic("Kamera für AUSGANG")
    
    if scanned_full:
        clean_id = str(scanned_full.split(";")[0])
        df = st.session_state.lager_daten
        
        # WICHTIG: Wir suchen nur nach Zeilen mit dieser ID, die noch auf "Eingang" stehen
        treffer = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")]
        
        if not treffer.empty:
            idx = treffer.index[0]
            st.warning(f"Material gefunden: **{df.at[idx, 'Material']}**")
            if st.button("Verbrauch bestätigen"):
                df.at[idx, "Status"] = "Verbraucht"
                df.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                if save_to_github(df):
                    st.session_state.lager_daten = df
                    st.success("Ware wurde ausgebucht!")
                    st.rerun()
        else:
            # Checken ob es die ID überhaupt gibt
            if (df["QR_ID"] == clean_id).any():
                st.error("Dieses Gebinde wurde bereits früher verbraucht!")
            else:
                st.error("ID völlig unbekannt im System.")

# --- SEITE: BESTANDSLISTE ---
elif menu == "📊 Bestandsliste":
    st.header("Aktueller Ist-Bestand")
    df = st.session_state.lager_daten
    lager_aktuell = df[df["Status"] == "Eingang"]
    st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis", "Datum_Eingang"]], use_container_width=True)

# --- SEITE: QR-DRUCK ---
else:
    st.header("QR-Code für Lieferanten-Simulation")
    c1, c2 = st.columns(2)
    with c1:
        t_id = st.text_input("ID")
        t_mat = st.text_input("Material Name")
    with c2:
        t_lief = st.text_input("Lieferant")
        t_preis = st.number_input("Preis", min_value=0.0)
    
    if t_id and t_mat:
        full_code = f"{t_id};{t_mat};{t_lief};{t_preis}"
        qr_img = qrcode.make(full_code)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption=f"QR-Inhalt: {full_code}", width=250)
        st.download_button("QR herunterladen", buf.getvalue(), f"QR_{t_id}.png")
