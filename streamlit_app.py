import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime as dt

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
    data['heure'] = data['datetime'].dt.hour
    data['week'] = ~data['weekend']  # True si jour de semaine hors weekend, False sinon
    data['working_day'] = ~data['holiday']  # True si jour ouvrable, False sinon
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
type_jour_semaine = st.sidebar.multiselect(
    "Jour de semaine :",
    options=df['week'].unique(),
    default=df['week'].unique()
)

# Filtre sur les jours ouvrables
type_jour = st.sidebar.multiselect(
    "Jour ouvrable :",
    options=df['working_day'].unique(),
    default=df['working_day'].unique()
)

# --- AFFICHAGE ---

st.title("🚀 Analyse des données de covoiturage sur Angers")

with st.expander("ℹ️ À propos de ce projet", expanded=True):
    col_text, col_img = st.columns([2, 1])
    with col_text:
        st.markdown("""
        Ce tableau de bord présente les données issues d'un **capteur de covoiturage** déployé par le **Cerema** sur la **D523 à Angers**.
        
        **Objectifs :**
        * Suivre l'évolution des pratiques de mobilité sur cet axe structurant.
        * Alimenter l'**[Observatoire National du Covoiturage au Quotidien](https://observatoire.covoiturage.gouv.fr/)**.
        * Comparer ces performances avec d'autres sites instrumentés en France.
        
        📍 **Localisation :** [Voir sur Google Street View](https://maps.app.goo.gl/jFscxgeSwcsrVd9L9)
        """)
    with col_img:
        # Remplace l'URL par une image réelle du capteur ou du site si disponible
        st.image("BlocMarque_RF-Cerema_horizontal.jpg", width=150)


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
mask = (df['working_day'].isin(type_jour)) & (df['week'].isin(type_jour_semaine))
df_filtered = df[mask].copy()

df_resampled = df_filtered.set_index('datetime').resample(granularity).agg({
    'total_passengers': ['count', 'sum'], # count = nb véhicules, sum = nb personnes
    'is_carpool': 'sum'                    # sum de booléens = nb de True (véhicules covoit)
})

# Nettoyage des noms de colonnes après agrégation
df_resampled.columns = ['nb_vehicules', 'total_personnes', 'nb_covoit']

df_par_heure = df_filtered.groupby('heure').agg({
    'total_passengers': 'count', #['count', 'sum'],  # count = nb véhicules, sum = nb personnes
    'is_carpool': 'sum'            # Nombre de covoiturages
}).reset_index()

df_par_heure['taux_moyen_covoit'] = (df_par_heure['is_carpool'] / df_par_heure['total_passengers'].replace(0, 1)) * 100

# Calcul des indicateurs clés
df_resampled['taux_covoiturage'] = (df_resampled['nb_covoit'] / df_resampled['nb_vehicules']) * 100
df_resampled['taux_occupation_moyen'] = df_resampled['total_personnes'] / df_resampled['nb_vehicules']

# Préparation des données pour la courbe combinée
df_evolution = df_resampled.reset_index().melt(
    id_vars='datetime', 
    value_vars=['nb_vehicules', 'nb_covoit'],
    var_name='Type de flux', 
    value_name='Nombre de véhicules'
)


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

st.subheader("📊 Distribution de l'occupation")
# On utilise df_filtered pour garder la précision par véhicule
fig_hist = px.histogram(
    df_filtered, 
    x='total_passengers', 
    color='type_vehicule',
    barmode='group',
    title="Nombre de personnes par véhicule (Répartition)",
    labels={'total_passengers': 'Nombre d\'occupants', 'count': 'Nombre de véhicules'},
    category_orders={"total_passengers": [1, 2, 3, 4, 5]}
)
st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# Graphique principal
st.subheader(f"Évolution temporelle")

tab1, tab2, tab3, tab4 = st.tabs(["Taux de covoiturage (%)", "Taux d'occupation", "Titre à trouver"])

with tab1:
    fig_covoit = px.line(df_resampled.reset_index(), x='datetime', y='taux_covoiturage', 
                         title="Évolution du taux de covoiturage",
                         labels={'taux_covoiturage': 'Taux (%)', 'datetime': 'Temps'})
    st.plotly_chart(fig_covoit, use_container_width=True)

    fig_horaire = px.bar(
        df_par_heure, 
        x='heure', 
        y='taux_moyen_covoit',
        title="Taux de covoiturage moyen par heure",
        labels={'heure': 'Heure de la journée', 'taux_moyen_covoit': 'Taux moyen (%)'},
        color='taux_moyen_covoit',
        color_continuous_scale='Viridis'
    )
    # Ajuster l'axe X pour voir toutes les heures
    fig_horaire.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=1))
    st.plotly_chart(fig_horaire, use_container_width=True)

with tab2:
    fig_occup = px.area(df_resampled.reset_index(), x='datetime', y='taux_occupation_moyen',
                        title="Évolution de l'occupation moyenne",
                        labels={'taux_occupation_moyen': 'Nombre de personnes par véhicule'})
    st.plotly_chart(fig_occup, use_container_width=True)
with tab3:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=df_par_heure['heure'],
            y=df_par_heure['is_carpool'],
            name="Covoiturage",
            marker_color='#E67E22' # Orange
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df_par_heure['heure'],
            y=df_par_heure['total_passengers'] - df_par_heure['is_carpool'],
            name="Autosolistes",
            marker_color='#3498DB' # Bleu
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_par_heure['heure'],
            y=df_par_heure['taux_moyen_covoit'],
            name="Taux de covoiturage (%)",
            mode='lines+markers+text',
            text=[f"{val:.0f}%" for val in df_par_heure['taux_moyen_covoit']],
            textposition="top center",
            line=dict(color='Red', width=2),
            marker=dict(size=8)
        ),
        secondary_y=True,
    )
    fig.update_layout(
        title_text="Répartition horaire et taux de covoiturage",
        barmode='stack', # Pour empiler les barres bleu et orange
        xaxis=dict(tickmode='linear', dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Nombre de véhicules", secondary_y=False)
    fig.update_yaxes(title_text="Taux de covoiturage (%)", secondary_y=True, range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)
with tab4:
    fig_combinee = px.line(
        df_evolution, 
        x='datetime', 
        y='Nombre de véhicules', 
        color='Type de flux',
        title="Chronique du trafic : Global vs Covoiturage",
        line_shape='spline', # Pour des courbes plus lisses
        color_discrete_map={'nb_vehicules': '#636EFA', 'nb_covoit': '#00CC96'}
    )
    st.plotly_chart(fig_combinee, use_container_width=True)

# Aperçu des données agrégées
with st.expander("Voir les données agrégées"):
    st.dataframe(df_resampled)



# Bouton d'action
if st.button("Célébrer le déploiement !"):
    st.balloons()
    st.success("L'appli fonctionne parfaitement !")