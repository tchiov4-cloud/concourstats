import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
import time

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="ConcourStats",
    page_icon="🎓",
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stTitle, .stSubheader {
        text-align: center;
    }
    .stMetric {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    [data-testid="stMetricValue"] {
        color: #007bff !important;
    }
    [data-testid="stMetricLabel"] {
        color: #333333 !important;
    }
    .stButton>button[kind="primary"] {
        background-color: #007bff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONNEXION TiDB ---
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["tidb"]["host"],
        user=st.secrets["tidb"]["user"],
        password=st.secrets["tidb"]["password"],
        database=st.secrets["tidb"]["database"],
        port=int(st.secrets["tidb"]["port"])
    )

# --- STRUCTURE CENTRÉE ---
side_margin_left, central_column, side_margin_right = st.columns([1, 4, 1])

with central_column:
    # --- HEADER SIMPLE (SANS BOUTON QUITTER) ---
    st.title("🎓 ConcourStats")
    st.markdown("<p style='text-align: center;'>Analyse descriptive des performances des prépas</p>", unsafe_allow_html=True)

    # --- TEXTE ANIMÉ ---
    message = (
        "Bienvenue sur ConcourStats, votre plateforme d'aide à la décision. "
        "Nous collectons les expériences réelles des candidats aux concours "
        "pour transformer des données brutes en statistiques exploitables."
    )
    
    placeholder = st.empty()
    animated_text = ""
    for char in message:
        animated_text += char
        placeholder.markdown(
            f"<div style='text-align: center; max-width: 650px; margin: 0 auto 20px auto;'>"
            f"<p style='font-style: italic; color: #555;'>{animated_text}▌</p></div>", unsafe_allow_html=True)
        time.sleep(0.01)
    
    placeholder.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><p style='font-style: italic;'>{message}</p></div>", unsafe_allow_html=True)

    st.markdown("---")

    tab1, tab2 = st.tabs(["📝 Formulaire de Collecte", "📊 Dashboard Statistique"])

    # --- ONGLET 1 : COLLECTE ---
    with tab1:
        st.subheader("Enregistrez votre expérience")
        with st.form("modern_form", clear_on_submit=True):
            nom = st.text_input("Nom complet")
            groupe = st.selectbox("Votre groupe", ["Alpha", "Bravo", "Elite", "Autre"])
            loc = st.text_input("📍 Localisation")
            prix = st.number_input("💰 Coût (FCFA)", min_value=0, step=5000)
            res = st.select_slider("Résultat", options=["Échoué", "Admis"])
            fil = st.text_input("🎓 Filière (Si admis)")
            submit = st.form_submit_button("🚀 Envoyer", type="primary")
            
            if submit:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    sql = "INSERT INTO collect_concours (nom_etudiant, nom_groupe, localisation, cout_formation, resultat, filiere_admission) VALUES (%s, %s, %s, %s, %s, %s)"
                    val = (nom, groupe, loc, prix, res, fil if res == "Admis" else "N/A")
                    cursor.execute(sql, val)
                    conn.commit()
                    st.success("Données enregistrées !")
                    cursor.close()
                    conn.close()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # --- ONGLET 2 : ANALYSE ---
    with tab2:
        try:
            conn = get_connection()
            df = pd.read_sql("SELECT * FROM collect_concours", conn)
            conn.close()

            if not df.empty:
                # KPI
                c1, c2, c3 = st.columns(3)
                admis_df = df[df['resultat'] == 'Admis']
                with c1: st.metric("Participants", len(df))
                with c2: st.metric("Admis", len(admis_df))
                with c3: st.metric("Succès", f"{(len(admis_df)/len(df)*100):.1f}%")

                st.write("###") 

                # GRAPHIQUES
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown("<h4 style='text-align: center;'>🏆 Top Performance</h4>", unsafe_allow_html=True)
                    stats = df.groupby('nom_groupe').agg(
                        total=('resultat', 'count'),
                        admis=('resultat', lambda x: (x == 'Admis').sum())
                    ).reset_index()
                    stats['Taux %'] = (stats['admis'] / stats['total']) * 100
                    st.plotly_chart(px.bar(stats, x='nom_groupe', y='Taux %', color='Taux %', template='plotly_white'), use_container_width=True)

                with g2:
                    st.markdown("<h4 style='text-align: center;'>🎯 Spécialisation</h4>", unsafe_allow_html=True)
                    choix = st.selectbox("Filtrer par centre :", df['nom_groupe'].unique())
                    df_pie = admis_df[admis_df['nom_groupe'] == choix]
                    if not df_pie.empty:
                        st.plotly_chart(px.pie(df_pie, names='filiere_admission', hole=0.5, template='plotly_white'), use_container_width=True)
                    else: st.write("Aucun admis.")

                # --- LISTE DES PARTICIPANTS ---
                st.markdown("---")
                with st.expander("📋 Voir la liste complète des participants"):
                    display_df = df[['nom_etudiant', 'nom_groupe', 'localisation', 'resultat', 'filiere_admission']]
                    st.dataframe(display_df, use_container_width=True)
                    
                    csv = display_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Télécharger la liste (CSV)",
                        data=csv,
                        file_name='participants_concourstats.csv',
                        mime='text/csv',
                    )

                # --- RECOMMANDATION ---
                st.markdown("---")
                st.markdown("<h3 style='text-align: center;'>💡 Recommandation Stratégique</h3>", unsafe_allow_html=True)
                
                if not stats.empty and len(admis_df) > 0:
                    best_row = stats.loc[stats['Taux %'].idxmax()]
                    st.success(f"**Meilleur Centre : {best_row['nom_groupe']}**")
                    st.info(f"Le centre **{best_row['nom_groupe']}** domine avec **{best_row['Taux %']:.1f}%** de réussite.")
                else:
                    st.info("Données insuffisantes pour une recommandation.")

            else: st.warning("Base de données vide.")
        except Exception as e: st.error(f"Erreur : {e}")
