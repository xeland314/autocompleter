# --- Configuración y almacenamiento para el Rate Limiter ---
# defaultdict para almacenar el historial de solicitudes por IP.
# Cada valor es un deque que contiene las marcas de tiempo de las solicitudes.
# Usamos deque para eficiencia en añadir y eliminar elementos del principio/final.
from collections import defaultdict, deque
import time
from fastapi import HTTPException, Request


request_history = defaultdict(deque)

# Define los límites de solicitudes en segundos
# Se ha eliminado el límite explícito por segundo para permitir mayor fluidez.
LIMIT_PER_MINUTE = 3000
WINDOW_MINUTE = 60.0
LIMIT_PER_HOUR = 3000
WINDOW_HOUR = 3600.0
LIMIT_PER_DAY = 100000
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

