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

def plot_histogram_occupancy(df):
    """Distribution du nombre de personnes par véhicule."""
    fig = px.histogram(
        df, 
        x='total_passengers', 
        color='type_vehicule',
        barmode='group',
        title="Nombre de personnes par véhicule",
        labels={'total_passengers': 'Nombre d\'occupants', 'count': 'Nombre de véhicules'},
        category_orders={"total_passengers": [1, 2, 3, 4, 5]},
        color_discrete_map={'Covoiturage': COLORS['covoit'], 'Autosolistes': COLORS['solo']}
    )
    fig.update_layout(
        xaxis=dict(tickmode='linear', tick0=1, dtick=1, range=[0.5, 5.5]),
        bargap=0.4,
        template="plotly_white"
    )
    return fig

def plot_evolution_flux(df_res):
    """Chronique du trafic : total vs covoiturage."""
    # Préparation des données pour le tracé
    df_melt = df_res.reset_index().melt(
        id_vars='datetime', 
        value_vars=['nb_vehicules', 'nb_covoit'], 
        var_name='Type de flux', 
        value_name='Nombre'
    )
    fig = px.line(
        df_melt, x='datetime', y='Nombre', color='Type de flux',
        title="Chronique du trafic : total vs covoiturage",
        line_shape='spline',
        color_discrete_map={'nb_vehicules': COLORS['solo'], 'nb_covoit': COLORS['covoit']}
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
        name="Autosolistes", line=dict(color="#FF4B4B", width=2)
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
               name="Covoiturage", marker_color=COLORS['accent']),
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Nb véhicules", secondary_y=False)
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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_yaxes(title_text="Pers/véhicule", range=[1.0, 1.8], secondary_y=False)
    fig.update_yaxes(title_text="Débit (veh/h)", secondary_y=True)
    return fig