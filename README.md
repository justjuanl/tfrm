![logo](src/bannertfrm.png)

# Trinity's Fire Risk Map 🧭

Mapa comunitario interactivo para la región española de Galicia,
para prevención y sistema de alertas de incendios. 🔥

## Por qué? 🤔

Como parte de nuestra solución al Reto 4 del Hackaton CoAfina 2025 "Educando a las comunidades con ciencia del cambio climático" hemos desarrollado una app de libre acceso al alcance de la población civil para monitoreo de diversas variables y métricas climáticas, así como un sistema de alerta temprana para posibles escenarios de incendios forestales.

## ¿Para quién? 🌍

### PARA TODOS❗❤️

Toda persona con un dispositivo con conexion a internet puede ser capaz de conectarse!

### Interfaz intuitiva y sencilla 🙂‍↕️

![interfaz](src/interfaz.png)

Sin ejecutar scripts, sin instalación, sin descargas 🙂‍↔️🙂‍↔️🙂‍↔️

Los datos son nuestros aliados en la prevención y lucha contra el cambio climático, si los entendemos podemos tomar acción!


## Datos abiertos científicamente trabajados 😎👨‍🔬

Trinity's Fire Risk Map utiliza un gran conjuntos de datos abiertos de "Copernicus Data Space Ecosystem" un programa de Observación de la Tierra de la Unión Europea, liderado por la Comisión Europea en asociación con la Agencia Espacial Europea (ESA) 🇪🇺


#### Trinity's Fire Map considera parametros calculados a partir de técnicas profesionales en el analisis de datos para proporcinar informacion util y confiable a los usuarios.

![correlacion](src/matriz_correlacion.png)

## Despliegue 🚀⚡

La App usas la tecnología de los contenedores Dockers para funcionar como una Docker Web App, sustentada en Streamlit para la creacion de Dashboard y graficos interactivos, mezclado con la potencia de Python y sus distintas librerias (Flask, Numpy, Xarray, Folium, Matplotlib)


<div style="display: flex; gap: 20px; justify-content: center;">
  <img src="src/docker.png" alt="Descripción 1" width="300" height="200" />
  
  <img src="src/python.png" alt="Descripción 2" width="300" height="200" />
</div>


### Pre-requisitos
- Docker y Docker Compose instalados. [Documentacion](https://docs.docker.com/)

- Credenciales del Climate Data Store (CDS) de Copernicus.
  [Puedes configurarlo aqui!](https://cds.climate.copernicus.eu/how-to-api)
  





### Paso a Paso:

1. Clona el repositorio
```
git clone #link-del-repo
```
2. cambia a la carpeta del repositorio
```
cd /carpeta-repositori
```
3. Modifica el contenido del archivo ".env" añadiendo la key CDS 
```
#ejecuta "ls -a" si no ves el archivo

CDSAPI_KEY='tu-key' #sin comillas
```


4. Inicia el dashboard, desde el directorio donde se encuentra el compose.yml:

```bash
docker compose up

#usa "docker compose up -d" para el modo detached
```

5. Abre tu navegador en `http://localhost:8501`

