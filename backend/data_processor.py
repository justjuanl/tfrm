import xarray as xr
import numpy as np
import pandas as pd
from glob import glob
import warnings

# Suppress chunking warnings
warnings.filterwarnings('ignore', message='.*chunks.*')

def preprocess_rename_time(ds):
    """Rename valid_time to time if present"""
    if 'valid_time' in ds.coords or 'valid_time' in ds.dims:
        ds = ds.rename({'valid_time': 'time'})
    return ds

def load_data():
    """Load and merge all NetCDF files safely"""
    files = sorted(glob('data/*.nc'))
    if not files:
        raise FileNotFoundError("No se encontraron archivos NetCDF en data/")
    
    print(f"Loading {len(files)} NetCDF files...")
    
    # Load and immediately convert to in-memory data
    datasets = []
    for f in files:
        print(f"  - Loading {f}")
        try:
            with xr.open_dataset(f, engine='netcdf4') as ds:
                ds = preprocess_rename_time(ds)
                ds = ds.load()
                datasets.append(ds)
        except Exception as e:
            print(f"    Warning: Could not load {f}: {e}")
            continue
    
    if not datasets:
        raise RuntimeError("No datasets could be loaded successfully")
    
    print("Merging datasets...")
    merged = xr.merge(datasets, compat='no_conflicts')
    print(f"Data loaded successfully! Shape: {dict(merged.dims)}")
    return merged

def get_available_year_months(ds):
    """Extract available (year, month) combinations from dataset"""
    dates = pd.to_datetime(ds.time.values)
    df = pd.DataFrame({'date': dates})
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    years = sorted(df['year'].unique())
    available = {y: sorted(df[df['year'] == y]['month'].unique().tolist()) for y in years}
    return available

def get_available_dates(ds):
    """Get list of available dates from dataset"""
    times = pd.to_datetime(ds.time.values)
    return sorted(times)

def get_data_for_date(ds, date):
    """Extract data for a specific date"""
    return ds.sel(time=date, method='nearest')

def calculate_wind_speed(u, v):
    """Calculate wind speed from u and v components"""
    return np.sqrt(u**2 + v**2)

def calculate_wind_direction(u, v):
    """Calculate wind direction in degrees"""
    direction = (180 / np.pi) * np.arctan2(u, v) + 180
    return direction

def calculate_relative_humidity(t2m, d2m):
    """Calculate relative humidity from temperature and dewpoint"""
    t_c = t2m - 273.15
    d_c = d2m - 273.15
    rh = 100 * (np.exp((17.625 * d_c) / (243.04 + d_c)) / 
                np.exp((17.625 * t_c) / (243.04 + t_c)))
    return np.clip(rh, 0, 100)

def calculate_yearly_trend(ds, variable, year, date_key='time'):
    """
    Calculate temporal trend for a specific year only
    Returns monthly values for that year
    """
    dates = pd.to_datetime(ds[date_key].values)
    
    # Filter only the selected year
    year_mask = dates.year == year
    year_dates = dates[year_mask]
    
    if len(year_dates) == 0:
        return {'dates': [], 'values': [], 'months': []}
    
    try:
        if variable == 'risk_index':
            values = []
            for date in year_dates:
                data_slice = ds.sel({date_key: date}, method='nearest')
                from risk_calculator import calculate_risk_index
                risk_data = calculate_risk_index(data_slice)
                avg_risk = float(risk_data['risk'].mean().values)
                values.append(avg_risk)
            values = np.array(values)
            
        elif variable == 'temperature':
            year_ds = ds.sel({date_key: year_dates})
            values = (year_ds['t2m'].mean(dim=['latitude', 'longitude']).values - 273.15)
            
        elif variable == 'relative_humidity':
            year_ds = ds.sel({date_key: year_dates})
            rh = calculate_relative_humidity(year_ds['t2m'], year_ds['d2m'])
            values = rh.mean(dim=['latitude', 'longitude']).values
            
        elif variable == 'solar_radiation':
            year_ds = ds.sel({date_key: year_dates})
            if 'ssrd' in year_ds:
                values = year_ds['ssrd'].mean(dim=['latitude', 'longitude']).values / 1e6
            else:
                values = np.zeros(len(year_dates))
                
        elif variable == 'wind_speed':
            year_ds = ds.sel({date_key: year_dates})
            # Calculate wind SPEED (not direction)
            ws = calculate_wind_speed(year_ds['u10'], year_ds['v10'])
            values = ws.mean(dim=['latitude', 'longitude']).values
            
        else:
            year_ds = ds.sel({date_key: year_dates})
            values = (year_ds['t2m'].mean(dim=['latitude', 'longitude']).values - 273.15)
        
        # Extract month numbers for x-axis
        months = [d.month for d in year_dates]
        
        return {'dates': year_dates, 'values': values, 'months': months}
        
    except Exception as e:
        print(f"Error calculating yearly trend for {variable}: {e}")
        return {'dates': year_dates, 'values': np.zeros(len(year_dates)), 'months': []}

def calculate_historical_average(ds, variable, start_year=2017, end_year=2024, date_key='time'):
    """
    Calculate monthly historical average from start_year to end_year
    Returns average values for each month (1-12)
    """
    dates = pd.to_datetime(ds[date_key].values)
    
    # Filter years in range
    mask = (dates.year >= start_year) & (dates.year <= end_year)
    historical_dates = dates[mask]
    
    if len(historical_dates) == 0:
        return {i: 0 for i in range(1, 13)}
    
    # Group by month and calculate averages
    monthly_avgs = {}
    
    for month in range(1, 13):
        month_dates = historical_dates[historical_dates.month == month]
        if len(month_dates) == 0:
            monthly_avgs[month] = np.nan
            continue
        
        try:
            if variable == 'risk_index':
                values = []
                for date in month_dates:
                    data_slice = ds.sel({date_key: date}, method='nearest')
                    from risk_calculator import calculate_risk_index
                    risk_data = calculate_risk_index(data_slice)
                    avg_risk = float(risk_data['risk'].mean().values)
                    values.append(avg_risk)
                monthly_avgs[month] = np.nanmean(values)
                
            elif variable == 'temperature':
                month_ds = ds.sel({date_key: month_dates})
                monthly_avgs[month] = float((month_ds['t2m'].mean(dim=['latitude', 'longitude']).mean().values - 273.15))
                
            elif variable == 'relative_humidity':
                month_ds = ds.sel({date_key: month_dates})
                rh = calculate_relative_humidity(month_ds['t2m'], month_ds['d2m'])
                monthly_avgs[month] = float(rh.mean(dim=['latitude', 'longitude']).mean().values)
                
            elif variable == 'solar_radiation':
                month_ds = ds.sel({date_key: month_dates})
                if 'ssrd' in month_ds:
                    monthly_avgs[month] = float(month_ds['ssrd'].mean(dim=['latitude', 'longitude']).mean().values / 1e6)
                else:
                    monthly_avgs[month] = 0

            elif variable == 'wind_speed':
                month_ds = ds.sel({date_key: month_dates})
                # Calculate wind SPEED for historical average
                ws = calculate_wind_speed(month_ds['u10'], month_ds['v10'])
                monthly_avgs[month] = float(ws.mean(dim=['latitude', 'longitude']).mean().values)
                
            else:
                month_ds = ds.sel({date_key: month_dates})
                monthly_avgs[month] = float((month_ds['t2m'].mean(dim=['latitude', 'longitude']).mean().values - 273.15))
                
        except Exception as e:
            print(f"Error calculating average for month {month}: {e}")
            monthly_avgs[month] = np.nan
    
    return monthly_avgs

def calculate_temporal_trend(ds, variable, date_key='time'):
    """Calculate temporal trend for a variable"""
    dates = pd.to_datetime(ds[date_key].values)
    
    try:
        if variable == 'risk_index':
            values = []
            for date in dates:
                data_slice = ds.sel({date_key: date}, method='nearest')
                from risk_calculator import calculate_risk_index
                risk_data = calculate_risk_index(data_slice)
                avg_risk = float(risk_data['risk'].mean().values)
                values.append(avg_risk)
            values = np.array(values)
        elif variable == 'temperature':
            values = (ds['t2m'].mean(dim=['latitude', 'longitude']).values - 273.15)
        elif variable == 'relative_humidity':
            rh = calculate_relative_humidity(ds['t2m'], ds['d2m'])
            values = rh.mean(dim=['latitude', 'longitude']).values
        elif variable == 'solar_radiation':
            if 'ssrd' in ds:
                values = ds['ssrd'].mean(dim=['latitude', 'longitude']).values / 1e6
            else:
                values = np.zeros(len(dates))
        elif variable == 'wind_speed':
            ws = calculate_wind_speed(ds['u10'], ds['v10'])
            values = ws.mean(dim=['latitude', 'longitude']).values
        else:
            values = (ds['t2m'].mean(dim=['latitude', 'longitude']).values - 273.15)
        
        return {'dates': dates, 'values': values}
    except Exception as e:
        print(f"Error calculating trend for {variable}: {e}")
        return {'dates': dates, 'values': np.zeros(len(dates))}
    
def load_fire_data():
    """Load and filter fire data for Galicia region"""
    try:
        import pandas as pd
        
        fires_df = pd.read_csv('data/fires-all.csv')
        
        # Filter for Galicia, fires > 10 hectares, from 2017 onwards
        fires_galicia = fires_df[
            (fires_df['superficie'] > 10) & 
            (fires_df['lat'] > 41.78) & 
            (fires_df['lat'] < 43.3) & 
            (fires_df['lng'] > -9.7) & 
            (fires_df['lng'] < -6.7) & 
            (fires_df['fecha'] >= '2017-01-01')
        ].copy()
        
        # Convert fecha to datetime
        fires_galicia['fecha'] = pd.to_datetime(fires_galicia['fecha'])
        
        print(f"Loaded {len(fires_galicia)} fire records for Galicia (>10ha, 2017+)")
        return fires_galicia
        
    except Exception as e:
        print(f"Error loading fire data: {e}")
        return pd.DataFrame()

