import streamlit as st
import pandas as pd
import numpy as np

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

st.markdown(f"Analyse basée sur **{len(df_filtered):,}** passages de véhicules.")

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
c1, c2, c3 = st.columns(3)
total_v = len(df_filtered)
covoit_v = df_filtered['is_covoit'].sum()
perc_covoit = (covoit_v / total_v * 100) if total_v > 0 else 0

c1.metric("Total Véhicules", f"{total_v:,}")
c2.metric("Véhicules en Covoiturage", f"{covoit_v:,}")
c3.metric("Taux de Covoiturage", f"{perc_covoit:.1f}%")

# Graphique principal
st.subheader(f"Évolution du trafic (par {granularity.lower()})")
st.line_chart(df_grouped)

# Aperçu des données agrégées
with st.expander("Voir le tableau des données agrégées"):
    st.dataframe(df_grouped, use_container_width=True)

# Statistiques Min/Max sur la période
st.subheader("📍 Extrêmes de la période")
if not df_grouped.empty:
    total_col = df_grouped.sum(axis=1) if show_covoit_split else df_grouped['Total Véhicules']
    max_val = total_col.max()
    max_time = total_col.idxmax()
    min_val = total_col.min()
    min_time = total_col.idxmin()
    
    col_a, col_b = st.columns(2)
    col_a.info(f"**Pic d'affluence :** {max_val} véhicules le {max_time.strftime('%d/%m à %Hh')}")
    col_b.info(f"**Minimum de trafic :** {min_val} véhicules le {min_time.strftime('%d/%m à %Hh')}")

# Bouton d'action
if st.button("Célébrer le déploiement !"):
    st.balloons()
    st.success("L'appli fonctionne parfaitement !")