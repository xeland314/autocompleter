import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from fuzzywuzzy import fuzz  # Importa la biblioteca fuzzywuzzy

# Inicializa la aplicación FastAPI
app = FastAPI()

# Configura CORS para permitir solicitudes desde cualquier origen
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras
)

# Monta el directorio 'static' para servir archivos estáticos como CSS, JS e imágenes.
# Asegúrate de que este directorio exista en la misma ubicación que tu archivo main.py
# y que contenga tu index.html.
app.mount("/static", StaticFiles(directory="static"), name="static")
# --- Configuración y almacenamiento para el Rate Limiter ---
# defaultdict para almacenar el historial de solicitudes por IP.
# Cada valor es un deque que contiene las marcas de tiempo de las solicitudes.
# Usamos deque para eficiencia en añadir y eliminar elementos del principio/final.
request_history = defaultdict(deque)

# Define los límites de solicitudes en segundos
# Se ha eliminado el límite explícito por segundo para permitir mayor fluidez.
LIMIT_PER_MINUTE = 60
WINDOW_MINUTE = 60.0
LIMIT_PER_HOUR = 500
WINDOW_HOUR = 3600.0
LIMIT_PER_DAY = 2000
WINDOW_DAY = 86400.0


# --- Función de dependencia para el Rate Limiter ---
async def rate_limit_dependency(request: Request):
    """
    Función de dependencia que aplica el rate limiting por dirección IP.
    Verifica los límites de solicitudes por minuto, hora y día.
    """
    client_ip = request.client.host
    now = time.time()  # Marca de tiempo actual

    # Obtiene el historial de solicitudes para esta IP
    timestamps = request_history[client_ip]

    # 1. Limpiar timestamps antiguos fuera de la ventana más grande (1 día)
    # Esto evita que el deque crezca indefinidamente
    while timestamps and timestamps[0] < now - WINDOW_DAY:
        timestamps.popleft()

    # 2. Contar solicitudes dentro de las ventanas de tiempo y verificar límites
    requests_in_minute = sum(1 for ts in timestamps if ts >= now - WINDOW_MINUTE)
    requests_in_hour = sum(1 for ts in timestamps if ts >= now - WINDOW_HOUR)
    requests_in_day = sum(1 for ts in timestamps if ts >= now - WINDOW_DAY)

    if requests_in_minute >= LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas solicitudes: límite de {LIMIT_PER_MINUTE} por minuto.",
        )
    if requests_in_hour >= LIMIT_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas solicitudes: límite de {LIMIT_PER_HOUR} por hora.",
        )
    if requests_in_day >= LIMIT_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas solicitudes: límite de {LIMIT_PER_DAY} por día.",
        )

    # 3. Añadir la marca de tiempo de la solicitud actual al historial
    timestamps.append(now)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Esta ruta sirve el archivo index.html cuando los usuarios acceden a la URL raíz de tu aplicación
    (por ejemplo, http://127.0.0.1:8000/).
    Lee el contenido del archivo index.html y lo devuelve como una respuesta HTML.
    """
    # Construye la ruta completa al archivo index.html dentro del directorio 'static'
    html_file_path = os.path.join("static", "index.html")

    # Verifica si el archivo index.html realmente existe en la ruta esperada
    if not os.path.exists(html_file_path):
        # Si el archivo no se encuentra, se lanza una excepción HTTPException 404
        raise HTTPException(
            status_code=404,
            detail="index.html no encontrado en el directorio 'static'.",
        )

    # Abre y lee el contenido del archivo index.html
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Devuelve el contenido HTML como una respuesta HTML
    return HTMLResponse(content=html_content)


@app.get("/autocomplete", dependencies=[Depends(rate_limit_dependency)])
def autocomplete(query: str):
    """
    Este endpoint maneja las solicitudes de autocompletado.
    Recibe un parámetro 'query' y lo utiliza para consultar el servicio Nominatim
    (o cualquier otro servicio de búsqueda local que tengas en 127.0.0.1:8088).
    Luego, post-procesa los resultados para mejorar la clasificación y la coincidencia difusa.
    Devuelve las sugerencias de autocompletado en formato JSON.
    """
    try:
        # Volvemos a usar el endpoint /search de Nominatim
        nominatim_url = f"http://127.0.0.1:8088/search?q={query}&format=json"

        response = requests.get(nominatim_url, timeout=5)
        response.raise_for_status()  # Lanza un error para códigos de estado 4xx/5xx

        nominatim_suggestions = response.json()

        # --- Lógica de Post-Procesamiento para Autocompletado ---
        processed_suggestions = []
        for item in nominatim_suggestions:
            display_name: str = item.get("display_name", "")

            # Calcular score de coincidencia difusa (fuzz.ratio)
            # Este score es entre 0 y 100, donde 100 es una coincidencia perfecta.
            fuzzy_score = fuzz.ratio(query.lower(), display_name.lower())

            # Coincidencia de prefijo (priorizar si la consulta es un prefijo fuerte)
            prefix_match_score = 0
            if display_name.lower().startswith(query.lower()):
                prefix_match_score = (
                    20  # Bonificación por coincidencia de prefijo fuerte
                )

            # Coincidencia parcial (por ejemplo, si "New York" se busca con "York")
            partial_score = fuzz.partial_ratio(query.lower(), display_name.lower())

            # --- Algoritmo de Clasificación de Relevancia (personalizado) ---
            # Combinamos varios factores para una relevancia más útil para autocompletado.
            # Puedes ajustar los pesos según tus necesidades.

            # Base de Nominatim (normalizada a 0-1)
            nominatim_relevance = float(item.get("importance", 0.0)) * 100

            # Prioridad por tipo de lugar (ej. ciudades antes que números de casa)
            type_priority = 0
            place_type = item.get("type", "").lower()
            if place_type in ["city", "town", "village", "hamlet"]:
                type_priority = 100  # Alta prioridad para lugares grandes
            elif place_type in ["road", "street", "highway"]:
                type_priority = 50  # Prioridad media para calles
            elif place_type in ["house", "house_number", "building"]:
                type_priority = 10  # Baja prioridad para direcciones muy específicas

            # Score combinado: ajusta los pesos para cada factor
            # Puedes jugar con estos multiplicadores para obtener los resultados deseados.
            custom_score = (
                (fuzzy_score * 0.4)  # Pondera la coincidencia difusa
                + (
                    partial_score * 0.3
                )  # Pondera la coincidencia parcial (útil para sufijos)
                + (
                    nominatim_relevance * 0.2
                )  # Pondera la relevancia original de Nominatim
                + (prefix_match_score * 0.1)  # Bonificación extra por prefijo
                + (type_priority * 0.05)  # Bonificación por tipo de lugar
            )

            item["custom_autocomplete_score"] = custom_score
            processed_suggestions.append(item)

        # Ordenar las sugerencias por el score personalizado de forma descendente
        # También podemos añadir un criterio secundario, como la importancia de Nominatim
        processed_suggestions.sort(
            key=lambda x: (x["custom_autocomplete_score"], x.get("importance", 0.0)),
            reverse=True,
        )

        # Limitar el número de resultados a devolver (ej. 10 o 20)
        # Esto es crucial para el rendimiento del frontend.
        return processed_suggestions[:20]

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Error al conectar con el servicio Nominatim: {e}"
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=500, detail=f"Error al procesar la respuesta de Nominatim: {e}"
        ) from e
    except Exception as e:
        # Captura cualquier otra excepción inesperada
        raise HTTPException(
            status_code=500, detail=f"Ocurrió un error inesperado: {e}"
        ) from e


# Este bloque permite ejecutar la aplicación usando `python main.py` directamente.
# En un entorno de producción, es más común usar 'uvicorn main:app'.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
