from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
import os
import time
from collections import defaultdict, deque

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
LIMIT_PER_SECOND_WINDOW = 2.0  # Para la regla de 2 solicitudes por segundo
LIMIT_PER_MINUTE = 20
WINDOW_MINUTE = 60.0
LIMIT_PER_HOUR = 500
WINDOW_HOUR = 3600.0
LIMIT_PER_DAY = 2000
WINDOW_DAY = 86400.0


# --- Función de dependencia para el Rate Limiter ---
async def rate_limit_dependency(request: Request):
    """
    Función de dependencia que aplica el rate limiting por dirección IP.
    Verifica los límites de solicitudes por segundo, minuto, hora y día.
    """
    client_ip = request.client.host
    now = time.time()  # Marca de tiempo actual

    # Obtiene el historial de solicitudes para esta IP
    timestamps = request_history[client_ip]

    # 1. Limpiar timestamps antiguos fuera de la ventana más grande (1 día)
    # Esto evita que el deque crezca indefinidamente
    while timestamps and timestamps[0] < now - WINDOW_DAY:
        timestamps.popleft()

    # 2. Verificar el límite de 1 solicitud por segundo
    # Si hay solicitudes en el historial y la última fue hace menos de 1 segundo, se bloquea.
    if timestamps and (now - timestamps[-1]) < LIMIT_PER_SECOND_WINDOW:
        raise HTTPException(
            status_code=429, detail="Demasiadas solicitudes: 1 por segundo."
        )

    # 3. Contar solicitudes dentro de las ventanas de tiempo y verificar límites
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

    # 4. Añadir la marca de tiempo de la solicitud actual al historial
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
    Devuelve las sugerencias de autocompletado en formato JSON.
    Se le ha añadido la dependencia 'rate_limit_dependency' para aplicar los límites de solicitudes.
    """
    try:
        # Define la URL de tu servicio Nominatim. Asegúrate de que este servicio
        # esté corriendo y sea accesible desde donde se ejecuta tu aplicación FastAPI.
        nominatim_url = f"http://127.0.0.1:8088/search?q={query}&format=json"

        # Realiza una solicitud GET al servicio Nominatim con un tiempo de espera de 5 segundos.
        response = requests.get(nominatim_url, timeout=5)

        # Lanza una excepción si la respuesta HTTP tiene un código de estado de error (4xx o 5xx).
        response.raise_for_status()

        # Parsea la respuesta JSON del servicio Nominatim
        suggestions = response.json()

        # Devuelve las sugerencias obtenidas
        return suggestions
    except requests.exceptions.RequestException as e:
        # Captura cualquier error relacionado con la solicitud (ej. problemas de red, timeout).
        # Se lanza una excepción HTTP 500 con un mensaje detallado del error.
        raise HTTPException(
            status_code=500, detail=f"Error al conectar con el servicio Nominatim: {e}"
        ) from e
    except ValueError as e:
        # Captura errores al intentar parsear la respuesta como JSON (si no es un JSON válido).
        # Se lanza una excepción HTTP 500 con un mensaje detallado.
        raise HTTPException(
            status_code=500, detail=f"Error al procesar la respuesta de Nominatim: {e}"
        ) from e


# Este bloque permite ejecutar la aplicación usando `python main.py` directamente.
# En un entorno de producción, es más común usar 'uvicorn main:app'.
if __name__ == "__main__":
    import uvicorn

    # Para ejecutar la aplicación, puedes usar este comando en tu terminal:
    # uvicorn main:app --reload --host 0.0.0.0 --port 8000
    # --reload: Reinicia el servidor automáticamente al detectar cambios en el código.
    # --host 0.0.0.0: Permite que la aplicación sea accesible desde otras máquinas en la red.
    # --port 8000: Define el puerto en el que se ejecutará la aplicación.
    uvicorn.run(app, host="0.0.0.0", port=8000)
