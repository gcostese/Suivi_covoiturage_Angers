import streamlit as st
import pandas as pd
import plotly.express as px

# ---- FONCTIONS UTILES ----
# 1. Configuration de la page (Optionnel mais recommandé)
st.set_page_config(
    page_title="Analyse de données de covoiturage à Angers",
    page_icon="📊",
    layout="wide"
)

# 2. Fonction de chargement des données (Utilise le cache pour éviter de recharger à chaque clic)
@st.cache_data
def load_data(file_path):
    data = pd.read_parquet(file_path)
    data['datetime'] = pd.to_datetime(data['datetime'])
    data['is_carpool'] = data['total_passengers'] > 1
    data['type_vehicule'] = data['is_carpool'].map({True: 'Covoiturage', False: 'Solo'})
    return data


# ---- CHARGEMENT DES DONNÉES ----
try:
    df = load_data('donnees_angers.parquet')
except FileNotFoundError:
    st.error("Le fichier de données n'a pas été trouvé.")
    st.stop()


# ---- PARAMETRAGE ----
# Sidebar pour les filtres
st.sidebar.header("Filtres")

# Choix de la maille temporelle
granularity = st.sidebar.selectbox(
    "Fréquence de regroupement :",
    options=['H', 'D', 'W'], 
    format_func=lambda x: {'H': 'Heure', 'D': 'Jour', 'W': 'Semaine'}[x]
)

# Filtre sur les jours ouvrables
type_jour = st.sidebar.multiselect(
    "Type de jour :",
    options=df['holiday'].unique(),
    default=df['holiday'].unique()
)

# --- AFFICHAGE ---

st.title("🚀 Analyse des données de covoiturage sur Angers")
st.write("Voici les premiers résultats extraits du projet.")

st.markdown(f"Analyse basée sur **{len(df):,}** passages de véhicules.")

# --- APERÇU DES DONNÉES ---
st.subheader("👀 Aperçu du jeu de données")

tab1, tab2 = st.tabs(["Tableau complet", "Statistiques descriptives"])

with tab1:
    st.write("Voici les 10 premières lignes :")
    st.dataframe(df.head(10), use_container_width=True)

with tab2:
    st.write("Résumé mathématique de l'ensemble :")
    st.write(df.describe())

st.divider() # Petite ligne de séparation

# --- TRAITEMENT DES DONNÉES ---
# Filtrage par type de jour
mask = df['holiday'].isin(type_jour)
df_filtered = df[mask].copy()

df_resampled = df_filtered.set_index('datetime').resample(granularity).agg({
    'total_passengers': ['count', 'sum'], # count = nb véhicules, sum = nb personnes
    'is_covoit': 'sum'                    # sum de booléens = nb de True (véhicules covoit)
})

# Nettoyage des noms de colonnes après agrégation
df_resampled.columns = ['nb_vehicules', 'total_personnes', 'nb_covoit']

# Calcul des indicateurs clés
df_resampled['taux_covoiturage'] = (df_resampled['nb_covoit'] / df_resampled['nb_vehicules']) * 100
df_resampled['taux_occupation_moyen'] = df_resampled['total_personnes'] / df_resampled['nb_vehicules']

# Métriques clés
c1, c2, c3, c4 = st.columns(4)
total_v = df_resampled['nb_vehicules'].sum()
total_c = df_resampled['nb_covoit'].sum()
avg_occup = df_filtered['total_passengers'].mean()

c1.metric("Véhicules Total", f"{total_v:,}")
c2.metric("Véhicules Covoit.", f"{total_c:,}")
c3.metric("Taux Covoit. Moyen", f"{(total_c/total_v)*100:.1f}%")
c4.metric("Occupation Moyenne", f"{avg_occup:.2f} pers/véh")

st.divider()

# Graphique principal
st.subheader(f"Évolution temporelle (par {granularity.lower()})")

tab1, tab2 = st.tabs(["Taux de Covoiturage (%)", "Taux d'Occupation"])

with tab1:
    fig_covoit = px.line(df_resampled.reset_index(), x='datetime', y='taux_covoiturage', 
                         title="Évolution du taux de covoiturage",
                         labels={'taux_covoiturage': 'Taux (%)', 'datetime': 'Temps'})
    st.plotly_chart(fig_covoit, use_container_width=True)

with tab2:
    fig_occup = px.area(df_resampled.reset_index(), x='datetime', y='taux_occupation_moyen',
                        title="Évolution de l'occupation moyenne",
                        labels={'taux_occupation_moyen': 'Passagers / Véhicule'})
    st.plotly_chart(fig_occup, use_container_width=True)

# Aperçu des données agrégées
with st.expander("Voir les données agrégées"):
    st.dataframe(df_resampled)



# Bouton d'action
if st.button("Célébrer le déploiement !"):
    st.balloons()
    st.success("L'appli fonctionne parfaitement !")