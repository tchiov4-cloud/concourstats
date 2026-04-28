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
    .main { background-color: #f5f7f9; }
    .stTitle, .stSubheader { text-align: center; }
    .stMetric {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    [data-testid="stMetricValue"] { color: #007bff !important; }
    .stButton>button[kind="primary"] { background-color: #007bff; color: white; }
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
    st.title("🎓 ConcourStats")
    st.markdown("<p style='text-align: center;'>Analyse descriptive des performances des prépas</p>", unsafe_allow_html=True)

    # --- TEXTE ANIMÉ ---
    message = (
        "Bienvenue sur ConcourStats, votre plateforme d'aide à la décision. "
        "Nous analysons les taux de réussite et d'échec pour vous guider."
    )
    st.info(message)

    st.markdown("---")
    tab1, tab2 = st.tabs(["📝 Formulaire de Collecte", "📊 Dashboard Statistique"])

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

    with tab2:
        try:
            conn = get_connection()
            df = pd.read_sql("SELECT * FROM collect_concours", conn)
            conn.close()

            if not df.empty:
                # --- CALCULS DES TAUX ---
                total_part = len(df)
                admis_df = df[df['resultat'] == 'Admis']
                echoue_df = df[df['resultat'] == 'Échoué']
                
                taux_succes = (len(admis_df) / total_part) * 100
                taux_echec = (len(echoue_df) / total_part) * 100

                # KPI - AJOUT DU TAUX D'ECHEC
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("Participants", total_part)
                with c2: st.metric("Admis", len(admis_df))
                with c3: st.metric("Taux Succès", f"{taux_succes:.1f}%")
                with c4: st.metric("Taux Échec", f"{taux_echec:.1f}%", delta=f"-{taux_echec:.1f}%", delta_color="inverse")

                st.write("###") 

                # GRAPHIQUES
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown("<h4 style='text-align: center;'>📉 Comparatif par Centre</h4>", unsafe_allow_html=True)
                    # Préparation des données pour un graphique groupé
                    stats = df.groupby(['nom_groupe', 'resultat']).size().reset_index(name='Nombre')
                    fig_bar = px.bar(stats, x='nom_groupe', y='Nombre', color='resultat', 
                                     barmode='group', template='plotly_white',
                                     color_discrete_map={'Admis': '#28a745', 'Échoué': '#dc3545'})
                    st.plotly_chart(fig_bar, use_container_width=True)

                with g2:
                    st.markdown("<h4 style='text-align: center;'>🎯 Répartition Globale</h4>", unsafe_allow_html=True)
                    fig_pie = px.pie(df, names='resultat', hole=0.5, 
                                     color='resultat',
                                     color_discrete_map={'Admis': '#28a745', 'Échoué': '#dc3545'})
                    st.plotly_chart(fig_pie, use_container_width=True)

                # --- LISTE DES PARTICIPANTS ---
                st.markdown("---")
                with st.expander("📋 Voir la liste complète"):
                    st.dataframe(df[['nom_etudiant', 'nom_groupe', 'resultat', 'filiere_admission']], use_container_width=True)

                # --- RECOMMANDATION ---
                st.markdown("---")
                if taux_succes > 0:
                    # Trouver le groupe avec le plus haut taux de succès
                    group_stats = df.groupby('nom_groupe').agg(
                        total=('resultat', 'count'),
                        admis=('resultat', lambda x: (x == 'Admis').sum())
                    )
                    group_stats['taux'] = (group_stats['admis'] / group_stats['total']) * 100
                    best_group = group_stats['taux'].idxmax()
                    
                    st.success(f"💡 **Conseil :** Le centre **{best_group}** affiche la meilleure dynamique de réussite actuelle.")
                
            else: st.warning("Base de données vide.")
        except Exception as e: st.error(f"Erreur : {e}")
