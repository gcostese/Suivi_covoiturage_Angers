import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static

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
    # On prépare la donnée melt pour l'évolution
    df_evolution = df_res.reset_index().melt(
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

def plot_rate_evolution(df_resampled, column, title, y_label):
    """Générateur générique pour les graphiques d'évolution (Taux covoit ou Occupation)."""
    fig = px.area(
        df_resampled.reset_index(), 
        x='datetime', 
        y=column, 
        title=title,
        labels={column: y_label, 'datetime': 'Temps'}
    )
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
    fig.update_yaxes(title_text="Pers/véhicule", range=[1.0, 2.0], secondary_y=False)
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
    fig.update_layout(coloraxis_colorbar=dict(title="%"))
    
    return fig