import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import visualizations as viz
from streamlit_folium import st_folium

# ---- FONCTIONS UTILES ----
# Fonction de chargement des données (Utilise le cache pour éviter de recharger à chaque clic)
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

@st.cache_data
def get_processed_data(df, working_days, week_days, granularity, selected_hours):
    """Calcule toutes les agrégations nécessaires en une seule fois (Performance)."""
    mask = (
        (df['working_day'].isin(working_days)) & 
        (df['week'].isin(week_days)) &
        (df['heure'].isin(selected_hours))
    )
    df_f = df[mask].copy()
    
    # Évolution temporelle
    resampled = df_f.set_index('datetime').resample(granularity).agg({
        'total_passengers': ['count', 'sum'],
        'is_carpool': 'sum'
    })
    resampled.columns = ['nb_vehicules', 'total_personnes', 'nb_covoit']
    resampled['taux_covoiturage'] = (resampled['nb_covoit'] / resampled['nb_vehicules']) * 100
    resampled['taux_occupation_moyen'] = resampled['total_personnes'] / resampled['nb_vehicules']
    
    # Profil horaire
    hourly = df_f.groupby('heure').agg({
        'total_passengers': ['count', 'mean'],
        'is_carpool': 'sum'
    }).reset_index()
    hourly.columns = ['heure', 'total_veh', 'occup_moy', 'nb_covoit']
    hourly['taux_covoit'] = (hourly['nb_covoit'] / hourly['total_veh']) * 100
    
    return df_f, resampled, hourly

def fmt_fr(val, decimal=0):
    return f"{val:,.{decimal}f}".replace(",", " ").replace(".", ",")

# --- SECTIONS DE L'INTERFACE ---
def render_header():
    st.title("🚀 Analyse des données de covoiturage sur Angers")
    with st.expander("ℹ️ À propos de ce projet", expanded=True):
        col_text, col_map, col_img = st.columns([1, 1, 1])
        with col_text:
            st.markdown("""
            Ce tableau de bord présente les données issues d'un **capteur de covoiturage** déployé par le **Cerema** sur la **D523 à Angers**.
            
            **Objectifs :**
            * Suivre l'évolution des pratiques de mobilité sur cet axe structurant.
            * Alimenter l'**[Observatoire National du Covoiturage au Quotidien](https://observatoire.covoiturage.gouv.fr/)**.
            * Comparer ces performances avec d'autres sites instrumentés en France.
            """)
        with col_map:
            st.markdown("""📍 **Localisation :** """)
            # Affichage de la carte interactive
            m = viz.plot_sensor_map()
            if m:
                st_folium(m, width=400, height=200, key="angers_map")
            else:
                st.error("Impossible de charger la carte.")
                st.link_button("Voir l'emplacement du capteur sur Google Maps", "https://maps.app.goo.gl/ckfqhaZpKWt8UyMY6")
        with col_img:
            map_html = """
            <iframe src="https://www.google.com/maps/embed?pb=!4v1774273135064!6m8!1m7!1srhUgFf_7vpdd4CoIKwl9oQ!2m2!1d47.46375210665583!2d-0.6383491700641112!3f69.2!4f5.079999999999998!5f1.1924812503605782" 
            width="400" height="400" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
            """
            components.html(map_html, height=450)

def render_metrics(df_raw, df_f, df_res):
    st.markdown(f"Voici les premiers résultats issus de l'analyse sur **{fmt_fr(len(df_f))}" + 
                f"** passages de véhicules légers (sur un total de {fmt_fr(len(df_raw))}).")
    c1, c2, c3, c4 = st.columns(4)
    total_v = len(df_f)
    total_c = df_res['nb_covoit'].sum()
    c1.metric("Nombre total de véhicules", f"{fmt_fr(total_v)}")
    c2.metric("Nombre de véhicules en covoiturage", f"{fmt_fr(total_c)}")
    c3.metric("Taux de covoiturage", f"{(total_c/total_v*100):.1f}%".replace(".", ","))
    c4.metric("Taux d'occupation moyen", f"{df_f['total_passengers'].mean():.2f}".replace(".", ","))


# --- FONCTION PRINCIPALE ---
def main():
    st.set_page_config(page_title="Mesure du covoiturage à Angers", 
                       page_icon="📊", 
                       layout="wide")
    PERIODS = {
        "Toute la journée": list(range(0, 24)),
        "Pointe Matin (7h-9h)": [7, 8, 9],
        "Creux Journée (10h-16h)": [10, 11, 12, 13, 14, 15],
        "Pointe Soir (16h-19h)": [16, 17, 18],
        "Nuit (19h-7h)": [19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6]
    }
    
    # ---- CHARGEMENT DES DONNÉES ----
    try:
        df_raw = load_data('donnees_angers.parquet')
    except FileNotFoundError:
        st.error("Le fichier de données n'a pas été trouvé.")
        st.stop()

    # ---- PARAMETRAGE ----
    st.sidebar.image("BlocMarque_RF-Cerema_horizontal.jpg", 
                     use_container_width=True)

    # Sidebar pour les filtres
    st.sidebar.header("⚙️ Configuration")

    # Choix de la maille temporelle
    granularity = st.sidebar.selectbox(
        "Fréquence de regroupement :",
        options=['H', 'D', 'W'], 
        format_func=lambda x: {'H': 'Heure', 'D': 'Jour', 'W': 'Semaine'}[x]
    )

    selected_period_label = st.sidebar.selectbox(
        "Tranche horaire :",
        options=list(PERIODS.keys()),
        index=0
    )
    selected_hours = PERIODS[selected_period_label]

    # Filtre sur les jours de semaine
    choix_semaine = st.sidebar.radio(
        "Type de jours :",
        ["Tous", "Semaine uniquement", "Week-end uniquement"],
        horizontal=True
    )

    mapping_semaine = {
        "Tous": [True, False],
        "Semaine uniquement": [True],
        "Week-end uniquement": [False]
    }
    type_jour_sem = mapping_semaine[choix_semaine]

    # Filtre sur les jours ouvrables
    choix_ouv = st.sidebar.radio(
        "Calendrier :",
        ["Tous", "Jours ouvrés", "Fériés"],
        horizontal=True
    )

    mapping_ouv = {
        "Tous": [True, False],
        "Jours ouvrés": [True],
        "Fériés": [False]
    }
    type_jour_ouv = mapping_ouv[choix_ouv]

    # --- Calculs ---
    df_f, df_res, df_hour = get_processed_data(
        df_raw, 
        type_jour_ouv, 
        type_jour_sem, 
        granularity, 
        selected_hours
        )


    # --- AFFICHAGE ---
    render_header()
    st.divider()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("cd_42840474_animation.gif", 
                 caption="Exemple de véhicule avec 4 occupants détectés par le capteur (Crédit : Cerema)",
                 use_container_width=True)

    st.divider()

    # --- APERÇU DES DONNÉES ---
    st.subheader("👀 Aperçu du jeu de données")

    render_metrics(df_raw, df_f, df_res)

    tab1, tab2 = st.tabs(["Tableau complet", "Statistiques descriptives"])

    with tab1:
        st.write("Voici les 10 premières lignes :")
        st.dataframe(df_raw.head(10), use_container_width=True)

    with tab2:
        st.write("Résumé mathématique de l'ensemble :")
        st.write(df_raw.describe())

    st.divider() # Petite ligne de séparation

    # --- TRAITEMENT DES DONNÉES ---
    tab_dist, tab_evol, tab_hour, tab_week = st.tabs(["🎯 Distribution", "📈 Évolution", "🕒 Profil horaire", "🏁 Profil hebdomadaire"])

    with tab_dist:
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(viz.plot_histogram_occupancy_with_perc(df_f), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")
        with col2:
            st.plotly_chart(viz.plot_pie_carpool(df_f), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")

    with tab_evol:
        st.subheader("Chroniques des flux (de véhicules et de personnes)")
        st.plotly_chart(viz.plot_evolution_flux(df_res), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")
        
        # Graphique Solo/Covoit (pré-calculé pour viz)
        df_stats = df_f.groupby([pd.Grouper(key='datetime', freq=granularity), 'type_vehicule'])['total_passengers'].sum().unstack(fill_value=0)
        df_stats['Total'] = df_stats.sum(axis=1)
        st.plotly_chart(viz.plot_stacked_persons(df_stats.reset_index()), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")

        st.divider()
        st.subheader("Évolution du taux de covoiturage")
        st.plotly_chart(
            viz.plot_rate_evolution(df_res, 'taux_covoiturage', "Taux de covoiturage", "Pourcentage"),
            use_container_width=True, 
            theme="streamlit"
        )

        st.divider()
        st.subheader("Évolution du taux d'occupation")
        st.plotly_chart(
            viz.plot_rate_evolution(df_res, 'taux_occupation_moyen', "Occupation moyenne par véhicule", "Pers/Véh"),
            use_container_width=True, 
            theme="streamlit"
        )

    with tab_hour:
        # Adaptation des noms pour viz.py
        df_hour_renamed = df_hour.rename(columns={'total_veh': 'total_passengers', 'nb_covoit': 'is_carpool', 'taux_covoit': 'taux_moyen_covoit'})
        st.plotly_chart(viz.plot_hourly_profile_mixed(df_hour_renamed), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")
        
        df_occ_flow = df_hour.rename(columns={'occup_moy': 'occupation_moy', 'total_veh': 'debit_moyen'})
        st.plotly_chart(viz.plot_occupancy_vs_flow(df_occ_flow), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")

    with tab_week:
        st.plotly_chart(viz.plot_heatmap_covoiturage(df_f), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")

    # --- FOOTER ---
    # Aperçu des données agrégées
    with st.expander("Voir les données agrégées"):
        st.dataframe(df_res)

    with st.expander("💾 Exporter les données"):
        st.download_button("Télécharger les données filtrées (CSV)", df_f.to_csv(index=False), "data_angers.csv", "text/csv")

if __name__ == "__main__":
    main()