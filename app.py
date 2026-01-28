import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
from PIL import Image
from github import Github

st.set_page_config(page_title="Lager-System", page_icon="📦")

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
        excel_data = output.getvalue()
        contents = repo.get_contents(GITHUB_FILENAME)
        repo.update_file(path=GITHUB_FILENAME, message="Lager-Update", content=excel_data, sha=contents.sha)
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")
        return False

@st.cache_data(ttl=60)
def load_data():
    try:
        return pd.read_excel(GITHUB_FILENAME)
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

# Initialisierung
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION ---
st.title("📦 Lager-System Prototyp")
menu = st.sidebar.radio("Menü", ["Bestand & Scanner", "Wareneingang", "QR-Code erzeugen"])

# --- SEITE 1: BESTAND ---
if menu == "Bestand & Scanner":
    df = st.session_state.lager_daten
    lager_aktuell = df[df["Status"] == "Eingang"]
    st.subheader("Aktueller Lagerbestand")
    st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)
    
    st.divider()
    scan_input = st.text_input("ID einscannen zum VERBRAUCHEN:").strip()
    if scan_input:
        idx_list = df.index[df["QR_ID"].astype(str) == scan_input].tolist()
        if idx_list:
            idx = idx_list[0]
            if df.at[idx, "Status"] == "Eingang":
                st.success(f"Gefunden: {df.at[idx, 'Material']}")
                if st.button("Verbrauch bestätigen"):
                    df.at[idx, "Status"] = "Verbraucht"
                    df.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                    if save_to_github(df):
                        st.success("Gespeichert!")
                        st.rerun()
            else:
                st.warning("Bereits verbraucht.")
        else:
            st.error("Unbekannte ID.")

# --- SEITE 2: WARENEINGANG ---
elif menu == "Wareneingang":
    st.subheader("Neues Material aufnehmen")
    with st.form("in_form"):
        f_id = st.text_input("QR-ID (z.B. ID-005)")
        f_name = st.text_input("Name")
        f_lief = st.text_input("Lieferant")
        f_preis = st.number_input("Preis", min_value=0.0)
        if st.form_submit_button("Speichern"):
            df = st.session_state.lager_daten
            neue_zeile = {"QR_ID": str(f_id), "Material": str(f_name), "Lieferant": str(f_lief), "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"), "Datum_Ausgang": "", "Preis": float(f_preis)}
            df = pd.concat([df, pd.DataFrame([neue_zeile])], ignore_index=True)
            if save_to_github(df):
                st.session_state.lager_daten = df
                st.success("Dauerhaft gespeichert!")

# --- SEITE 3: QR-GENERATOR ---
else:
    st.subheader("QR-Code für Etikett erstellen")
    st.write("Gib die ID ein, für die du ein Etikett drucken möchtest.")
    
    qr_id_input = st.text_input("ID eingeben (z.B. ID-001)")
    
    if qr_id_input:
        # QR-Code Logik
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_id_input)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Bild für Streamlit vorbereiten
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.image(byte_im, caption=f"QR-Code für ID: {qr_id_input}", width=200)
        
        st.download_button(
            label="💾 QR-Code Bild herunterladen",
            data=byte_im,
            file_name=f"QR_{qr_id_input}.png",
            mime="image/png"
        )
        st.info("Tipp: Du kannst dieses Bild einfach ausdrucken und auf das Gebinde kleben.")
