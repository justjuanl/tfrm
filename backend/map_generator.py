import folium
from folium import plugins
import numpy as np
from matplotlib import cm, colors
from scipy.ndimage import zoom
from branca.colormap import LinearColormap


def get_color(value, variable='risk_index'):
    """Return color based on value and variable type"""
    if variable == 'risk_index':
        if value < 0.3:
            return '#2ecc71'
        elif value < 0.6:
            return '#f39c12'
        else:
            return '#e74c3c'
    elif variable == 'temperature':
        if value < 20:
            return '#3498db'
        elif value < 30:
            return '#f39c12'
        else:
            return '#e74c3c'
    else:
        return '#95a5a6'


def get_colormap_for_variable(variable):
    """Return appropriate matplotlib colormap for each variable"""
    colormaps = {
        'risk_index': 'YlOrRd',
        'temperature': 'RdYlBu_r',
        'relative_humidity': 'Blues',
        'solar_radiation': 'YlOrRd',
        'wind_speed': 'viridis'
    }
    return colormaps.get(variable, 'coolwarm')


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


def create_interactive_map(risk_data, data_slice, variable='risk_index', date=None, 
                          show_fires=False, fires_data=None, dataset=None, date_key='time'):
    """Create interactive Folium map with smooth heatmap overlay"""
    
    # Center on Galicia
    center_lat, center_lon = 42.88, -8.0
    
    # Create map with zoom constraints
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        min_zoom=7,
        max_zoom=12,
        tiles='CartoDB Positron',
        max_bounds=True
    )
    
    # Get data to display based on variable
    if variable == 'risk_index':
        data_to_plot = risk_data['risk']
        colormap_name = 'YlOrRd'
    elif variable == 'temperature':
        data_to_plot = risk_data['temperature']
        colormap_name = 'RdYlBu_r'
    elif variable == 'relative_humidity':
        data_to_plot = risk_data['relative_humidity']
        colormap_name = 'Blues'
    elif variable == 'solar_radiation':
        # Try multiple sources with validation
        data_to_plot = None
        
        # Option 1: ssrd from data_slice
        if 'ssrd' in data_slice.data_vars:
            temp_data = data_slice['ssrd'].values
            if not np.all(np.isnan(temp_data)):
                data_to_plot = data_slice['ssrd']
        
        # Option 2: avg_sdswrf as fallback
        if data_to_plot is None and 'avg_sdswrf' in data_slice.data_vars:
            temp_data = data_slice['avg_sdswrf'].values
            if not np.all(np.isnan(temp_data)):
                data_to_plot = data_slice['avg_sdswrf']
        
        # Option 3: from risk_data
        if data_to_plot is None and risk_data.get('solar_radiation') is not None:
            data_to_plot = risk_data['solar_radiation']
        
        # Final fallback
        if data_to_plot is None:
            data_to_plot = risk_data['temperature']
        
        colormap_name = 'YlOrRd'
    elif variable == 'wind_speed':
        data_to_plot = risk_data['wind_speed']
        colormap_name = 'viridis'
    else:
        data_to_plot = risk_data['risk']
        colormap_name = 'YlOrRd'
    
    # Initialize colorbar_html
    colorbar_html = ""
    
    try:
        # Extract data values
        data_values = data_to_plot.values
        
        # Check if data is valid
        if data_values is None or len(data_values) == 0:
            return m
        
        # Calculate NaN percentage
        nan_percentage = np.sum(np.isnan(data_values)) / data_values.size * 100
        
        # Check if ALL values are NaN
        if np.all(np.isnan(data_values)):
            html_msg = f"""
            <div style="position: fixed; top: 100px; left: 50%; transform: translateX(-50%); 
                        background: white; padding: 20px; border-radius: 10px; 
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2); z-index: 1000; max-width: 400px;">
                <h4 style="margin:0; color: #e74c3c;">⚠️ Sin Datos Disponibles</h4>
                <p style="margin: 10px 0 0 0;">No hay datos de {get_variable_label(variable).lower()} para esta fecha específica.</p>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">
                    Intenta seleccionar otro mes. El gráfico temporal muestra meses con datos disponibles.
                </p>
            </div>
            """
            m.get_root().html.add_child(folium.Element(html_msg))
            return m
        
        # Get coordinate bounds
        lat_min = float(data_to_plot.latitude.min().values)
        lat_max = float(data_to_plot.latitude.max().values)
        lon_min = float(data_to_plot.longitude.min().values)
        lon_max = float(data_to_plot.longitude.max().values)
        
        # Set map bounds to data extent
        m.fit_bounds([[lat_min, lon_min], [lat_max, lon_max]])
        
        # Interpolate for smoother heatmap
        zoom_factor = 5
        data_upsampled = zoom(data_values, (zoom_factor, zoom_factor), order=1)
        
        # Check valid data percentage after interpolation
        valid_percentage = np.sum(~np.isnan(data_upsampled)) / data_upsampled.size * 100
        
        if valid_percentage < 10:
            html_msg = f"""
            <div style="position: fixed; top: 100px; left: 50%; transform: translateX(-50%); 
                        background: white; padding: 20px; border-radius: 10px; 
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2); z-index: 1000; max-width: 400px;">
                <h4 style="margin:0; color: #f39c12;">⚠️ Datos Insuficientes</h4>
                <p style="margin: 10px 0 0 0;">Solo {valid_percentage:.1f}% de los datos están disponibles para esta fecha.</p>
                <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">
                    Selecciona otro mes para ver más datos.
                </p>
            </div>
            """
            m.get_root().html.add_child(folium.Element(html_msg))
            return m
        
        # Normalize values
        if variable == 'solar_radiation':
            vmin = float(np.nanmin(data_upsampled))
            vmax = float(np.nanmax(data_upsampled))
        else:
            valid_data = data_upsampled[~np.isnan(data_upsampled)]
            vmin = float(np.percentile(valid_data, 2))
            vmax = float(np.percentile(valid_data, 98))
        
        # Ensure vmin < vmax
        if np.isnan(vmin) or np.isnan(vmax) or vmin >= vmax:
            vmin = float(np.nanmin(data_upsampled))
            vmax = float(np.nanmax(data_upsampled))
            if np.isnan(vmin) or np.isnan(vmax) or vmin >= vmax:
                vmax = vmin + 0.01 if not np.isnan(vmin) else 1.0
                vmin = 0.0 if np.isnan(vmin) else vmin
        
        if not (vmin < vmax):
            vmin = 0.0
            vmax = 1.0
        
        norm = colors.Normalize(vmin=vmin, vmax=vmax)
        
        # Apply colormap
        cmap = cm.get_cmap(colormap_name)
        data_normalized = np.nan_to_num(data_upsampled, nan=vmin)
        rgba_array = (cmap(norm(data_normalized)) * 255).astype(np.uint8)
        
        # Add ImageOverlay
        bounds = [[lat_min, lon_min], [lat_max, lon_max]]
        folium.raster_layers.ImageOverlay(
            image=rgba_array,
            bounds=bounds,
            opacity=0.65,
            interactive=True,
            name='Heatmap'
        ).add_to(m)
        
        # Add warning if significant data is missing
        if nan_percentage > 30:
            html_msg = f"""
            <div style="position: fixed; top: 100px; right: 20px; 
                        background: #fff3cd; padding: 15px; border-radius: 8px; 
                        border-left: 4px solid #ffc107; box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                        z-index: 1000; max-width: 280px;">
                <h4 style="margin:0; color: #856404; font-size: 14px;">⚠️ Datos Parciales</h4>
                <p style="margin: 8px 0 0 0; font-size: 13px; color: #856404;">
                    {nan_percentage:.0f}% de los datos no están disponibles.
                </p>
            </div>
            """
            m.get_root().html.add_child(folium.Element(html_msg))
        
        # # Add default LinearColormap colorbar
        # colorbar_values = np.linspace(vmin, vmax, 10)
        # colorbar_colors = [cmap(norm(val)) for val in colorbar_values]
        
        # linear_colormap = LinearColormap(
        #     colors=colorbar_colors,
        #     index=colorbar_values.tolist(),
        #     vmin=vmin,
        #     vmax=vmax,
        #     caption=get_variable_label(variable)
        # )
        # linear_colormap.add_to(m)
        
        # Add marker points
        for i, lat in enumerate(data_to_plot.latitude.values[::2]):
            for j, lon in enumerate(data_to_plot.longitude.values[::2]):
                try:
                    val = float(data_to_plot.sel(latitude=lat, longitude=lon, method='nearest').values)
                    risk_val = float(risk_data['risk'].sel(latitude=lat, longitude=lon, method='nearest').values)
                    temp_val = float(risk_data['temperature'].sel(latitude=lat, longitude=lon, method='nearest').values)
                    rh_val = float(risk_data['relative_humidity'].sel(latitude=lat, longitude=lon, method='nearest').values)
                    
                    if not np.isnan(val):
                        popup_html = f"""
                        <div style="font-family: Arial; width: 220px;">
                            <h4 style="margin:0; color: #2c3e50;">📍 Punto de Medición</h4>
                            <hr style="margin: 5px 0;">
                            <b>Coordenadas:</b> {lat:.2f}, {lon:.2f}<br>
                            <b style="color: {get_color(risk_val)};">🔥 Riesgo:</b> {risk_val:.2f}<br>
                            <b>🌡️ Temperatura:</b> {temp_val:.1f}°C<br>
                            <b>💧 Humedad:</b> {rh_val:.1f}%<br>
                        </div>
                        """
                        
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=5,
                            popup=folium.Popup(popup_html, max_width=250),
                            color='white',
                            fill=True,
                            fillColor=get_color(val, variable),
                            fillOpacity=0.8,
                            weight=1
                        ).add_to(m)
                except:
                    pass
        
        # Add wind arrows
        if variable == 'wind_speed':
            for lat in data_to_plot.latitude.values[::2]:
                for lon in data_to_plot.longitude.values[::2]:
                    try:
                        u = float(risk_data['wind_u'].sel(latitude=lat, longitude=lon, method='nearest').values)
                        v = float(risk_data['wind_v'].sel(latitude=lat, longitude=lon, method='nearest').values)
                        
                        if not (np.isnan(u) or np.isnan(v)):
                            magnitude = np.sqrt(u**2 + v**2)
                            arrow_length = 0.06 * (1 + magnitude / 10)
                            
                            end_lat = lat + v * arrow_length
                            end_lon = lon + u * arrow_length
                            
                            folium.PolyLine(
                                locations=[[lat, lon], [end_lat, end_lon]],
                                color='#FF6B35',
                                weight=4,
                                opacity=0.9
                            ).add_to(m)
                            
                            angle = np.arctan2(v, u)
                            arrow_angle = 30 * np.pi / 180
                            arrow_size = arrow_length * 0.3
                            
                            left_lat = end_lat - arrow_size * np.sin(angle + arrow_angle)
                            left_lon = end_lon - arrow_size * np.cos(angle + arrow_angle)
                            
                            right_lat = end_lat - arrow_size * np.sin(angle - arrow_angle)
                            right_lon = end_lon - arrow_size * np.cos(angle - arrow_angle)
                            
                            folium.PolyLine(
                                locations=[[end_lat, end_lon], [left_lat, left_lon]],
                                color='#FF6B35',
                                weight=4,
                                opacity=0.9
                            ).add_to(m)
                            
                            folium.PolyLine(
                                locations=[[end_lat, end_lon], [right_lat, right_lon]],
                                color='#FF6B35',
                                weight=4,
                                opacity=0.9
                            ).add_to(m)
                    except:
                        pass
        # Add fire markers if enabled - FILTER BY SELECTED MONTH/YEAR
        if show_fires and fires_data is not None and len(fires_data) > 0 and date is not None:
            # Extract year and month from selected date
            selected_year = date.year
            selected_month = date.month
            
            # Filter fires for selected month and year
            fires_filtered = fires_data[
                (fires_data['fecha'].dt.year == selected_year) &
                (fires_data['fecha'].dt.month == selected_month)
            ]
            
            print(f"DEBUG: Showing {len(fires_filtered)} fires for {selected_year}-{selected_month:02d}")
            
            for idx, fire in fires_filtered.iterrows():
                try:
                    fire_lat = fire['lat']
                    fire_lng = fire['lng']
                    fire_date = fire['fecha']
                    fire_size = fire['superficie']
                    
                    # Scale marker size and opacity based on fire size
                    radius = min(8 + (fire_size / 10), 25)
                    opacity = min(0.4 + (fire_size / 200), 0.9)
                    
                    # Try to get weather data for the fire date
                    weather_info = ""
                    if dataset is not None:
                        try:
                            fire_data_slice = dataset.sel({date_key: fire_date}, method='nearest', tolerance='30D')
                            
                            # Get weather data at fire location
                            fire_temp = float(fire_data_slice['t2m'].sel(
                                latitude=fire_lat, longitude=fire_lng, method='nearest'
                            ).values) - 273.15
                            
                            fire_u = float(fire_data_slice['u10'].sel(
                                latitude=fire_lat, longitude=fire_lng, method='nearest'
                            ).values)
                            fire_v = float(fire_data_slice['v10'].sel(
                                latitude=fire_lat, longitude=fire_lng, method='nearest'
                            ).values)
                            fire_wind = np.sqrt(fire_u**2 + fire_v**2)
                            
                            fire_d2m = float(fire_data_slice['d2m'].sel(
                                latitude=fire_lat, longitude=fire_lng, method='nearest'
                            ).values)
                            
                            # Calculate relative humidity
                            t_c = fire_temp
                            d_c = fire_d2m - 273.15
                            fire_rh = 100 * (np.exp((17.625 * d_c) / (243.04 + d_c)) / 
                                           np.exp((17.625 * t_c) / (243.04 + t_c)))
                            fire_rh = np.clip(fire_rh, 0, 100)
                            
                            weather_info = f"""
                            <hr style="margin: 8px 0;">
                            <b>📊 Datos Meteorológicos ({fire_date.strftime('%Y-%m-%d')})</b><br>
                            <b>🌡️ Temperatura:</b> {fire_temp:.1f}°C<br>
                            <b>💧 Humedad:</b> {fire_rh:.1f}%<br>
                            <b>💨 Viento:</b> {fire_wind:.1f} m/s
                            """
                        except Exception as weather_error:
                            weather_info = f"<hr><small>Datos meteorológicos no disponibles</small>"
                    
                    # Create popup with fire info
                    popup_html = f"""
                    <div style="font-family: Arial; width: 250px;">
                        <h4 style="margin:0; color: #e74c3c;">🔥 Incendio Histórico</h4>
                        <hr style="margin: 5px 0;">
                        <b>📅 Fecha:</b> {fire_date.strftime('%d/%m/%Y')}<br>
                        <b>📍 Ubicación:</b> {fire_lat:.3f}, {fire_lng:.3f}<br>
                        <b>🌲 Superficie quemada:</b> {fire_size:.1f} ha
                        {weather_info}
                    </div>
                    """
                    
                    # Add fire marker with pulsing effect
                    folium.CircleMarker(
                        location=[fire_lat, fire_lng],
                        radius=radius,
                        popup=folium.Popup(popup_html, max_width=280),
                        tooltip=f"🔥 {fire_size:.0f}ha - {fire_date.strftime('%d/%m/%Y')}",
                        color='#d63031',
                        fill=True,
                        fillColor='#ff7675',
                        fillOpacity=opacity,
                        weight=2
                    ).add_to(m)
                    
                except Exception as fire_error:
                    print(f"Error adding fire marker: {fire_error}")
                    pass
            
            # Add info message if fires shown
            if len(fires_filtered) > 0:
                fires_info_html = f"""
                <div style="position: fixed; 
                            top: 60px; 
                            left: 50%; 
                            transform: translateX(-50%);
                            z-index: 1000;
                            background: rgba(214, 48, 49, 0.9);
                            color: white;
                            padding: 8px 15px;
                            border-radius: 20px;
                            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                            font-size: 13px;
                            font-weight: 600;">
                    🔥 {len(fires_filtered)} incendio(s) en {selected_year}-{selected_month:02d}
                </div>
                """
                m.get_root().html.add_child(folium.Element(fires_info_html))

    except Exception as e:
        print(f"ERROR creating heatmap overlay: {e}")
        import traceback
        traceback.print_exc()
    
    # Legend - bottom right
    legend_html = '''

    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; 
                background-color: white; border:2px solid grey; 
                z-index:9999; font-size:14px; padding: 15px; 
                border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <p style="margin:0; font-weight:bold; font-size: 16px;">🔥 Nivel de Riesgo</p>
    <hr style="margin: 8px 0;">
    <p style="margin:5px 0;"><span style="color:#2ecc71; font-size:20px;">●</span> Bajo (&lt; 0.3)</p>
    <p style="margin:5px 0;"><span style="color:#f39c12; font-size:20px;">●</span> Medio (0.3-0.6)</p>
    <p style="margin:5px 0;"><span style="color:#e74c3c; font-size:20px;">●</span> Alto (&gt; 0.6)</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

def add_risk_markers(folium_map, high_risk_regions):
    """
    Add fire warning markers for high-risk regions
    
    Parameters:
    -----------
    folium_map : folium.Map
        The map to add markers to
    high_risk_regions : list
        List of high-risk regions from identify_high_risk_regions()
    """
    import folium
    
    for region in high_risk_regions:
        # Create popup with detailed info
        popup_html = f"""
        <div style="font-family: Arial; width: 200px;">
            <h4 style="color: #e74c3c; margin: 0;">⚠️ Riesgo Crítico</h4>
            <hr style="margin: 5px 0;">
            <p style="margin: 5px 0;"><b>Índice:</b> {region['risk']:.2f}</p>
            <p style="margin: 5px 0;"><b>Temp:</b> {region['temperature']:.1f}°C</p>
            <p style="margin: 5px 0;"><b>Humedad:</b> {region['humidity']:.1f}%</p>
            <p style="margin: 5px 0;"><b>Viento:</b> {region['wind_speed']:.1f} m/s</p>
        </div>
        """
        
        # Add fire marker
        folium.Marker(
            location=[region['lat'], region['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"🔥 Riesgo: {region['risk']:.2f}",
            icon=folium.Icon(
                color='red',
                icon='fire',
                prefix='fa'  # Font Awesome
            )
        ).add_to(folium_map)
    
    return folium_map
