# Buscador de Ubicaciones - Ecuador

Este proyecto es un buscador de ubicaciones que utiliza un servidor **Nominatim** local, filtrando únicamente resultados dentro de **Ecuador**.

## Características

- Creado con **FastAPI** y un HTML simple.
- Redirige las peticiones del usuario al servidor Nominatim local.
- Muestra los resultados en una página HTML.
- Permite ver un historial de búsquedas.
- Se pueden copiar fácilmente las coordenadas de una ubicación.
- Opción para abrir la ubicación directamente en **Google Maps**.
- Muestra la ubicación seleccionada en un mapa interactivo usando **Leaflet**.
- Permite copiar las respuestas en formato **JSON** y **XML**.
- Acceso a la documentación interactiva de la API mediante **Swagger** y **ReDoc**.

## Uso

1. Ingresa una dirección o lugar en Ecuador.
2. Visualiza los resultados y selecciona la ubicación deseada.
3. Observa la ubicación en el mapa interactivo.
4. Copia las coordenadas o las respuestas en formato JSON o XML.
5. Abre la ubicación en Google Maps u OSM.
6. Consulta el historial de búsquedas recientes.
7. Accede a la documentación de la API en `/docs` (Swagger) o `/redoc` (ReDoc).

## Requisitos

- Python 3.8+
- FastAPI
- Servidor Nominatim local (aunque este esté configurado solo con datos de Ecuador)

## Instalación

```bash
pip install fastapi uvicorn requests python-multipart
```

## Ejecución

```bash
uvicorn main:app --reload
```

## Disclaimer

Este proyecto está diseñado únicamente para uso personal o en entornos controlados con un servidor Nominatim local configurado con datos de Ecuador.

> **Advertencia:**  
> No utilices este buscador con el servidor Nominatim original ni con plataformas que no permitan el uso de autocompletado o redirección de consultas automatizadas. El uso indebido puede violar los términos de servicio y resultar en bloqueos o sanciones.
