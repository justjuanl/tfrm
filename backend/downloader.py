import cdsapi
import zipfile
import os
import streamlit as st


def download_galicia_data():
    """
    Download ERA5 monthly data for Galicia from Copernicus CDS
    """
    print("🌍 Iniciando descarga de datos ERA5 para Galicia...")
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Get credentials from environment variables or Streamlit secrets
    try:
        # Try Streamlit secrets first (for Community Cloud deployment)
        cds_url = st.secrets.get("CDSAPI_URL", "https://cds.climate.copernicus.eu/api")
        cds_key = st.secrets["CDSAPI_KEY"]
        print("✓ Using credentials from Streamlit secrets")
    except (FileNotFoundError, KeyError):
        # Fall back to environment variables (for Docker/local)
        cds_url = os.getenv("CDSAPI_URL", "https://cds.climate.copernicus.eu/api")
        cds_key = os.getenv("CDSAPI_KEY")
        
        if not cds_key:
            raise ValueError(
                "❌ CDSAPI_KEY not found! Please set it as an environment variable or in Streamlit secrets."
            )
        print("✓ Using credentials from environment variables")
    
    # Initialize CDS API client with explicit credentials
    client = cdsapi.Client(url=cds_url, key=cds_key)
    
    dataset = "reanalysis-era5-single-levels-monthly-means"
    request = {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": [
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "2m_dewpoint_temperature",
            "2m_temperature",
            "skin_temperature",
            "instantaneous_10m_wind_gust",
            "mean_potential_evaporation_rate",
            "mean_surface_downward_short_wave_radiation_flux",
            "surface_latent_heat_flux",
            "surface_sensible_heat_flux",
            "surface_solar_radiation_downwards",
            "potential_evaporation",
            "snow_depth",
            "snowmelt",
            "volumetric_soil_water_layer_1",
            "volumetric_soil_water_layer_2",
            "volumetric_soil_water_layer_3",
            "volumetric_soil_water_layer_4",
            "vertically_integrated_moisture_divergence",
            "high_vegetation_cover",
            "leaf_area_index_high_vegetation",
            "leaf_area_index_low_vegetation",
            "low_vegetation_cover",
            "land_sea_mask",
            "slope_of_sub_gridscale_orography",
            "standard_deviation_of_orography",
            "total_column_water_vapour"
        ],
        "year": [
            "2017", "2018", "2019",
            "2020", "2021", "2022",
            "2023", "2024", "2025"
        ],
        "month": [
            "01", "02", "03",
            "04", "05", "06",
            "07", "08", "09",
            "10", "11", "12"
        ],
        "time": ["00:00"],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [43.8, -9.3, 42.0, -6.7]  # Galicia bounds [N, W, S, E]
    }
    
    # Download to zip file
    zip_path = 'data/galicia_era5_data.zip'
    
    print("📥 Descargando datos (esto puede tardar varios minutos)...")
    client.retrieve(dataset, request, zip_path)
    
    print(f"✅ Descarga completada: {zip_path}")
    
    # Extract all .nc files
    print("📦 Extrayendo archivos NetCDF...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall("data")
    
    print("✅ Archivos extraídos exitosamente en data/")
    
    # List downloaded files
    nc_files = [f for f in os.listdir('data') if f.endswith('.nc')]
    print(f"\n📁 Archivos NetCDF descargados ({len(nc_files)}):")
    for f in nc_files:
        size_mb = os.path.getsize(f'data/{f}') / (1024 * 1024)
        print(f"  - {f} ({size_mb:.2f} MB)")
    
    print("\n🎉 ¡Datos listos para usar!")


if __name__ == '__main__':
    download_galicia_data()
