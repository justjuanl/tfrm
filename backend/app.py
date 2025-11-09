import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sys
import os
import time

def get_variable_label(variable):
    """Return Spanish label for variable"""
    labels = {
        'risk_index': 'Índice de Riesgo',
        'temperature': 'Temperatura (°C)',
        'relative_humidity': 'Humedad Relativa (%)',
        'solar_radiation': 'Radiación Solar (J/m²)',
        'wind_speed': 'Velocidad de Viento (m/s)'
    }
    return labels.get(variable, 'Variable')


# ---- ENVIRONMENT CONFIGURATION ----
os.environ['HDF5_USE_FILE_LOCKING'] = 'FALSE'

# ---- ANIMATION SESSION STATE ----
if 'playing' not in st.session_state:
    st.session_state.playing = False
if 'animation_speed' not in st.session_state:
    st.session_state.animation_speed = 0.5
if 'loop_animation' not in st.session_state:
    st.session_state.loop_animation = True

def toggle_play():
    """Toggle the play/pause state"""
    st.session_state.playing = not st.session_state.playing

def reset_animation(available, selected_year):
    """Reset to first month"""
    if selected_year in available:
        months_for_year = available[selected_year]
        if "sel_month" in st.session_state:
            st.session_state.sel_month = min(months_for_year)
    st.session_state.playing = False

def next_month_animation(available, selected_year):
    """Advance to next month"""
    if "sel_month" in st.session_state and selected_year in available:
        months_for_year = available[selected_year]
        try:
            current_idx = months_for_year.index(st.session_state.sel_month)
            
            if current_idx < len(months_for_year) - 1:
                st.session_state.sel_month = months_for_year[current_idx + 1]
            elif st.session_state.loop_animation:
                st.session_state.sel_month = months_for_year[0]
            else:
                st.session_state.playing = False
        except ValueError:
            pass

def prev_month_animation(available, selected_year):
    """Go to previous month"""
    if "sel_month" in st.session_state and selected_year in available:
        months_for_year = available[selected_year]
        try:
            current_idx = months_for_year.index(st.session_state.sel_month)
            
            if current_idx > 0:
                st.session_state.sel_month = months_for_year[current_idx - 1]
        except ValueError:
            pass

# ---- PAGE CONFIG & STYLE ----
st.set_page_config(
    page_title="Monitor Riesgo De Incendios Galicia",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    with open("assets/style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

# Single horizontal line header with white text
st.markdown("""
<style>
.horizontal-header {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 0;
    border-bottom: 1px solid #34495e;
    margin-bottom: 1.5rem;
    gap: 1rem;
}
.horizontal-header .title {
    color: #ecf0f1;
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0;
    padding: 0;
}
.horizontal-header .separator {
    color: #7f8c8d;
    font-size: 1.5rem;
}
.horizontal-header .subtitle {
    color: #95a5a6;
    font-size: 0.85rem;
    margin: 0;
}
</style>
<div class="horizontal-header">
    <span class="subtitle">Sistema de Monitoreo de Riesgo de Incendios | Copernicus ERA5</span>
</div>
""", unsafe_allow_html=True)


# ---- IMPORT MODULES ----
try:
    import data_processor as dp
    import risk_calculator as rc
    import map_generator as mg
except ImportError as e:
    st.error(f"❌ Error importando módulos: {e}")
    st.stop()

# ---- CACHED DATA LOADING ----
@st.cache_resource(show_spinner="Cargando datos climaticos...")
def load_cached_data():
    """Load dataset once and cache it across all sessions"""
    try:
        ds = dp.load_data()
        return ds
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return None

# Load data (cached, runs only once)
ds = load_cached_data()

if ds is None:
    st.error("❌ No se pudieron cargar los datos")
    st.info("Por favor, asegúrate de que los archivos NetCDF estén en la carpeta 'data/'")
    st.stop()

# Load fire data
@st.cache_data
def load_fire_data_cached():
    """Cache fire data loading"""
    return dp.load_fire_data()

fires_data = load_fire_data_cached()

# ---- GET AVAILABLE PERIODS ----
try:
    available = dp.get_available_year_months(ds)
    all_years = sorted(available.keys())
    
    if not all_years:
        st.error("No hay datos temporales disponibles en el dataset")
        st.stop()
        
except Exception as e:
    st.error(f"Error extrayendo fechas disponibles: {e}")
    st.stop()

# ---- CALCULATE GLOBAL THRESHOLD (once at startup) ----
@st.cache_data(show_spinner="Calculando umbral global de riesgo...")
def get_global_threshold(_ds, date_key):
    """Calculate global threshold once and cache it"""
    return rc.calculate_global_threshold(_ds, date_key)

# Calculate global threshold
date_key_temp = "time" if "time" in ds.coords else "valid_time"
global_threshold_info = get_global_threshold(ds, date_key_temp)

# ---- MOBILE OPTIMIZATION ----
is_mobile = st.session_state.get('mobile', False)

# ---- SIDEBAR - UPDATED LAYOUT ----

# ---- VARIABLE SELECTION (FIRST) ----
st.sidebar.markdown("---")
st.sidebar.markdown("### Variable a Visualizar")

# Initialize selected variable in session state if not exists
if 'selected_variable' not in st.session_state:
    st.session_state.selected_variable = "risk_index"

# Keep the original simple structure for variable_options
variable_options = {
    "Índice de Riesgo": "risk_index",
    "Temperatura": "temperature",
    "Humedad Relativa": "relative_humidity",
    "Radiación Solar": "solar_radiation",
    "Velocidad de Viento": "wind_speed"
}

# Icons for each variable
variable_icons = {
    "Índice de Riesgo": "🔥",
    "Temperatura": "🌡️",
    "Humedad Relativa": "💧",
    "Radiación Solar": "☀️",
    "Velocidad de Viento": "💨"
}

# Create vertical button tiles
for var_name, var_key in variable_options.items():
    is_selected = st.session_state.selected_variable == var_key
    
    # Use Streamlit's native button with custom styling
    button_type = "primary" if is_selected else "secondary"
    
    # Create custom button label with icon
    button_label = f"{variable_icons[var_name]} {var_name}"
    
    if st.sidebar.button(
        button_label,
        key=f"var_{var_key}",
        use_container_width=True,
        type=button_type
    ):
        st.session_state.selected_variable = var_key
        # st.rerun()

# Get the display name for selected variable (for use in rest of code)
selected_var = [k for k, v in variable_options.items() if v == st.session_state.selected_variable][0]

# ---- YEAR SELECTION ----
st.sidebar.markdown("---")
st.sidebar.markdown("### Seleccionar Período")

# Default to the most recent year with data
latest_year = max(all_years)
selected_year = st.sidebar.selectbox("Año", all_years, index=len(all_years)-1, key="year_select")

# ---- MONTH SELECTION ----
st.sidebar.markdown("---")
st.sidebar.markdown("### Mes")
months_spanish = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
]

# Initialize with latest available month for selected year
if "sel_month" not in st.session_state or "last_year" not in st.session_state or st.session_state["last_year"] != selected_year:
    st.session_state["sel_month"] = max(available[selected_year])
    st.session_state["last_year"] = selected_year

months_for_year = available[selected_year]
num_cols = 3
for i in range(0, len(months_for_year), num_cols):
    cols = st.sidebar.columns(num_cols)
    for j, col in enumerate(cols):
        if i + j < len(months_for_year):
            mon = months_for_year[i + j]
            with col:
                if st.button(
                    months_spanish[mon - 1],
                    key=f"mo_{selected_year}_{mon}",
                    use_container_width=True
                ):
                    st.session_state["sel_month"] = mon
                    st.session_state.playing = False

sel_month = st.session_state["sel_month"]

# Reset to latest available if selected month not in current year
if sel_month not in months_for_year:
    sel_month = max(months_for_year)
    st.session_state["sel_month"] = sel_month

st.sidebar.success(f"✓ {months_spanish[sel_month-1]} {selected_year}")

# ---- ANIMATION CONTROLS ----
st.sidebar.markdown("---")
st.sidebar.markdown("### Controles de Animación")

col_play, col_reset = st.sidebar.columns(2)
with col_play:
    play_icon = "⏸️ Pausar" if st.session_state.playing else "▶️ Reproducir"
    if st.sidebar.button(play_icon, key="play_btn", use_container_width=True):
        toggle_play()

with col_reset:
    if st.sidebar.button("⏮️ Reiniciar", key="reset_btn", use_container_width=True):
        reset_animation(available, selected_year)

col_prev, col_next = st.sidebar.columns(2)
with col_prev:
    if st.sidebar.button("◀️ Anterior", key="prev_btn", use_container_width=True):
        prev_month_animation(available, selected_year)
        st.session_state.playing = False

with col_next:
    if st.sidebar.button("▶️ Siguiente", key="next_btn", use_container_width=True):
        next_month_animation(available, selected_year)
        st.session_state.playing = False

st.session_state.animation_speed = st.sidebar.slider(
    "Velocidad (seg/mes)",
    min_value=0.1,
    max_value=3.0,
    value=st.session_state.animation_speed,
    step=0.1,
    help="Tiempo que se muestra cada mes durante la animación"
)

st.session_state.loop_animation = st.sidebar.checkbox(
    "Repetir animación",
    value=st.session_state.loop_animation,
    help="Volver a empezar automáticamente al llegar al último mes"
)

# ---- GLOBAL THRESHOLD INFO ----
st.sidebar.markdown("---")
if global_threshold_info is not None:
    st.sidebar.info(f"**Umbral Global de Riesgo:** {global_threshold_info['threshold']:.3f}")
else:
    st.sidebar.warning("⚠️ No se pudo calcular umbral global")

# ---- FIND AVAILABLE DATES ----
date_key = "time" if "time" in ds.coords else "valid_time"
candidate_dates = pd.to_datetime(ds[date_key].values)
nearest = candidate_dates[(candidate_dates.year == selected_year) & (candidate_dates.month == sel_month)]

if len(nearest) > 0:
    chosen_date = nearest[0]
else:
    chosen_date = candidate_dates[0]

# ---- FIRE OVERLAY TOGGLE ----
st.sidebar.markdown("---")
st.sidebar.markdown("### Incendios Históricos")
show_fires = st.sidebar.checkbox(
    "Mostrar incendios > 10ha (2017-2023)",
    value=True,
    help="Muestra ubicación de incendios históricos con datos meteorológicos del día"
)

# ---- DATA SLICE (with caching) ----
@st.cache_data(show_spinner=False)
def get_processed_data(_ds, date, date_key):
    """Cache processed data for each date"""
    data_slice = _ds.sel({date_key: date}, method='nearest')
    risk_data = rc.calculate_risk_index(data_slice)
    return data_slice, risk_data

try:
    data_slice, risk_data = get_processed_data(ds, chosen_date, date_key)
except Exception as e:
    st.error(f"Error procesando datos: {e}")
    with st.expander("Ver detalles"):
        import traceback
        st.code(traceback.format_exc())
    st.stop()

# ---- MAIN LAYOUT - ADJUSTED FOR 16:9 ----
col1, col2 = st.columns([1, 3])

with col1:
    try:
        # Calculate alerts with GLOBAL threshold
        alerts = rc.calculate_alerts(risk_data, global_threshold_info)
        
        # Centered statistics without title
        st.markdown("""
        <style>
        .centered-metrics {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Use centered container
        col_center = st.columns([0.1, 1, 0.1])[1]
        with col_center:
            st.metric("🌡️ Temp Media", f"{alerts['avg_temp']:.1f}°C")
            st.metric("💧 Humedad Media", f"{alerts['avg_humidity']:.1f}%")
            st.metric("🔥 Riesgo Medio", f"{alerts['avg_risk']:.2f}")
            st.metric("💨 Vel. Viento Medio", f"{alerts['avg_wind']:.1f} m/s")
        
        st.markdown("---")
        st.markdown("### ⚠️ Alertas por Región")
        
        # Get high-risk regions (with land-sea mask filtering)
        high_risk_regions = rc.identify_high_risk_regions(risk_data, alerts, data_slice)
        
        if len(high_risk_regions) > 0:
            st.error(f"🔴 **{len(high_risk_regions)} zonas** con riesgo alto detectadas")
            
            st.info(f"**Umbral Global:** {alerts['risk_threshold']:.3f} (μ + σ)")
            
            # Show top 5 regions in expander
            with st.expander(f"Ver detalles de zonas de riesgo ({len(high_risk_regions)} total)", expanded=False):
                for idx, region in enumerate(high_risk_regions[:5], 1):
                    st.markdown(f"""
                    **Zona {idx}** - Riesgo: **{region['risk']:.2f}** ({region['z_score']:.1f}σ)
                    - 📍 Lat: {region['lat']:.2f}°, Lon: {region['lon']:.2f}°
                    - 🌡️ Temp: {region['temperature']:.1f}°C
                    - 💧 Humedad: {region['humidity']:.1f}%
                    - 💨 Viento: {region['wind_speed']:.1f} m/s
                    """)
                    if idx < 5:
                        st.markdown("---")
        else:
            st.success(f"""
            **✅ No hay alertas activas**
            
            **Condiciones generales:**
            
            • Temp media: **{alerts['avg_temp']:.1f}°C**
            
            • Humedad media: **{alerts['avg_humidity']:.1f}%**
            
            • Vel. viento: **{alerts['avg_wind']:.1f} m/s**
            
            • Riesgo medio: **{alerts['avg_risk']:.2f}**
            
            • Umbral global: **{alerts['risk_threshold']:.2f}**
            """)
            
    except Exception as e:
        st.error(f"Error calculando alertas: {e}")
        import traceback
        st.code(traceback.format_exc())

with col2:
    st.markdown(f"### Mapa Interactivo de Galicia | {selected_var} - {sel_month}/{selected_year}")
    try:
        map_height = 450 if is_mobile else 550
        
        # Create sub-columns for map and colorbar
        map_col, colorbar_col = st.columns([5, 1])
        
        with map_col:
            m = mg.create_interactive_map(
                risk_data,
                data_slice,
                variable=variable_options[selected_var],
                date=chosen_date,
                show_fires=show_fires,
                fires_data=fires_data,
                dataset=ds,
                date_key=date_key
            )
            
            # Add high-risk region markers (with land-sea mask filtering)
            high_risk_regions = rc.identify_high_risk_regions(risk_data, alerts, data_slice)
            if hasattr(mg, 'add_risk_markers'):
                m = mg.add_risk_markers(m, high_risk_regions)
            
            st_folium(m, width=None, height=map_height)
        
        with colorbar_col:
            # Get colorbar data based on variable
            if variable_options[selected_var] == 'risk_index':
                data_for_colorbar = risk_data['risk']
                cmap_name = 'YlOrRd'
                unit = ''
            elif variable_options[selected_var] == 'temperature':
                data_for_colorbar = risk_data['temperature']
                cmap_name = 'RdYlBu_r'
                unit = '°C'
            elif variable_options[selected_var] == 'relative_humidity':
                data_for_colorbar = risk_data['relative_humidity']
                cmap_name = 'Blues'
                unit = '%'
            elif variable_options[selected_var] == 'solar_radiation':
                if 'ssrd' in data_slice.data_vars:
                    data_for_colorbar = data_slice['ssrd'] / 1e6
                else:
                    data_for_colorbar = risk_data['temperature']
                cmap_name = 'YlOrRd'
                unit = 'J/m²'
            elif variable_options[selected_var] == 'wind_speed':
                data_for_colorbar = risk_data['wind_speed']
                cmap_name = 'viridis'
                unit = 'm/s'
            else:
                data_for_colorbar = risk_data['risk']
                cmap_name = 'YlOrRd'
                unit = ''
            
            # Calculate value range
            values = data_for_colorbar.values
            valid_data = values[~np.isnan(values)]
            
            if len(valid_data) > 0:
                if variable_options[selected_var] == 'solar_radiation':
                    vmin = float(np.nanmin(valid_data))
                    vmax = float(np.nanmax(valid_data))
                else:
                    vmin = float(np.percentile(valid_data, 2))
                    vmax = float(np.percentile(valid_data, 98))
                
                # Ensure vmin < vmax
                if vmin >= vmax:
                    vmin = float(np.nanmin(valid_data))
                    vmax = float(np.nanmax(valid_data))
                    if vmin >= vmax:
                        vmax = vmin + 0.01
                
                # Create colorbar
                from matplotlib import cm as mpl_cm
                from matplotlib import colors as mpl_colors
                import matplotlib.pyplot as plt
                import matplotlib.ticker as ticker
                
                cmap = mpl_cm.get_cmap(cmap_name)
                norm = mpl_colors.Normalize(vmin=vmin, vmax=vmax)
                
                # Fixed dimensions
                fig_width = 0.4
                fig_height = 2.8
                
                # Create figure
                fig = plt.figure(figsize=(fig_width, fig_height), dpi=100)
                fig.patch.set_facecolor('#262730')
                
                # Create axes
                ax = fig.add_axes([0.3, 0.05, 0.3, 0.9])
                
                # Create colorbar
                cb = plt.colorbar(
                    mpl_cm.ScalarMappable(norm=norm, cmap=cmap),
                    cax=ax,
                    orientation='vertical'
                )
                
                cb.set_label(unit, fontsize=8, color='#ecf0f1')
                
                # Create custom tick formatter to add units
                def format_func(value, pos):
                    if unit:
                        return f'{value:.1f}{unit}'
                    else:
                        return f'{value:.2f}'
                
                cb.ax.yaxis.set_major_formatter(ticker.FuncFormatter(format_func))
                
                # Style ticks
                cb.ax.yaxis.set_ticks_position('right')
                cb.ax.yaxis.set_label_position('right')
                cb.ax.tick_params(labelsize=7, colors='#ecf0f1', length=3, width=1)
                cb.outline.set_edgecolor('#ecf0f1')
                cb.outline.set_linewidth(1.5)
                
                # Set number of ticks
                cb.locator = ticker.MaxNLocator(nbins=8)
                cb.update_ticks()
                
                # Display
                st.pyplot(fig, use_container_width=False)
                plt.close()

            
    except Exception as e:
        st.error(f"Error generando mapa: {e}")
        with st.expander("Ver detalles"):
            import traceback
            st.code(traceback.format_exc())


# ---- TEMPORAL EVOLUTION ----
st.markdown("---")
st.markdown(f"### Evolución Mensual {selected_year} - {selected_var}")

@st.cache_data(show_spinner="Generando gráfico...")
def get_yearly_trend(_ds, variable, year, date_key):
    """Cache yearly trend calculation"""
    return dp.calculate_yearly_trend(_ds, variable, year, date_key=date_key)

@st.cache_data(show_spinner=False)
def get_historical_average(_ds, variable, date_key):
    """Cache historical average calculation"""
    return dp.calculate_historical_average(_ds, variable, 2017, 2024, date_key=date_key)

try:
    trend_var = variable_options[selected_var]
    temporal_data = get_yearly_trend(ds, trend_var, selected_year, date_key)
    historical_avg = get_historical_average(ds, trend_var, date_key)
    
    if len(temporal_data['values']) > 0:
        # Month names in Spanish for x-axis
        month_names = [
            "Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
        ]
        
        # Create x-axis labels for current year
        x_labels = [month_names[m-1] for m in temporal_data['months']]
        
        # Prepare historical average data (all 12 months)
        hist_months = list(range(1, 13))
        hist_values = [historical_avg.get(m, np.nan) for m in hist_months]
        hist_labels = month_names
        
        # Get unit label for y-axis
        unit_labels = {
            'risk_index': 'Índice (0-1)',
            'temperature': 'Temperatura (°C)',
            'relative_humidity': 'Humedad (%)',
            'solar_radiation': 'Radiación (J/m²)',
            'wind_speed': 'Velocidad (m/s)'
        }
        y_label = unit_labels.get(trend_var, selected_var)
        
        fig = go.Figure()
        
        # Add historical average line (gray, dashed)
        fig.add_trace(go.Scatter(
            x=hist_labels,
            y=hist_values,
            mode='lines',
            name='Promedio 2017-2024',
            line=dict(
                color='rgba(150, 150, 150, 0.6)',
                width=3,
                dash='dash',
                shape='spline',
                smoothing=1.3
            ),
            hovertemplate='<b>Promedio histórico</b><br>%{y:.2f}<extra></extra>'
        ))
        
        # Add current year line (red, prominent)
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=temporal_data['values'],
            mode='lines+markers',
            name=f'{selected_year}',
            line=dict(
                color='#e74c3c',
                width=4,
                shape='spline',
                smoothing=1.3
            ),
            marker=dict(
                size=10 if not is_mobile else 8,
                color='#e74c3c',
                symbol='circle',
                line=dict(color='white', width=2)
            ),
            fill='tozeroy',
            fillcolor='rgba(231, 76, 60, 0.1)',
            hovertemplate='<b>%{x}</b><br>%{y:.2f}<extra></extra>'
        ))
        
        # Highlight current month with a star marker
        try:
            current_month_idx = temporal_data['months'].index(sel_month)
            current_month_value = temporal_data['values'][current_month_idx]
            current_month_label = month_names[sel_month - 1]
            
            fig.add_trace(go.Scatter(
                x=[current_month_label],
                y=[current_month_value],
                mode='markers',
                name='Mes actual',
                marker=dict(
                    size=20,
                    color='gold',
                    symbol='star',
                    line=dict(color='white', width=2)
                ),
                hovertemplate=f'<b>Mes actual: {current_month_label}</b><br>%{{y:.2f}}<extra></extra>'
            ))
        except (ValueError, IndexError):
            pass
        
        fig.update_layout(
            title=dict(
                text=f"Variación Mensual - {selected_var} ({selected_year})",
                font=dict(size=18, color='#fafafa')
            ),
            xaxis_title="Mes",
            yaxis_title=y_label,
            template="plotly_dark",
            paper_bgcolor='#262730',
            plot_bgcolor='#1a1a1a',
            height=300,
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor='rgba(0,0,0,0.3)',
                font=dict(color='#fafafa')
            ),
            font=dict(color='#fafafa'),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)',
                zeroline=False
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)',
                zeroline=False
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No hay datos disponibles para {selected_year}")
    
except Exception as e:
    st.error(f"Error generando gráfico temporal: {e}")
    with st.expander("Ver detalles"):
        import traceback
        st.code(traceback.format_exc())

# ---- DATA UPDATE SECTION ----
st.markdown("---")
st.markdown("### Actualizar Datos")

st.markdown("""
<div style="background-color: rgba(243, 156, 18, 0.15); padding: 15px; border-radius: 8px; 
            border-left: 4px solid #f39c12; margin-bottom: 15px;">
    <div style="color: #f39c12; font-size: 0.95rem;">
        <p style="margin: 0;">
            <b>⚠️ Advertencia:</b><br>
            La actualización de datos puede tardar entre <b>10-20 minutos</b> dependiendo de:
        </p>
        <ul style="margin: 8px 0 0 20px;">
            <li>Velocidad de conexión a Internet</li>
            <li>Disponibilidad de servidores de Copernicus CDS</li>
            <li>Cantidad de datos nuevos a descargar</li>
        </ul>
    </div>
</div>
""", unsafe_allow_html=True)

st.info("💡 Se descargarán los datos climáticos más recientes desde el servidor de Copernicus Climate Data Store.")

if st.button("Iniciar Actualización", type="primary", use_container_width=True):
    st.session_state['updating'] = True

if st.session_state.get('updating', False):
    st.markdown("---")
    st.markdown("#### Actualizando Datos...")
    
    progress_text = st.empty()
    progress_bar = st.progress(0)
    status_message = st.empty()
    
    try:
        import subprocess
        
        progress_text.text("🔍 Verificando script de actualización...")
        progress_bar.progress(10)
        time.sleep(0.5)
        
        update_script = "downloader.py"
        if not os.path.exists(update_script):
            status_message.error(f"❌ Error: No se encontró el script '{update_script}'")
            st.session_state['updating'] = False
            st.stop()
        
        progress_text.text("📡 Conectando con Copernicus CDS...")
        progress_bar.progress(20)
        status_message.info("Iniciando descarga de datos ERA5...")
        
        process = subprocess.Popen(
            ['python', update_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        steps = [
            (30, "Descargando 30/100.."),
            (40, "Descargando 40/100.."),
            (50, "Descargando 50/100.."),
            (60, "Descargando 60/100.."),
            (70, "Descargando 70/100.."),
            (80, "Descargando 80/100.."),
            (90, "Guardando en formato NetCDF..."),
        ]
        
        for progress, message in steps:
            if process.poll() is None:
                progress_bar.progress(progress)
                status_message.info(message)
                time.sleep(5)
            else:
                break
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            progress_bar.progress(100)
            progress_text.text("✅ Actualización completada")
            status_message.success("¡Datos actualizados correctamente! Recargando la aplicación...")
            time.sleep(2)
            st.session_state['updating'] = False
            st.rerun()
        else:
            status_message.error(f"❌ Error durante la actualización:\n{stderr}")
            with st.expander("Ver detalles del error"):
                st.code(stderr)
            st.session_state['updating'] = False
            
    except Exception as e:
        status_message.error(f"❌ Error inesperado: {e}")
        with st.expander("Ver detalles"):
            import traceback
            st.code(traceback.format_exc())
        st.session_state['updating'] = False

# ---- FOOTER ----
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 20px;">
    <div style="margin-bottom: 15px;">
        <p style="margin: 5px 0; font-size: 14px; opacity: 0.8;">
            <b>Datos:</b> 
            <a href="https://cds.climate.copernicus.eu/" target="_blank" style="color: #3498db;">
                Copernicus ERA5 Monthly Means
            </a> | 
            <a href="https://www.openstreetmap.org/" target="_blank" style="color: #3498db;">
                OpenStreetMap
            </a>
        </p>
        <p style="margin: 5px 0; font-size: 14px; opacity: 0.8;">
            <b>Tecnologías:</b> Python, Streamlit, Folium, xarray, Plotly
        </p>
        <p style="margin: 5px 0; font-size: 14px; opacity: 0.8;">
            Desarrollado para Hackaton CoAfina 2025
        </p>
    </div>
    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
        <p style="margin: 5px 0; font-size: 13px; opacity: 0.7;">
            Licencia: 
            <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" style="color: #3498db;">
                CC BY 4.0
            </a>
        </p>
        <p style="margin: 5px 0; font-size: 12px; opacity: 0.6;">
            Este trabajo está licenciado bajo Creative Commons Attribution 4.0 International
        </p>
    </div>
</div>
""", unsafe_allow_html=True)

# ---- ANIMATION LOOP (must be at the very end) ----
if st.session_state.playing:
    time.sleep(st.session_state.animation_speed)
    next_month_animation(available, selected_year)
    st.rerun()
