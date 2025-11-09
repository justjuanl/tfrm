import numpy as np
import data_processor as dp

def calculate_global_threshold(dataset, date_key='time'):
    """
    Calculate a single global threshold (mean + std) across entire dataset
    This threshold will be consistent across all months
    
    Parameters:
    -----------
    dataset : xarray.Dataset
        Full dataset with all time periods
    date_key : str
        Name of the time dimension ('time' or 'valid_time')
    
    Returns:
    --------
    dict
        Contains global mean, std, and threshold
    """
    print(f"Calculating global risk threshold across all {len(dataset[date_key])} time steps...")
    
    all_risk_values = []
    
    # Calculate risk for all time steps
    for time_idx in range(len(dataset[date_key])):
        try:
            data_slice = dataset.isel({date_key: time_idx})
            risk_data = calculate_risk_index(data_slice)
            
            risk_values = risk_data['risk'].values
            valid_risk = risk_values[~np.isnan(risk_values)]
            all_risk_values.extend(valid_risk.flatten())
            
        except Exception as e:
            print(f"Warning: Could not process time step {time_idx}: {e}")
            continue
    
    if len(all_risk_values) == 0:
        print("ERROR: No risk data collected for global threshold")
        return None
    
    # Calculate global statistics
    all_risk_array = np.array(all_risk_values)
    
    global_mean = float(np.mean(all_risk_array))
    global_std = float(np.std(all_risk_array))
    global_threshold = global_mean + global_std
    
    threshold_info = {
        'mean': global_mean,
        'std': global_std,
        'threshold': global_threshold,
        'median': float(np.median(all_risk_array)),
        'p84': float(np.percentile(all_risk_array, 84)),
        'p95': float(np.percentile(all_risk_array, 95)),
        'count': len(all_risk_array)
    }
    
    print(f"Global threshold calculated:")
    print(f"  Mean: {global_mean:.4f}")
    print(f"  Std:  {global_std:.4f}")
    print(f"  Threshold (μ + σ): {global_threshold:.4f}")
    
    return threshold_info


def calculate_risk_index(data):
    """
    Calculate fire risk index from multiple variables
    Higher values = higher fire risk
    Uses proper min-max normalization per month
    """
    # Extract variables
    t2m = data['t2m']  # Temperature
    u10 = data['u10']  # Wind U component
    v10 = data['v10']  # Wind V component
    d2m = data['d2m']  # Dewpoint temperature
    swvl1 = data['swvl1']  # Soil moisture layer 1
    
    # Calculate derived variables
    ws = dp.calculate_wind_speed(u10, v10)
    rh = dp.calculate_relative_humidity(t2m, d2m)
    
    # Convert temperature to Celsius
    temp_c = t2m - 273.15
    
    # Normalize variables using min-max normalization [0, 1]
    # Temperature: 0-40°C range
    t_norm = np.clip((temp_c - 0) / (40 - 0), 0, 1)
    
    # Wind speed: 0-15 m/s range
    ws_norm = np.clip(ws / 15, 0, 1)
    
    # Relative humidity: 0-100% (invert because LOW humidity = HIGH risk)
    rh_norm = np.clip(1 - (rh / 100), 0, 1)
    
    # Calculate weighted risk index
    # Weights: Temperature (34%), Wind (33%), Humidity (33%)
    risk = (
        0.34 * t_norm +
        0.33 * ws_norm +
        0.33 * rh_norm
    )
    
    # Extract solar radiation if available
    solar_rad = None
    if 'ssrd' in data:
        solar_rad = data['ssrd'] / 1e6  # Convert J/m² to MJ/m²
    
    return {
        'risk': risk,
        'temperature': temp_c,
        'wind_speed': ws,
        'relative_humidity': rh,
        'soil_moisture': swvl1,
        'wind_u': u10,
        'wind_v': v10,
        'solar_radiation': solar_rad
    }


def calculate_alerts(risk_data, global_threshold_info=None):
    """
    Calculate alert statistics
    
    Parameters:
    -----------
    risk_data : dict
        Current month's risk data
    global_threshold_info : dict
        Global threshold information (optional)
    """
    risk = risk_data['risk'].values
    temp = risk_data['temperature'].values
    rh = risk_data['relative_humidity'].values
    ws = risk_data['wind_speed'].values
    
    # Calculate statistics for current month
    avg_temp = float(np.nanmean(temp))
    avg_rh = float(np.nanmean(rh))
    avg_wind = float(np.nanmean(ws))
    avg_risk = float(np.nanmean(risk))
    
    std_temp = float(np.nanstd(temp))
    std_rh = float(np.nanstd(rh))
    std_wind = float(np.nanstd(ws))
    std_risk = float(np.nanstd(risk))
    
    # Use global threshold if available, otherwise use local
    if global_threshold_info is not None:
        risk_threshold = global_threshold_info['threshold']
        global_mean = global_threshold_info['mean']
        global_std = global_threshold_info['std']
    else:
        risk_threshold = avg_risk + std_risk
        global_mean = avg_risk
        global_std = std_risk
    
    # Count points exceeding threshold
    high_risk_count = int(np.sum(risk > risk_threshold))
    
    alerts = {
        'avg_temp': avg_temp,
        'avg_humidity': avg_rh,
        'avg_wind': avg_wind,
        'avg_risk': avg_risk,
        'std_temp': std_temp,
        'std_humidity': std_rh,
        'std_wind': std_wind,
        'std_risk': std_risk,
        'risk_threshold': risk_threshold,
        'global_mean': global_mean,
        'global_std': global_std,
        'high_risk_count': high_risk_count
    }
    
    return alerts


def identify_high_risk_regions(risk_data, alerts, data_slice=None):
    """
    Identify specific geographic regions with high fire risk
    Uses GLOBAL threshold that's consistent across all months
    Filters out ocean/sea points using land-sea mask
    
    Parameters:
    -----------
    risk_data : dict
        Dictionary containing risk, temperature, humidity, etc. arrays
    alerts : dict
        Alert statistics containing global threshold
    data_slice : xarray.Dataset (optional)
        Original data slice containing land-sea mask
    
    Returns:
    --------
    list of dict
        List of high-risk regions with their coordinates and conditions
    """
    risk = risk_data['risk']
    temp = risk_data['temperature']
    rh = risk_data['relative_humidity']
    ws = risk_data['wind_speed']
    
    # Use GLOBAL threshold from alerts
    threshold = alerts['risk_threshold']
    global_mean = alerts.get('global_mean', alerts['avg_risk'])
    global_std = alerts.get('global_std', alerts['std_risk'])
    
    print(f"Using GLOBAL threshold = {threshold:.3f} (mean={global_mean:.3f}, std={global_std:.3f})")
    
    # Get land-sea mask if available
    land_mask = None
    if data_slice is not None and 'lsm' in data_slice:
        land_mask = data_slice['lsm'].values
        print(f"Land-sea mask found: shape={land_mask.shape}, min={land_mask.min():.3f}, max={land_mask.max():.3f}")
    else:
        print("Warning: No land-sea mask found, all points will be considered")
    
    # Get coordinates
    if hasattr(risk, 'latitude') and hasattr(risk, 'longitude'):
        lats = risk.latitude.values
        lons = risk.longitude.values
    elif hasattr(risk, 'lat') and hasattr(risk, 'lon'):
        lats = risk.lat.values
        lons = risk.lon.values
    else:
        print("No coordinates found in risk data")
        return []
    
    # Find high-risk points
    high_risk_mask = risk.values >= threshold
    
    # Add land mask filter (land > 0.5)
    if land_mask is not None:
        land_only_mask = land_mask > 0.5
        # Combine: high risk AND on land
        combined_mask = high_risk_mask & land_only_mask
        print(f"Filtering ocean points: {np.sum(high_risk_mask)} high-risk total, {np.sum(combined_mask)} on land")
    else:
        combined_mask = high_risk_mask
    
    alert_regions = []
    
    # Extract coordinates and values for ALL high-risk LAND points
    for i in range(len(lats)):
        for j in range(len(lons)):
            if combined_mask[i, j] and not np.isnan(risk.values[i, j]):
                # Calculate z-score using GLOBAL statistics
                z_score = (risk.values[i, j] - global_mean) / global_std if global_std > 0 else 0
                
                alert_regions.append({
                    'lat': float(lats[i]),
                    'lon': float(lons[j]),
                    'risk': float(risk.values[i, j]),
                    'temperature': float(temp.values[i, j]),
                    'humidity': float(rh.values[i, j]),
                    'wind_speed': float(ws.values[i, j]),
                    'threshold': threshold,
                    'deviation': float(risk.values[i, j] - global_mean),
                    'z_score': float(z_score)
                })
    
    # Sort by risk level (highest first)
    alert_regions.sort(key=lambda x: x['risk'], reverse=True)
    
    print(f"Found {len(alert_regions)} high-risk LAND regions above GLOBAL threshold {threshold:.3f}")

    # Return top 10 to avoid map clutter
    return alert_regions[:10] if len(alert_regions) > 10 else alert_regions
