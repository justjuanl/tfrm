#!/bin/bash

# Function to show animated dots while waiting
show_progress() {
    local pid=$1
    local message=$2
    local dots=""
    
    echo -n "$message"
    
    while kill -0 $pid 2>/dev/null; do
        dots="${dots}."
        if [ ${#dots} -gt 3 ]; then
            dots=""
            echo -ne "\r$message   \r$message"
        else
            echo -ne "\r$message$dots"
        fi
        sleep 0.5
    done
    echo -e "\r$message... ✓"
}

echo "======================================"
echo "🚀 Fire Risk Dashboard - Iniciando"
echo "======================================"
echo ""

if [ ! -d "/app/data" ] || [ -z "$(ls -A /app/data/*.nc 2>/dev/null)" ]; then
    echo "📥 No se encontraron archivos de datos"
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║  🌍 DESCARGANDO DATOS CLIMÁTICOS       ║"
    echo "║                                        ║"
    echo "║  ⚠️  POR FAVOR NO CERRAR               ║"
    echo "║     Esto puede tardar 10-20 minutos   ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    
    # Run downloader in background
    python downloader.py &
    download_pid=$!
    
    # Show animated progress
    show_progress $download_pid "⏳ Descargando desde Copernicus CDS"
    
    # Wait for download to complete and check exit code
    wait $download_pid
    exit_code=$?
    
    echo ""
    if [ $exit_code -eq 0 ]; then
        echo "✅ ¡Descarga completada exitosamente!"
        echo ""
    else
        echo "❌ Error en la descarga (código: $exit_code)"
        echo "   Puedes reintentar con: docker exec galicia-fire-risk-dashboard python downloader.py"
        echo ""
        exit 1
    fi
else
    echo "✅ Archivos de datos encontrados"
    echo "   $(ls /app/data/*.nc | wc -l) archivos NetCDF disponibles"
    echo ""
fi

echo "======================================"
echo "🌐 Iniciando aplicación Streamlit"
echo "======================================"
echo ""

# Execute the CMD from compose.yml
exec "$@"
