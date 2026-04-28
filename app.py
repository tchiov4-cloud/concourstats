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
    .stTitle { text-align: center; color: #1E3A8A; }
    
    /* Style des cartes de métriques (Les carrés) */
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        padding: 20px !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        border: 1px solid #e0e0e0 !important;
        text-align: center !important;
    }
    
    /* Titre au niveau des carrés */
    [data-testid="stMetricLabel"] {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        color: #4B5563 !important;
        justify-content: center !important;
        margin-bottom: 10px !important;
    }

    /* Valeur numérique au centre */
    [data-testid="stMetricValue"] {
        color: #007bff !important;
        font-size: 2.2rem !important;
        font-weight: 800 !important;
    }
    
    .stButton>button[kind="primary"] { 
        background-color: #007bff; 
        color: white; 
        width: 100%; 
        border-radius: 8px;
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

# --- STRUCTURE ---
side_margin_left, central_column, side_margin_right = st.columns([1, 4, 1])

with central_column:
    st.title("🎓 ConcourStats")
    st.markdown("<p style='text-align: center; font-size: 1.2em; color: #666;'>Analyse descriptive des performances des prépas</p>", unsafe_allow_html=True)

    # --- TEXTE ANIMÉ ---
    message = (
        "Bienvenue sur ConcourStats, votre plateforme d'aide à la décision. "
        "Nous transformons vos expériences réelles en statistiques exploitables."
    )
    
    placeholder = st.empty()
    animated_text = ""
    for char in message:
        animated_text += char
        placeholder.markdown(f"<div style='text-align: center; font-style: italic; color: #555; margin-bottom: 20px;'>{animated_text}▌</div>", unsafe_allow_html=True)
        time.sleep(0.01)
    placeholder.markdown(f"<div style='text-align: center; font-style: italic; color: #555; margin-bottom: 20px;'>{message}</div>", unsafe_allow_html=True)

    st.markdown("---")
    tab1, tab2 = st.tabs(["📝 Formulaire de Collecte", "📊 Dashboard Statistique"])

    # --- ONGLET 1 : COLLECTE ---
    with tab1:
        st.subheader("Enregistrez votre expérience")
        with st.form("modern_form", clear_on_submit=True):
            nom = st.text_input("Nom complet").strip()
            groupe = st.selectbox("Votre centre de formation", ["Alpha", "Bravo", "Elite", "Autre"])
            loc = st.text_input("📍 Localisation")
            prix = st.number_input("💰 Coût (FCFA)", min_value=0, step=5000)
            res = st.select_slider("Résultat", options=["Échoué", "Admis"])
            fil = st.text_input("🎓 Filière (Si admis)")
            submit = st.form_submit_button("🚀 Envoyer les données", type="primary")
            
            if submit:
                if not nom:
                    st.warning("Veuillez entrer votre nom.")
                else:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        check_sql = "SELECT id FROM collect_concours WHERE nom_etudiant = %s AND nom_groupe = %s"
                        cursor.execute(check_sql, (nom, groupe))
                        if cursor.fetchone():
                            st.error(f"L'étudiant **{nom}** est déjà enregistré pour le groupe **{groupe}**.")
                        else:
                            sql = "INSERT INTO collect_concours (nom_etudiant, nom_groupe, localisation, cout_formation, resultat, filiere_admission) VALUES (%s, %s, %s, %s, %s, %s)"
                            val = (nom, groupe, loc, prix, res, fil if res == "Admis" else "N/A")
                            cursor.execute(sql, val)
                            conn.commit()
                            st.success("Données enregistrées avec succès !")
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
                df = df.drop_duplicates(subset=['nom_etudiant', 'nom_groupe'], keep='last')

                total_part = len(df)
                admis_df = df[df['resultat'] == 'Admis']
                taux_succes = (len(admis_df) / total_part) * 100
                taux_echec = 100 - taux_succes

                # --- AFFICHAGE DES CARTES (KPI) ---
                st.write("### 🔑 Indicateurs Clés")
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric(label="👥 Participants", value=total_part)
                with c2: st.metric(label="✅ Nombre d'Admis", value=len(admis_df))
                with c3: st.metric(label="📈 Taux de Réussite", value=f"{taux_succes:.1f}%")
                with c4: st.metric(label="📉 Taux d'Échec", value=f"{taux_echec:.1f}%")

                st.write("###") 

                # --- GRAPHIQUES ---
                g1, g2 = st.columns(2)
                with g1:
                    st.markdown("<h4 style='text-align: center;'>📉 Comparatif par Centre</h4>", unsafe_allow_html=True)
                    stats = df.groupby(['nom_groupe', 'resultat']).size().reset_index(name='Nombre')
                    fig_bar = px.bar(stats, x='nom_groupe', y='Nombre', color='resultat', 
                                     barmode='group', template='plotly_white',
                                     color_discrete_map={'Admis': '#28a745', 'Échoué': '#dc3545'})
                    st.plotly_chart(fig_bar, use_container_width=True)

                with g2:
                    st.markdown("<h4 style='text-align: center;'>🎯 Répartition par Groupe</h4>", unsafe_allow_html=True)
                    groupes_dispo = ["Tous"] + sorted(list(df['nom_groupe'].unique()))
                    groupe_sel = st.selectbox("Choisir un groupe à analyser", groupes_dispo)
                    
                    df_pie = df if groupe_sel == "Tous" else df[df['nom_groupe'] == groupe_sel]
                    
                    fig_pie = px.pie(df_pie, names='resultat', hole=0.5, 
                                     color='resultat',
                                     color_discrete_map={'Admis': '#28a745', 'Échoué': '#dc3545'})
                    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig_pie, use_container_width=True)

                with st.expander("📋 Voir la liste complète des candidats"):
                    st.dataframe(df[['nom_etudiant', 'nom_groupe', 'localisation', 'resultat', 'filiere_admission']], use_container_width=True)

                # --- RECOMMANDATION ---
                st.markdown("---")
                if taux_succes > 0:
                    group_stats = df.groupby('nom_groupe').agg(
                        total=('resultat', 'count'),
                        admis=('resultat', lambda x: (x == 'Admis').sum())
                    ).reset_index()
                    group_stats['taux'] = (group_stats['admis'] / group_stats['total']) * 100
                    best_group = group_stats.loc[group_stats['taux'].idxmax(), 'nom_groupe']
                    st.success(f"💡 **Recommandation :** Le centre **{best_group}** présente actuellement le meilleur taux de performance.")
                
            else: 
                st.warning("La base de données est actuellement vide.")
        except Exception as e: 
            st.error(f"Erreur lors du chargement des statistiques : {e}")
