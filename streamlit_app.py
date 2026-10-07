import streamlit as st
import pandas as pd
import datetime
import os
import json

# Seitensetup - Für Mobilgeräte optimiert
st.set_page_config(page_title="Arbeitszeiterfassung Schwerlast", page_icon="🚛", layout="wide")

# Dateien für die lokale Speicherung
DB_FILE = "arbeitszeiten_db.csv"
SETTINGS_FILE = "settings.json"

# Erwartete Spalten in der CSV
DEFAULT_COLUMNS = [
    "Datum", "Kunde", "Einsatzort", "Start_Standort", "Rahmen_Start", "Rahmen_Ende", 
    "Spesen_Typ", "Spesen_Betrag", "Tätigkeit", "Von", "Bis", "Equipment_Typ", 
    "Equipment_Details", "Getankt", "Miete_Status", "Miete_KM_Std_Start", "Miete_KM_Std_Ende", 
    "Tank_KM_Std_Stand", "Liter_Getankt", "Kommentar"
]

# Stammdaten laden / initialisieren
def load_settings():
    default_settings = {
        "firma_name": "Muster Logistik GmbH",
        "firma_strasse": "Firmenstraße 10",
        "firma_plz": "12345",
        "firma_ort": "Musterstadt",
        "heimat_strasse": "Musterstraße 1",
        "heimat_plz": "12345",
        "heimat_ort": "Musterstadt",
        "spesen_an_abreise": 16.0,
        "spesen_zwischen": 16.0,
        "spesen_voll": 32.0,
        "fuhrpark": ["LKW - HB-X 1234", "SPMT - Modul 01", "Teleskopstapler - TS-02", "Hubarbeitsbühne - HAB-05"],
        "kunden": ["Muster AG", "Schwerlast Logistik GmbH", "Windpark Nord"],
        "partner_register": [
            {
                "firma": "HKL Baumaschinen",
                "standort": "Unna",
                "strasse": "Gewerbestraße 5",
                "plz_ort": "59425 Unna",
                "telefon": "+49 2303 123456",
                "ansprechpartner": "Dispo / Service"
            },
            {
                "firma": "Mateco GmbH",
                "standort": "Dortmund",
                "strasse": "Mietparkallee 12",
                "plz_ort": "44135 Dortmund",
                "telefon": "+49 231 987654",
                "ansprechpartner": "Herr Becker"
            }
        ],
        "taetigkeiten": [
            "An- / Abreise (Fahrzeit)",
            "Schwerlasttransport / Fahrt",
            "Montage / Schwerassemblierung",
            "SPMT-Bedienung / Einsatz",
            "Wartezeit / Standzeit",
            "Be- / Entladung / Verladen",
            "Pause / Ruhezeit"
        ],
        "meldungen": []
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in default_settings.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            return default_settings
    return default_settings

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

settings = load_settings()

# Hilfsfunktionen für Adress-Strings
def get_firma_full_address():
    name = settings.get("firma_name", "")
    str_nr = settings.get("firma_strasse", "")
    plz = settings.get("firma_plz", "")
    ort = settings.get("firma_ort", "")
    parts = [p for p in [name, str_nr, f"{plz} {ort}".strip()] if p]
    return ", ".join(parts) if parts else "Firmenadresse (Nicht hinterlegt)"

def get_heimat_full_address():
    str_nr = settings.get("heimat_strasse", "")
    plz = settings.get("heimat_plz", "")
    ort = settings.get("heimat_ort", "")
    parts = [p for p in [str_nr, f"{plz} {ort}".strip()] if p]
    return ", ".join(parts) if parts else "Heimatadresse (Nicht hinterlegt)"

# Einträge laden / initialisieren (Inkl. automatischer Schema-Anpassung)
def load_records():
    if os.path.exists(DB_FILE):
        try:
            df = pd.read_csv(DB_FILE)
            for col in DEFAULT_COLUMNS:
                if col not in df.columns:
                    df[col] = "-"
            return df[DEFAULT_COLUMNS]
        except Exception:
            pass
    return pd.DataFrame(columns=DEFAULT_COLUMNS)

def save_record(new_row_dict):
    df = load_records()
    new_df = pd.DataFrame([new_row_dict])
    df = pd.concat([df, new_df], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def delete_record(index_to_delete):
    df = load_records()
    if index_to_delete in df.index:
        df = df.drop(index_to_delete).reset_index(drop=True)
        df.to_csv(DB_FILE, index=False)

# Header & Rollen-Auswahl in der Sidebar
st.sidebar.title("👤 Benutzer-Profil")
user_role = st.sidebar.selectbox("Aktuelle Rolle:", [
    "Fahrer / Monteur (Nur Erfassung)",
    "Vorarbeiter / Richtmeister (Erweiterte Rechte)",
    "Administrator (Vollzugriff)"
])

is_admin = "Administrator" in user_role
is_vorarbeiter = "Vorarbeiter" in user_role or is_admin

if is_admin:
    st.sidebar.success("🔑 Admin-Rechte aktiv: Vollzugriff & Löschrechte.")
elif is_vorarbeiter:
    st.sidebar.info("🛠️ Vorarbeiter-Rechte aktiv: Erweiterte Pflege & Löschrechte.")
else:
    st.sidebar.warning("🔒 Lesezugriff: Keine Lösch- oder Bearbeitungsrechte.")

# App Navigation
st.title("🚛 Arbeitszeiterfassung & Spesen")
st.caption("Prototyp für Schwerlast, Montage & SPMT-Einsätze")

tab1, tab2, tab3 = st.tabs(["📝 Tageserfassung", "📊 Übersicht & Export", "⚙️ Stammdaten & Partner-Register"])

# TAB 1: Tageserfassung
with tab1:
    with st.expander("📍 1. Datum, Kunde & Einsatzort", expanded=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            selected_date = st.date_input("Datum wählen", datetime.date.today())
            kunden_liste = settings.get("kunden", ["Standardkunde"])
            selected_kunde = st.selectbox("Kunde / Auftraggeber", kunden_liste)
        with col_c2:
            einsatzort = st.text_input("Einsatzort / Baustelle", "Z.B. Windpark Blexen")
            start_standort = st.selectbox("Tages-Startpunkt (für Auswertung)", [
                f"Firmenadresse: {get_firma_full_address()}",
                f"Heimatadresse: {get_heimat_full_address()}",
                "Direkt auf Baustelle / Hotel"
            ])

        st.markdown("---")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            rahmen_start = st.time_input("Gesamter Arbeitsbeginn (Rahmen)", datetime.time(7, 0))
        with col_r2:
            rahmen_ende = st.time_input("Gesamtes Arbeitsende (Rahmen)", datetime.time(18, 0))

    with st.expander("💶 2. Spesen & Abwesenheit", expanded=True):
        col_sp1, col_sp2 = st.columns([2, 1])
        with col_sp1:
            spesen_typ = st.selectbox("Spesen-Kategorie für heute:", [
                "Keine Spesen (Heimschläfer)",
                "Anreise von Heimatadresse (100% Satz)",
                "Abreise zur Heimatadresse (100% Satz)",
                "Voller Einsatztag (100% Satz)",
                "An-/Abreise (Doppelter Satz 200%)",
                "Voller Einsatztag (Doppelter Satz 200%)"
            ])
        with col_sp2:
            base_voll = float(settings.get("spesen_voll", 32.0))
            base_an = float(settings.get("spesen_an_abreise", 16.0))
            if "Keine" in spesen_typ:
                calc_spesen = 0.0
            elif "Anreise" in spesen_typ or "Abreise" in spesen_typ:
                calc_spesen = base_an * (2.0 if "200%" in spesen_typ else 1.0)
            else:
                calc_spesen = base_voll * (2.0 if "200%" in spesen_typ else 1.0)
                
            st.metric("Spesen Anspruch", f"{calc_spesen:.2f} €")

    with st.expander("⏱️ 3. Tätigkeit & Equipment erfassen", expanded=True):
        col_t1, col_t2, col_t3 = st.columns([2, 1, 1])
        with col_t1:
            taetigkeits_liste = settings.get("taetigkeiten", ["Montage", "Fahrt"])
            taetigkeit = st.selectbox("Tätigkeit", taetigkeits_liste)
        with col_t2:
            t_von = st.time_input("Von", datetime.time(7, 0), key="t_von")
        with col_t3:
            t_bis = st.time_input("Bis", datetime.time(8, 30), key="t_bis")
            
        st.markdown("**Eingesetztes Equipment / Fahrzeuge:**")
        eq_cols = st.columns(4)
        eq_lkw = eq_cols[0].checkbox("🚛 LKW")
        eq_spmt = eq_cols[1].checkbox("🚜 SPMT")
        eq_stapler = eq_cols[2].checkbox("🏗️ Stapler")
        eq_hab = eq_cols[3].checkbox("🛠️ Hubarbeitsbühne")
        
        eq_details_list = []
        fuhrpark_liste = settings.get("fuhrpark", [])
        
        if eq_lkw:
            sel_lkw = st.selectbox("LKW Kennzeichen", fuhrpark_liste if fuhrpark_liste else ["LKW-1"], key="lkw_sel")
            eq_details_list.append(f"LKW: {sel_lkw}")
        if eq_spmt:
            sel_spmt = st.text_input("SPMT Modul / Achsen", "SPMT 6-Achsen", key="spmt_sel")
            eq_details_list.append(f"SPMT: {sel_spmt}")
        if eq_stapler:
            sel_stapler = st.selectbox("Teleskopstapler", fuhrpark_liste if fuhrpark_liste else ["Stapler-1"], key="stapler_sel")
            eq_details_list.append(f"Stapler: {sel_stapler}")
        if eq_hab:
            hab_type = st.radio("Herkunft HAB:", ["Eigenes Gerät", "Mietgerät / Extern"], horizontal=True)
            if hab_type == "Eigenes Gerät":
                hab_val = st.selectbox("HAB Gerät", fuhrpark_liste if fuhrpark_liste else ["HAB-1"], key="hab_sel")
                eq_details_list.append(f"HAB (Eigen): {hab_val}")
            else:
                partner_reg = settings.get("partner_register", [])
                partner_options = [f"{p['firma']} ({p['standort']})" for p in partner_reg] if partner_reg else ["Kein Partner hinterlegt"]
                sel_partner_idx = st.selectbox("Vermieter / Mietstation auswählen", range(len(partner_options)), format_func=lambda x: partner_options[x], key="partner_sel")
                
                if partner_reg:
                    p_info = partner_reg[sel_partner_idx]
                    st.info(f"📞 **Kontaktdaten Mietstation:** {p_info['firma']} {p_info['standort']} | Tel: **{p_info['telefon']}** ({p_info['ansprechpartner']}) | {p_info['strasse']}, {p_info['plz_ort']}")
                    eq_details_list.append(f"HAB (Miete): {p_info['firma']} {p_info['standort']}")

        st.markdown("---")
        st.markdown("**Sonderprüfungen (Tanken / Mietgeräte):**")
        col_s1, col_s2 = st.columns(2)
        is_tanked = col_s1.checkbox("⛽ Getankt")
        is_miete = col_s2.checkbox("📋 Miet-Übergabe / Rückgabe")
        
        tank_km_std_val = ""
        liter_val = ""
        miete_status = "Nein"
        miete_km_start = ""
        miete_km_ende = ""
        
        if is_tanked or is_miete:
            st.warning("⚠️ Pflichtfelder für Zählerstände / Tankmenge aktiv:")
            
            if is_miete:
                col_m1, col_m2 = st.columns(2)
                miete_status = col_m1.selectbox("Miet-Vorgang *", ["Miet-Übernahme (Start / Eingang)", "Miet-Rückgabe (Ende / Abgabe)"])
                if "Übernahme" in miete_status:
                    miete_km_start = col_m2.text_input("Km / Std bei EINGANG (Übernahme) *", placeholder="Z. B. 124,5 Std")
                else:
                    miete_km_ende = col_m2.text_input("Km / Std bei ABGABE (Rückgabe) *", placeholder="Z. B. 138,0 Std")
            
            if is_tanked:
                col_t1, col_t2 = st.columns(2)
                tank_km_std_val = col_t1.text_input("KM- / Std-Stand beim Tanken *", placeholder="Z. B. 142.500 km")
                liter_val = col_t2.text_input("Liter Getankt *", placeholder="Z. B. 350 L")

        kommentar = st.text_input("Kommentar / Bemerkung", "Z.B. Entladung Bauteil A")

        if st.button("💾 Tages-Eintrag speichern", type="primary", use_container_width=True):
            if is_tanked and (not tank_km_std_val or not liter_val):
                st.error("Bitte Zählerstand und Liter beim Tanken eintragen!")
            elif is_miete and ("Übernahme" in miete_status and not miete_km_start):
                st.error("Bitte Zählerstand bei Miet-Übernahme eintragen!")
            elif is_miete and ("Rückgabe" in miete_status and not miete_km_ende):
                st.error("Bitte Zählerstand bei Miet-Rückgabe eintragen!")
            else:
                eq_type_str = ", ".join([k for k, v in [("LKW", eq_lkw), ("SPMT", eq_spmt), ("Stapler", eq_stapler), ("HAB", eq_hab)] if v])
                row = {
                    "Datum": selected_date.strftime("%Y-%m-%d"),
                    "Kunde": selected_kunde,
                    "Einsatzort": einsatzort,
                    "Start_Standort": start_standort.split(":")[0],
                    "Rahmen_Start": rahmen_start.strftime("%H:%M"),
                    "Rahmen_Ende": rahmen_ende.strftime("%H:%M"),
                    "Spesen_Typ": spesen_typ,
                    "Spesen_Betrag": calc_spesen,
                    "Tätigkeit": taetigkeit,
                    "Von": t_von.strftime("%H:%M"),
                    "Bis": t_bis.strftime("%H:%M"),
                    "Equipment_Typ": eq_type_str if eq_type_str else "Keines",
                    "Equipment_Details": " | ".join(eq_details_list) if eq_details_list else "-",
                    "Getankt": "Ja" if is_tanked else "Nein",
                    "Miete_Status": miete_status,
                    "Miete_KM_Std_Start": miete_km_start if miete_km_start else "-",
                    "Miete_KM_Std_Ende": miete_km_ende if miete_km_ende else "-",
                    "Tank_KM_Std_Stand": tank_km_std_val if tank_km_std_val else "-",
                    "Liter_Getankt": liter_val if liter_val else "-",
                    "Kommentar": kommentar
                }
                save_record(row)
                st.success("✅ Eintrag erfolgreich in der Datenbank gespeichert!")

# TAB 2: Übersicht & Löschverwaltung
with tab2:
    st.subheader("📊 Gespeicherte Tageseinträge (Leistungsnachweis)")
    df_data = load_records()
    if not df_data.empty:
        st.dataframe(df_data, use_container_width=True)
        
        col_m1, col_m2 = st.columns(2)
        total_spesen = df_data["Spesen_Betrag"].astype(float).sum()
        col_m1.metric("Gesamtsumme Spesen", f"{total_spesen:.2f} €")
        col_m2.metric("Anzahl Einträge", len(df_data))
        
        csv_bytes = df_data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Alle Daten als Excel/CSV herunterladen", data=csv_bytes, file_name="arbeitszeiten_export.csv", mime="text/csv", use_container_width=True)
        
        # Löschbereich nur für Vorarbeiter & Admins
        st.markdown("---")
        if is_vorarbeiter:
            with st.expander("🗑️ Leistungsnachweis-Eintrag löschen (Nur Vorgesetzte)", expanded=False):
                st.warning("Achtung: Gelöschte Zeilen können nicht wiederhergestellt werden!")
                
                options_to_delete = [
                    f"Zeile {idx}: Datum {row.get('Datum', '-')} | Kunde: {row.get('Kunde', '-')} | Tätigkeit: {row.get('Tätigkeit', '-')}" 
                    for idx, row in df_data.iterrows()
                ]
                sel_del_idx = st.selectbox("Eintrag zum Löschen auswählen:", range(len(options_to_delete)), format_func=lambda x: options_to_delete[x])
                
                if st.button("🗑️ Ausgewählten Eintrag unwiderruflich löschen", type="secondary"):
                    delete_record(sel_del_idx)
                    st.success("Eintrag erfolgreich gelöscht!")
                    st.rerun()
        else:
            st.info("🔒 **Löschen gesperrt:** Nur Vorarbeiter und Administratoren dürfen falsche Tageseinträge entfernen.")
            
    else:
        st.info("Noch keine Einträge erfasst.")

# TAB 3: Einstellungen & Partner-Register
with tab3:
    st.subheader("⚙️ Stammdaten, Partner & Meldungen")
    
    if not is_vorarbeiter:
        st.warning("🔒 **Schreibgeschützter Modus:** Nur Administratoren und Vorarbeiter dürfen Stammdaten verwalten oder löschen.")

    # 1. Meldungen & Feedback-Bereich
    with st.expander("📩 1. Fehler- & Korrekturmeldungen zu Stammdaten", expanded=True):
        meldungen_liste = settings.get("meldungen", [])
        
        with st.form("meldung_form", clear_on_submit=True):
            st.markdown("**🚨 Neue Korrektur / Änderung melden:**")
            col_m1, col_m2 = st.columns(2)
            absender_name = col_m1.text_input("Dein Name / Name des Mitarbeiters", "Mitarbeiter X")
            betrifft_kategorie = col_m2.selectbox("Betrifft Bereich", ["Mietstation / Partner", "Kunden / Baustelle", "Fuhrpark", "Sonstiges"])
            meldung_text = st.text_area("Beschreibung der Änderung / Falsche Daten", placeholder="Z. B. Telefonnummer von HKL Unna hat sich geändert auf 0171-1234567")
            
            submit_meldung = st.form_submit_button("📩 Meldung an Vorarbeiter / Admin senden", use_container_width=True)
            if submit_meldung:
                if meldung_text.strip():
                    neue_meldung = {
                        "id": len(meldungen_liste) + 1,
                        "datum": datetime.date.today().strftime("%Y-%m-%d"),
                        "von": absender_name,
                        "bereich": betrifft_kategorie,
                        "text": meldung_text.strip(),
                        "status": "🔴 Offen",
                        "erledigt_von": "-"
                    }
                    meldungen_liste.append(neue_meldung)
                    settings["meldungen"] = meldungen_liste
                    save_settings(settings)
                    st.success("✅ Meldung erfolgreich gesendet!")
                    st.rerun()
                else:
                    st.error("Bitte gib eine Beschreibung der Änderung ein!")

        st.markdown("---")
        st.markdown("**📋 Übersicht aller gemeldeten Stammdaten-Korrekturen:**")
        
        if meldungen_liste:
            for idx, m in enumerate(meldungen_liste):
                with st.container():
                    col_m1, col_m2, col_m3 = st.columns([3, 1, 1.5])
                    with col_m1:
                        st.markdown(f"**#{m['id']} [{m['datum']}] {m['bereich']}** - *gemeldet von {m['von']}*")
                        st.write(f"> {m['text']}")
                    with col_m2:
                        st.markdown(f"**Status:** {m['status']}")
                        if m['status'] == "🟢 Erledigt":
                            st.caption(f"Erledigt von: {m.get('erledigt_von', 'Admin')}")
                    with col_m3:
                        if is_vorarbeiter:
                            if m['status'] != "🟢 Erledigt":
                                if st.button("✅ Erledigt", key=f"btn_done_{idx}"):
                                    meldungen_liste[idx]["status"] = "🟢 Erledigt"
                                    meldungen_liste[idx]["erledigt_von"] = user_role.split("(")[0].strip()
                                    settings["meldungen"] = meldungen_liste
                                    save_settings(settings)
                                    st.rerun()
                            if st.button("🗑️ Löschen", key=f"btn_del_m_{idx}"):
                                meldungen_liste.pop(idx)
                                settings["meldungen"] = meldungen_liste
                                save_settings(settings)
                                st.success("Meldung gelöscht!")
                                st.rerun()
                st.divider()
        else:
            st.info("Aktuell liegen keine offenen Meldungen vor.")

    # 2. Firmenadresse (Nur Admin)
    with st.expander("🏢 2. Firmenadresse / Hauptstandort (Fix)", expanded=False):
        if is_admin:
            new_firma_name = st.text_input("Firmenname", settings.get("firma_name", "Muster Logistik GmbH"))
            col_fa1, col_fa2, col_fa3 = st.columns([2, 1, 1])
            with col_fa1:
                new_firma_strasse = st.text_input("Straße & Hausnummer (Firma)", settings.get("firma_strasse", "Firmenstraße 10"))
            with col_fa2:
                new_firma_plz = st.text_input("PLZ (Firma)", settings.get("firma_plz", "12345"))
            with col_fa3:
                new_firma_ort = st.text_input("Ort (Firma)", settings.get("firma_ort", "Musterstadt"))
        else:
            st.write(f"**{settings.get('firma_name')}**")
            st.write(f"{settings.get('firma_strasse')}, {settings.get('firma_plz')} {settings.get('firma_ort')}")

    # 3. Heimatadresse
    with st.expander("🏠 3. Heimatadresse / Wohnort (Personalisiert)", expanded=False):
        col_ha1, col_ha2, col_ha3 = st.columns([2, 1, 1])
        with col_ha1:
            new_heimat_strasse = st.text_input("Straße & Hausnummer (Heimat)", settings.get("heimat_strasse", "Musterstraße 1"), disabled=not is_vorarbeiter)
        with col_ha2:
            new_heimat_plz = st.text_input("PLZ (Heimat)", settings.get("heimat_plz", "12345"), disabled=not is_vorarbeiter)
        with col_ha3:
            new_heimat_ort = st.text_input("Ort (Heimat)", settings.get("heimat_ort", "Musterstadt"), disabled=not is_vorarbeiter)

    # 4. Spesensätze (Nur Admin)
    with st.expander("💶 4. Spesensätze & Pauschalen", expanded=False):
        col_s1, col_s2, col_s3 = st.columns(3)
        new_an = col_s1.number_input("Spesen An-/Abreisetag (€)", value=float(settings.get("spesen_an_abreise", 16.0)), disabled=not is_admin)
        new_zw = col_s2.number_input("Spesen Zwischenpauschale (€)", value=float(settings.get("spesen_zwischen", 16.0)), disabled=not is_admin)
        new_voll = col_s3.number_input("Spesen Voller Tag (€)", value=float(settings.get("spesen_voll", 32.0)), disabled=not is_admin)

    # 5. Zentrales Partner- & Mietstationen-Register
    with st.expander("🏭 5. Zentrales Partner- & Mietstationen-Register", expanded=True):
        st.markdown("Hier sind alle externen Vermieter und Partnerstandorte mit Kontaktdaten hinterlegt.")
        partner_reg = settings.get("partner_register", [])
        
        if partner_reg:
            df_partner = pd.DataFrame(partner_reg)
            st.dataframe(df_partner, use_container_width=True)
            
            if is_vorarbeiter:
                st.markdown("**🗑️ Mietstation / Partner löschen:**")
                partner_names = [f"{p['firma']} ({p['standort']})" for p in partner_reg]
                del_p_idx = st.selectbox("Wähle einen Partner zum Entfernen aus:", range(len(partner_names)), format_func=lambda x: partner_names[x], key="del_p_select")
                
                if st.button("🗑️ Partner aus Register löschen"):
                    removed = partner_reg.pop(del_p_idx)
                    settings["partner_register"] = partner_reg
                    save_settings(settings)
                    st.success(f"Eintrag '{removed['firma']} ({removed['standort']})' wurde gelöscht!")
                    st.rerun()
        else:
            st.info("Noch keine Mietstationen eingetragen.")
            
        if is_vorarbeiter:
            st.markdown("---")
            st.markdown("**➕ Neue Mietstation / Partner hinzufügen:**")
            col_p1, col_p2 = st.columns(2)
            add_firma = col_p1.text_input("Firma / Marke", "HKL Baumaschinen")
            add_standort = col_p2.text_input("Niederlassung / Standort", "Münster")
            col_p3, col_p4 = st.columns(2)
            add_strasse = col_p3.text_input("Straße & Hausnummer", "Industriestraße 12")
            add_plz_ort = col_p4.text_input("PLZ & Ort", "48153 Münster")
            col_p5, col_p6 = st.columns(2)
            add_telefon = col_p5.text_input("Telefon / Hotline", "+49 251 123456")
            add_ansprech = col_p6.text_input("Ansprechpartner / Abteilung", "Werkstatt / Service")
            
            if st.button("➕ Partner zum Register hinzufügen"):
                new_entry = {
                    "firma": add_firma,
                    "standort": add_standort,
                    "strasse": add_strasse,
                    "plz_ort": add_plz_ort,
                    "telefon": add_telefon,
                    "ansprechpartner": add_ansprech
                }
                partner_reg.append(new_entry)
                settings["partner_register"] = partner_reg
                save_settings(settings)
                st.success(f"✅ {add_firma} ({add_standort}) erfolgreich zum Register hinzugefügt!")
                st.rerun()

    # 6. Listen & Kategorien (Fuhrpark, Kunden, Tätigkeiten)
    with st.expander("🚛 6. Fuhrpark & Kundenlisten", expanded=False):
        fuhrpark_text = st.text_area("Fuhrpark (Pro Zeile ein Kennzeichen/Gerät)", "\n".join(settings.get("fuhrpark", [])), disabled=not is_vorarbeiter)
        kunden_text = st.text_area("Kunden / Auftraggeber (Pro Zeile ein Kunde)", "\n".join(settings.get("kunden", [])), disabled=not is_vorarbeiter)
        taetigkeiten_text = st.text_area("Auswählbare Tätigkeiten (Pro Zeile eine Tätigkeit)", "\n".join(settings.get("taetigkeiten", [])), disabled=not is_admin)

    if is_vorarbeiter:
        if st.button("💾 Alle Stammdaten speichern", type="primary", use_container_width=True):
            if is_admin:
                settings["firma_name"] = new_firma_name
                settings["firma_strasse"] = new_firma_strasse
                settings["firma_plz"] = new_firma_plz
                settings["firma_ort"] = new_firma_ort
                settings["spesen_an_abreise"] = new_an
                settings["spesen_zwischen"] = new_zw
                settings["spesen_voll"] = new_voll
                settings["taetigkeiten"] = [line.strip() for line in taetigkeiten_text.split("\n") if line.strip()]
            
            settings["heimat_strasse"] = new_heimat_strasse
            settings["heimat_plz"] = new_heimat_plz
            settings["heimat_ort"] = new_heimat_ort
            settings["fuhrpark"] = [line.strip() for line in fuhrpark_text.split("\n") if line.strip()]
            settings["kunden"] = [line.strip() for line in kunden_text.split("\n") if line.strip()]
            
            save_settings(settings)
            st.success("✅ Stammdaten erfolgreich aktualisiert!")

