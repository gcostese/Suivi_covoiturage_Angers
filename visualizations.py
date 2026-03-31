import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.colors as mcolors
import folium
from streamlit_folium import folium_static
try:
    import statsmodels
except ImportError:
    pass

# Configuration centralisée des couleurs pour la cohérence visuelle
COLORS = {
    'covoit': '#00CC96',
    'solo': '#636EFA',
    'total': '#AB63FA',
    'accent': '#E67E22',
    'bg_transparent': 'rgba(0,0,0,0)'
}

# Configuration de l'export (PNG haute résolution)
PLOTLY_CONFIG = {
    'displaylogo': False,
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'export_covoit_angers',
        'height': 720,
        'width': 1280,
        'scale': 2
    }
}

def plot_sensor_map(lat=47.463791, lon=-0.638287):
    """Génère une carte interactive Folium centrée sur le capteur."""
    # Création de la carte de base (fond clair pour la lisibilité)
    m = folium.Map(location=[lat, lon], zoom_start=15, control_scale=True, tiles="cartodbpositron")
    
    # Ajout d'un marqueur personnalisé
    folium.Marker(
        [lat, lon],
        popup="Capteur Cerema D523",
        tooltip="Localisation du capteur",
        icon=folium.Icon(color="orange", icon="info-sign")
    ).add_to(m)
    
    # Optionnel : Ajout d'un cercle pour simuler la zone de détection
    folium.Circle(
        location=[lat, lon],
        radius=100,
        color="orange",
        fill=True,
        fill_opacity=0.2
    ).add_to(m)
    
    return m

def plot_histogram_occupancy_with_perc(df):
    # 1. Pré-calcul des effectifs et pourcentages
    stats = df.groupby(['total_passengers', 'type_vehicule']).size().reset_index(name='counts')
    total = stats['counts'].sum()
    stats['percentage'] = (stats['counts'] / total) * 100

    # 2. Création du graphique
    fig = px.bar(
        stats, 
        x='total_passengers', 
        y='counts', 
        color='type_vehicule',
        barmode='group',
        text='percentage', # On définit le texte à afficher
        title="Répartition des occupants (en % du total)",
        labels={
            'total_passengers': 'Nombre d\'occupants', 
            'counts': 'Nombre de véhicules',
            'Covoiturage': 'Covoitureurs',
            'Solo': 'Autosolistes'
            },
        color_discrete_map={'Covoiturage': COLORS['covoit'], 'Solo': COLORS['solo']}
    )

    # 3. Formatage du texte (arrondi à 1 décimale + %)
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    
    fig.update_layout(
        xaxis=dict(tickmode='linear', dtick=1),
        yaxis=dict(title="Nombre de véhicules"),
        uniformtext_minsize=8, 
        uniformtext_mode='hide'
    )
    return fig

def plot_pie_carpool(df):
    """Génère un camembert du ratio Solo vs Covoiturage."""
    # Préparation simple des données
    stats = df['type_vehicule'].value_counts().reset_index()
    stats.columns = ['Type', 'Valeur']

    fig = px.pie(
        stats, 
        values='Valeur', 
        names='Type',
        title="Répartition globale du trafic",
        color='Type',
        labels={
            'Covoiturage': 'Covoitureurs',
            'Solo': 'Autosolistes'
        },
        color_discrete_map={'Covoiturage': COLORS['covoit'], 'Solo': COLORS['solo']},
        hole=0.4 # Transforme le camembert en Donut pour plus de modernité
    )
    
    # Affichage des labels et pourcentages à l'intérieur
    fig.update_traces(textinfo='percent+label', pull=[0, 0.1]) 
    
    return fig

def plot_evolution_flux(df_res):
    df_plot = df_res.reset_index().rename(columns={'index': 'datetime'})
    df_evolution = df_plot.melt(
        id_vars='datetime', 
        value_vars=['nb_vehicules', 'nb_covoit'],
        var_name='Type de flux', 
        value_name='Nombre de véhicules'
    )
    """Chronique du trafic : total vs covoiturage."""
    fig = px.line(
        df_evolution, x='datetime', y='Nombre de véhicules', color='Type de flux',
        title="Chronique du trafic : total vs covoiturage",
        line_shape='spline',
        labels={
            'datetime': 'Temps',
            'nb_vehicules': 'Total',
            'nb_covoit': 'Covoitureurs'
        },
        color_discrete_map={'nb_vehicules': COLORS['total'], 'nb_covoit': COLORS['covoit']}
    )
    fig.update_layout(hovermode="x unified")
    return fig

def plot_stacked_persons(df_stats):
    """Courbes comparatives des personnes transportées (autosolistes vs covoitureurs)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_stats['datetime'], y=df_stats['Total'],
        name="Total", line=dict(color=COLORS['total'], width=1.5)
    ))
    fig.add_trace(go.Scatter(
        x=df_stats['datetime'], y=df_stats['Covoiturage'],
        name="Covoitureurs", line=dict(color=COLORS['covoit'], width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df_stats['datetime'], y=df_stats['Solo'],
        name="Autosolistes", line=dict(color=COLORS['solo'], width=2)
    ))
    fig.update_layout(
        title="Nombre de personnes transportées : autosolistes vs covoitureurs",
        xaxis_title="Temps",
        yaxis_title="Nombre de personnes",
        hovermode="x unified"
    )
    return fig

def plot_seat_efficiency(df_hour):
    """
    Calcule et affiche le % de sièges occupés vs vides par heure.
    Base : 5 places par véhicule.
    """
    # 1. Calcul des métriques (on suppose 5 places par véhicule)
    df_hour['sieges_totaux'] = df_hour['total_veh_cumul'] * 5
    df_hour['% Occupés'] = (df_hour['total_pers_cumul'] / df_hour['sieges_totaux']) * 100
    df_hour['% Vides'] = 100 - df_hour['% Occupés']
    
    # 2. Passage en format long pour Plotly
    df_melted = df_hour.melt(
        id_vars='heure', 
        value_vars=['% Occupés', '% Vides'],
        var_name='État du siège', 
        value_name='Pourcentage'
    )

    fig = px.bar(
        df_melted, x='heure', y='Pourcentage', color='État du siège',
        title="% Sièges occupés vs vides (base = 5 places / véhicule)",
        color_discrete_map={'% Occupés': COLORS['covoit'], '% Vides': COLORS['solo']},
        barmode='stack'
    )

    # 3. Ajustement des axes pour coller à ton image (zoom sur 25% - 40%)
    fig.update_layout(
        yaxis=dict(range=[10, 50], dtick=5, ticksuffix="%"),
        xaxis=dict(tickmode='linear', dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def plot_rate_evolution(df_resampled, granularity, column, title, y_label):
    """Générateur générique pour les graphiques d'évolution (Taux covoit ou Occupation)."""
    full_range = pd.date_range(start=df_resampled.index.min(), end=df_resampled.index.max(), freq=granularity)
    df_resampled = df_resampled.reindex(full_range)
    df_plot = df_resampled.reset_index().rename(columns={'index': 'datetime'})
    df_plot['datetime'] = pd.to_datetime(df_plot['datetime'])
    df_plot[column] = df_plot[column].fillna(0)
    fig = px.area(
        df_plot, 
        x='datetime', 
        y=column, 
        title=title,
        labels={column: y_label, 'datetime': 'Temps'}
    ) 
    fig.update_traces(connectgaps=False)
    return fig

def plot_hourly_profile_mixed(df_par_heure):
    """Graphique combiné : Barres empilées (volumes) + Ligne (taux de covoiturage)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Barres empilées
    fig.add_trace(
        go.Bar(x=df_par_heure['heure'], y=df_par_heure['is_carpool'], 
               name="Covoiturage", marker_color=COLORS['covoit']),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(x=df_par_heure['heure'], y=df_par_heure['total_passengers'] - df_par_heure['is_carpool'], 
               name="Autosolistes", marker_color=COLORS['solo']),
        secondary_y=False,
    )
    
    # Ligne du taux
    fig.add_trace(
        go.Scatter(
            x=df_par_heure['heure'], y=df_par_heure['taux_moyen_covoit'],
            name="Taux de covoiturage (%)", mode='lines+markers',
            line=dict(color='Red', width=2)
        ),
        secondary_y=True,
    )
    
    fig.update_layout(
        title_text="Répartition horaire et taux de covoiturage",
        barmode='stack',
        xaxis=dict(tickmode='linear', dtick=1, range=[-0.5, 23.5]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="Débit moyen (véh/h)", secondary_y=False)
    fig.update_yaxes(title_text="Taux (%)", secondary_y=True, range=[0, 100])
    return fig

def plot_occupancy_vs_flow(df_occup_debit):
    """Relation entre le taux d'occupation et le débit horaire."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Bar(
            x=df_occup_debit['heure'], y=df_occup_debit['occupation_moy'],
            name="Occupation moyenne", marker_color='#3274A1',
            text=df_occup_debit['occupation_moy'].round(2), textposition='outside'
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df_occup_debit['heure'], y=df_occup_debit['debit_moyen'],
            name="Débit moyen (veh/h)", mode='lines+markers',
            line=dict(color='Red', width=2)
        ),
        secondary_y=True,
    )
    
    fig.update_layout(
        title_text="Taux d'occupation moyen et débit horaire",
        xaxis=dict(tickmode='linear', dtick=1, range=[-0.5, 23.5]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    fig.update_yaxes(title_text="Pers/véhicule", secondary_y=False)
    fig.update_yaxes(title_text="Débit (veh/h)", secondary_y=True)
    return fig

def plot_heatmap_covoiturage(df):
    """Génère un damier Heure vs Jour de la semaine pour le taux de covoiturage."""
    # 1. Préparation des données : extraction du nom du jour
    df_heat = df.copy()
    df_heat['jour_nom'] = df_heat['datetime'].dt.day_name()
    
    # Ordonner les jours de la semaine correctement
    jours_ordre = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    jours_traduits = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    # 2. Pivot Table : Moyenne du taux (is_carpool * 100 pour avoir un %)
    # On groupe par jour et par heure
    pivot = df_heat.groupby(['jour_nom', 'heure'])['is_carpool'].mean().unstack() * 100
    
    # Réorganiser les lignes selon l'ordre des jours
    pivot = pivot.reindex(jours_ordre)
    pivot.index = jours_traduits # Traduction pour l'affichage
    
    # 3. Création du graphique
    fig = px.imshow(
        pivot,
        labels=dict(x="Heure de la journée", y="Jour de la semaine", color="Taux (%)"),
        x=pivot.columns,
        y=pivot.index,
        color_continuous_scale="RdYlGn", # Du rouge (bas) au vert (haut)
        aspect="auto",
        title="Intensité du covoiturage par période"
    )
    
    fig.update_xaxes(dtick=1) # Afficher toutes les heures
    fig.update_layout(coloraxis_colorbar=dict(title="Taux de covoiturage (%)"))
    
    return fig

def get_bivariate_color(taux, debit_norm):
    """
    Calcule la couleur selon la colormap PiYG modifiée par le débit.
    taux: 0 à 100 | debit_norm: 0 à 1
    """
    # Points d'ancrage (R, G, B)
    rose = [197, 27, 125]    # Bas taux
    jaune = [255, 255, 191]  # Milieu (50%)
    vert = [31, 120, 31]     # Haut taux (Vert foncé type Cerema)

    # 1. Interpolation de la teinte (Hue) selon le taux
    if taux < 50:
        # Interpolation Rose -> Jaune
        f = taux / 50
        r = int(rose[0] + (jaune[0] - rose[0]) * f)
        g = int(rose[1] + (jaune[1] - rose[1]) * f)
        b = int(rose[2] + (jaune[2] - rose[2]) * f)
    else:
        # Interpolation Jaune -> Vert
        f = (taux - 50) / 50
        r = int(jaune[0] + (vert[0] - jaune[0]) * f)
        g = int(jaune[1] + (vert[1] - jaune[1]) * f)
        b = int(jaune[2] + (vert[2] - jaune[2]) * f)

    # 2. Ajustement par le débit (Luminosité/Saturation)
    # Si débit faible (0), on tend vers le blanc cassé pour "effacer" la donnée peu significative
    # Si débit fort (1), on garde la couleur pure calculée ci-dessus
    l_factor = 0.3 + (0.7 * debit_norm) 
    
    final_r = int(r * l_factor + (255 * (1 - l_factor)))
    final_g = int(g * l_factor + (255 * (1 - l_factor)))
    final_b = int(b * l_factor + (255 * (1 - l_factor)))

    return f'rgb({final_r}, {final_g}, {final_b})'

def plot_bivariate_legend():
    """Génère une matrice 10x10 servant de légende pour le heatmap bivarié."""
    grid_size = 10
    taux_vals = np.linspace(0, 100, grid_size)
    debit_vals = np.linspace(0, 1, grid_size)
    
    colors = []
    for d in debit_vals:
        row = []
        for t in taux_vals:
            # Utilisation de la nouvelle fonction commune
            row.append(get_bivariate_color(t, d))
        colors.append(row)

    fig = go.Figure(data=go.Heatmap(
        z=[[i for i in range(grid_size)] for j in range(grid_size)],
        x=taux_vals,
        y=debit_vals,
        showscale=False,
        hoverinfo='none'
    ))

    # Application des couleurs à la grille
    for r, row in enumerate(colors):
        for c, color in enumerate(row):
            fig.add_shape(type="rect", x0=taux_vals[c]-5, y0=debit_vals[r]-0.05, 
                          x1=taux_vals[c]+5, y1=debit_vals[r]+0.05, 
                          fillcolor=color, line=dict(width=0))

    fig.update_layout(
        title="Légende Bivariée",
        xaxis_title="Taux (%)",
        yaxis_title="Débit (Relatif)",
        width=250, height=250,
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(tickvals=[0, 50, 100], fixedrange=True),
        yaxis=dict(tickvals=[0, 0.5, 1], ticktext=["Faible", "Moyen", "Fort"], fixedrange=True)
    )
    return fig

def plot_heatmap_covoiturage_2d(df):
    """
    Génère un damier bivarié : 
    - Teinte (Hue) : Taux de covoiturage (Rouge -> Vert)
    - Luminosité/Saturation : Débit total (Clair -> Sombre)
    """
    df_heat = df.copy()
    df_heat['jour_nom'] = df_heat['datetime'].dt.day_name()
    jours_ordre = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    jours_traduits = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    # 1. Calcul des deux métriques
    stats = df_heat.groupby(['jour_nom', 'heure']).agg(
        taux=('is_carpool', lambda x: x.mean() * 100),
        debit=('is_carpool', 'count')
    ).reset_index()
    
    # 2. Normalisation du débit pour l'affichage (0 à 1)
    # On utilise le 95ème percentile pour éviter que les records isolés n'écrasent tout
    max_debit = stats['debit'].max() if not stats['debit'].empty else 1
    stats['debit_norm'] = stats['debit'] / max_debit
    stats['color'] = stats.apply(lambda x: get_bivariate_color(x['taux'], x['debit_norm']), axis=1)
    
    # 3. Fonction de mélange de couleurs (Bivariate Mapping)
    stats['color'] = stats.apply(lambda x: get_bivariate_color(x['taux'], x['debit_norm']), axis=1)

    # 4. Construction manuelle du Heatmap avec Graph Objects
    pivot_color = stats.pivot(index='jour_nom', columns='heure', values='color').reindex(jours_ordre)
    pivot_taux = stats.pivot(index='jour_nom', columns='heure', values='taux').reindex(jours_ordre)
    pivot_debit = stats.pivot(index='jour_nom', columns='heure', values='debit').reindex(jours_ordre)

    fig = go.Figure(data=go.Heatmap(
        z=[[i for i in range(24)] for j in range(7)], # Valeurs fictives pour la structure
        x=list(range(24)),
        y=jours_traduits,
        coloraxis="coloraxis",
        customdata=np.dstack((pivot_taux, pivot_debit)),
        hovertemplate="<b>%{y} %{x}h</b><br>Taux : %{customdata[0]:.1f}%<br>Débit : %{customdata[1]} véh/h<extra></extra>"
    ))

    # On applique les couleurs calculées cellule par cellule
    colors_list = pivot_color.values.tolist()
    fig.update_traces(zmin=0, zmax=1, showscale=False) # On cache la colorbar standard
    
    # Ajout des rectangles de couleur
    for r, row in enumerate(colors_list):
        for c, color in enumerate(row):
            fig.add_shape(type="rect", x0=c-0.5, y0=r-0.5, x1=c+0.5, y1=r+0.5, 
                          fillcolor=color, line=dict(width=0))

    fig.update_layout(title="Intensité du covoiturage bivariée (taux VS débit)",
                      xaxis_title="Heure de la journée", yaxis_title="Jour de la semaine",
                      xaxis=dict(dtick=1), yaxis=dict(autorange="reversed"))
    
    return fig

def plot_correlation_scatter(df_resampled):
    """
    Nuage de points : Total véhicules (x) vs Covoiturage (y).
    df_resampled doit contenir 'nb_vehicules', 'nb_covoit' et une colonne pour le type de jour.
    """
    # On recrée une colonne lisible pour la légende
    df_plot = df_resampled.copy().reset_index()
    df_plot['week'] = df_plot['week'].fillna(True).astype(bool)
    df_plot['Type de jour'] = df_plot['week'].map({True: 'Semaine', False: 'Week-end'})
    
    fig = px.scatter(
        df_plot, 
        x='nb_vehicules', 
        y='nb_covoit',
        color='Type de jour',
        trendline="ols", # ajoute une ligne de tendance pour voir la corrélation
        title="Corrélation : Flux total vs Covoiturage",
        labels={
            'nb_vehicules': 'Nombre total de véhicules',
            'nb_covoit': 'Nombre de véhicules en covoiturage',
            'Type de jour': 'Période'
        },
        color_discrete_map={'Semaine': COLORS['solo'], 'Week-end': COLORS['accent']},
        template="plotly_white"
    )

    # --- AJOUT DE L'ÉQUATION DANS L'INFOBULLE ---
    results = px.get_trendline_results(fig)
    for i, row in results.iterrows():
        model = row["px_fit_results"]
        b, a = model.params  # b = intercept, a = pente (slope)
        r2 = model.rsquared
        
        # Construction de la chaîne de l'équation
        equation = f"y = {a:.3f}x {b:+.1f}"
        
        # Mise à jour de la trace de tendance correspondante (index i*2 + 1)
        # On modifie le texte affiché au survol de la ligne
        fig.data[i*2 + 1].hovertemplate = (
            f"<b>Tendance {row['Période']}</b><br>" +
            f"Équation : {equation}<br>" +
            f"R² : {r2:.3f}<extra></extra>"
        )
    
    fig.update_layout(
        hovermode="closest",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
        )
    return fig