# Buscador de Ubicaciones - Ecuador

Este proyecto es un buscador de ubicaciones que utiliza un servidor **Nominatim** local, filtrando únicamente resultados dentro de **Ecuador**.

## Características

- Creado con **FastAPI** y un HTML simple.
- Redirige las peticiones del usuario al servidor Nominatim local.
- Muestra los resultados en una página HTML.
- Permite ver un historial de búsquedas.
- Se pueden copiar fácilmente las coordenadas de una ubicación.
- Opción para abrir la ubicación directamente en **Google Maps**.

## Uso

1. Ingresa una dirección o lugar en Ecuador.
2. Visualiza los resultados y selecciona la ubicación deseada.
3. Copia las coordenadas o abre la ubicación en Google Maps u OSM.
4. Consulta el historial de búsquedas recientes.

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
