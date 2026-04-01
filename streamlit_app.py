import streamlit as st
import pandas as pd
import numpy as np
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
    data['week'] = ~data['weekend'].fillna(False) # True si jour de semaine hors weekend, False sinon
    data['working_day'] = ~data['holiday']  # True si jour ouvrable, False sinon
    data['is_carpool'] = data['total_passengers'] > 1
    data['type_vehicule'] = data['is_carpool'].map({True: 'Covoiturage', False: 'Solo'})
    return data

@st.cache_data
def get_processed_data(df, working_days, week_days, granularity, selected_hours):
    """Calcule toutes les agrégations nécessaires en une seule fois."""
    mask = (
        (df['working_day'].isin(working_days)) & 
        (df['week'].isin(week_days)) &
        (df['heure'].isin(selected_hours))
    )
    df_f = df[mask].copy()
    
    nb_jours = df_f['datetime'].dt.date.nunique()
    if nb_jours == 0:
        nb_jours = 1

    # Évolution temporelle
    resampled = df_f.set_index('datetime').resample(granularity).agg({
        'total_passengers': ['count', 'sum'],
        'is_carpool': 'sum',
        'week': 'first'
    })
    resampled.columns = ['nb_vehicules', 'total_personnes', 'nb_covoit', 'week']
    resampled['taux_covoiturage'] = (resampled['nb_covoit'] / resampled['nb_vehicules']) * 100
    resampled['taux_occupation_moyen'] = resampled['total_personnes'] / resampled['nb_vehicules']
    
    # Profil horaire : on calcule la somme, puis on divise par le nombre de jours
    hourly = df_f.groupby('heure').agg({
        'total_passengers': ['count', 'sum'], # count = nb vehicules
        'is_carpool': 'sum'
    }).reset_index()
    
    hourly.columns = ['heure', 'total_veh_cumul', 'total_pers_cumul', 'nb_covoit_cumul']
    
    # Normalisation par le nombre de jours pour obtenir une moyenne horaire
    hourly['debit_moyen'] = hourly['total_veh_cumul'] / nb_jours
    hourly['covoit_moyen'] = hourly['nb_covoit_cumul'] / nb_jours
    hourly['autosolo_moyen'] = (hourly['total_veh_cumul'] - hourly['nb_covoit_cumul']) / nb_jours
    
    # Les taux restent inchangés car le ratio cumulé ou moyen est le même
    hourly['taux_covoit'] = (hourly['nb_covoit_cumul'] / hourly['total_veh_cumul']) * 100
    hourly['occup_moy'] = hourly['total_pers_cumul'] / hourly['total_veh_cumul']
    
    return df_f, resampled, hourly, nb_jours

def fmt_fr(val, decimal=0):
    return f"{val:,.{decimal}f}".replace(",", " ").replace(".", ",")

# --- SECTIONS DE L'INTERFACE ---
def render_header():
    st.title("🚗👥 Analyse des données de covoiturage sur Angers")
    with st.expander("ℹ️ À propos de ce projet", expanded=True):
        st.markdown("""
            Ce tableau de bord présente les données issues d'un **capteur de covoiturage** de la société [Invision AI](https://invision.ai/) 
                        déployé par le **[Cerema](https://www.cerema.fr/)** 
                        sur la **D523 à Angers** en partenariat avec le [Département de Maine-et-Loire](https://www.maine-et-loire.fr).
            
            **Objectifs :**
            * Suivre l'évolution des pratiques de mobilité sur cet axe structurant.
            * Alimenter l'**[Observatoire National du Covoiturage au Quotidien](https://observatoire.covoiturage.gouv.fr/)**.
            * Comparer ces performances avec d'autres sites instrumentés en France.
            """)

        col1, col_map, col_img, col4 = st.columns([1, 2, 2, 1])
        with col_map:
            st.markdown("""📍 **Localisation :** """)
            # Affichage de la carte interactive
            m = viz.plot_sensor_map()
            if m:
                st_folium(m, width=400, height=300, key="angers_map")
            else:
                st.error("Impossible de charger la carte.")
                st.link_button("Voir l'emplacement du capteur sur Google Maps", "https://maps.app.goo.gl/ckfqhaZpKWt8UyMY6")
        with col_img:
            map_html = """
            <iframe src="https://www.google.com/maps/embed?pb=!4v1774273135064!6m8!1m7!1srhUgFf_7vpdd4CoIKwl9oQ!2m2!1d47.46375210665583!2d-0.6383491700641112!3f69.2!4f5.079999999999998!5f1.1924812503605782" 
            width="400" height="300" style="border:0;" allowfullscreen="" loading="lazy" referrerpolicy="no-referrer-when-downgrade"></iframe>
            """
            components.html(map_html, height=450)

def render_metrics(df_raw, df_f, df_res, nb_jours):
    st.markdown(f"Voici les premiers résultats issus de l'analyse de **{fmt_fr(len(df_f))}**" + 
                f" passages de véhicules légers (sur un total de {fmt_fr(len(df_raw))})" +
                f" pour une période de **{nb_jours}** jours.")
    c1, c2, c3, c4, c5 = st.columns(5)
    total_v = len(df_f)
    total_c = df_res['nb_covoit'].sum()
    c1.metric("Nombre total de véhicules", f"{fmt_fr(total_v)}")
    c2.metric("Nombre de véhicules en covoiturage", f"{fmt_fr(total_c)}")
    c3.metric("Taux de covoiturage", f"{(total_c/total_v*100):.1f}%".replace(".", ","))
    c4.metric("Taux d'occupation moyen", f"{df_f['total_passengers'].mean():.2f}".replace(".", ","))
    c5.metric("Nombre de jours analysés", f"{fmt_fr(nb_jours)}")


# --- FONCTION PRINCIPALE ---
def main():
    st.set_page_config(page_title="Mesure du covoiturage à Angers", 
                       page_icon="📊", 
                       layout="wide")
    PERIODS = {
        "Toute la journée": list(range(0, 24)),
        "Pointe du matin (7h-9h)": [7, 8, 9],
        "Creux en journée (10h-16h)": [10, 11, 12, 13, 14, 15],
        "Pointe du soir (16h-19h)": [16, 17, 18],
        "Nuit (19h-7h)": [0, 1, 2, 3, 4, 5, 6,19, 20, 21, 22, 23]
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
    granularity = 'h'
    #granularity = st.sidebar.selectbox(
    #    "Fréquence de regroupement :",
    #    options=['h', 'd', 'w'], 
    #    format_func=lambda x: {'h': 'Heure', 'd': 'Jour', 'w': 'Semaine'}[x]
    #)

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
        horizontal=False
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
        ["Tous", "Jours ouvrés", "Fériés ou vacances scolaires"],
        horizontal=False
    )

    mapping_ouv = {
        "Tous": [True, False],
        "Jours ouvrés": [True],
        "Fériés ou vacances scolaires": [False]
    }
    type_jour_ouv = mapping_ouv[choix_ouv]

    # --- Calculs ---
    df_f, df_res, df_hour, nb_jours_select = get_processed_data(
        df_raw, 
        type_jour_ouv, 
        type_jour_sem, 
        granularity, 
        selected_hours
        )
    # Supprime les périodes agrégées qui ne contiennent aucun véhicule
    df_res_mod = df_res[df_res['nb_vehicules'] > 0]

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

    render_metrics(df_raw, df_f, df_res, nb_jours_select)

    st.write("Voici les 10 premières lignes :")
    st.dataframe(df_raw.head(10), use_container_width=True)

    st.divider() # Petite ligne de séparation

    # --- TRAITEMENT DES DONNÉES ---
    st.subheader("🖥️ Datavisualisation")
    tab_dist, tab_evol, tab_hour, tab_week, tab_corr = st.tabs(["📊 Distribution", "📈 Évolution", "🕒 Profil horaire", "📅 Profil hebdomadaire", "🔀 Corrélation"])

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
        full_range = pd.date_range(start=df_stats.index.min(), end=df_stats.index.max(), freq=granularity)
        df_stats = df_stats.reindex(full_range, fill_value=0)
        df_stats['Total'] = df_stats.sum(axis=1)
        st.plotly_chart(viz.plot_stacked_persons(df_stats.reset_index().rename(columns={'index': 'datetime'})), 
                        use_container_width=True, 
                        config=viz.PLOTLY_CONFIG, 
                        theme="streamlit"
                        )

        st.divider()
        st.subheader("Évolution du taux de covoiturage")
        st.plotly_chart(
            viz.plot_rate_evolution(df_res, granularity, 'taux_covoiturage', "Taux de covoiturage", "Pourcentage"),
            use_container_width=True, 
            theme="streamlit"
        )

        st.divider()
        st.subheader("Évolution du taux d'occupation")
        st.plotly_chart(
            viz.plot_rate_evolution(df_res, granularity, 'taux_occupation_moyen', "Occupation moyenne par véhicule", "Pers/Véh"),
            use_container_width=True, 
            theme="streamlit"
        )

    with tab_hour:
        df_hour_viz = df_hour.rename(columns={
            'debit_moyen': 'total_passengers', # Pour plot_hourly_profile_mixed
            'covoit_moyen': 'is_carpool', 
            'taux_covoit': 'taux_moyen_covoit',
            'occup_moy': 'occupation_moy'      # Pour plot_occupancy_vs_flow
        })
        
        st.plotly_chart(viz.plot_hourly_profile_mixed(df_hour_viz), use_container_width=True)

        df_occ_flow = df_hour.rename(columns={
            'occup_moy': 'occupation_moy', 
            'debit_moyen': 'debit_moyen'
            })
        st.plotly_chart(viz.plot_occupancy_vs_flow(df_occ_flow), use_container_width=True)

        st.divider()
        st.subheader("Analyse des sièges vides")
        st.plotly_chart(viz.plot_seat_efficiency(df_hour), use_container_width=True)

    with tab_week:
        st.plotly_chart(viz.plot_heatmap_covoiturage(df_f), use_container_width=True, config=viz.PLOTLY_CONFIG, theme="streamlit")
        
        # Analyse bivariée
        taux_series = df_f.groupby([df_f['datetime'].dt.day_name(), 'heure'])['is_carpool'].mean() * 100
        t_min, t_max = taux_series.min(), taux_series.max()
        col_chart, col_legend = st.columns([4, 1])
        with col_chart:
            st.plotly_chart(viz.plot_heatmap_covoiturage_2d(df_f), use_container_width=True) 
        with col_legend:
            st.plotly_chart(viz.plot_bivariate_legend(t_min, t_max), use_container_width=True, config={'displayModeBar': False})
            st.info("La carte de chaleur bivariée utilise la couleur pour le taux et l'intensité pour le volume de trafic.")
    
    with tab_corr:
        fig_corr = viz.plot_correlation_scatter(df_res_mod)
        # Extraire les résultats de la tendance
        try:
            import plotly.express as px
            # Récupération des résultats de toutes les lignes de tendance
            results = px.get_trendline_results(fig_corr)
            # Création de colonnes dynamiques selon le nombre de périodes trouvées
            if results is not None and not results.empty:
                # On crée autant de colonnes qu'il y a de tracés (Semaine, Week-end, etc.)
                cols_metrics = st.columns(len(results))
                for i, row in results.iterrows():
                    # Extraire les infos du modèle statsmodels sous-jacent
                    model = row["px_fit_results"]
                    nom_periode = row["Période"]
                    # Récupérer le R2 et le nombre d'observations (n)
                    r2_val = model.rsquared
                    n_points = int(model.nobs)
                    
                    if np.isnan(r2_val) or model.nobs <= 1:
                        continue

                    # Affichage dans la colonne dédiée
                    with cols_metrics[i]:
                        b, a = model.params
                        st.metric(
                            label=f"R² ({nom_periode})", 
                            value=f"{r2_val:.3f}".replace(".", ",")
                        )
                        st.write(f"Equation : :blue[$y = {a:.3f}x {b:+.1f}$]") # Affiche l'équation en bleu
                        st.caption(f"Basé sur **{n_points}** points de mesure")
        except Exception as e:
            st.info(f"Les lignes de tendance ne sont pas disponibles pour cet affichage. \\ Erreur : {e}")
        st.plotly_chart(fig_corr, use_container_width=True)

    # --- FOOTER ---
    st.subheader("🚀 Aller plus loin")

    # Aperçu des données agrégées
    with st.expander("Voir les données agrégées"):
        st.dataframe(df_res)

    with st.expander("💾 Exporter les données"):
        st.download_button("Télécharger les données filtrées (CSV)", df_f.to_csv(index=False), "data_angers.csv", "text/csv")

if __name__ == "__main__":
    main()