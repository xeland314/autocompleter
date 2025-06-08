import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Importa los módulos refactorizados
from rate_limiter import rate_limit_dependency
from nominatim_client import NominatimClient
from cache import RedisCache, FeedbackStore
from scoring_model import AutocompleteScorer

# Inicializa la aplicación FastAPI
app = FastAPI()

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta el directorio 'static'
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Inicialización de Clientes y Modelos ---
# Cliente de Nominatim
nominatim_client = NominatimClient(base_url="http://127.0.0.1:8088")

# Caché de Redis para respuestas de Nominatim (expire de 5 minutos)
redis_cache = RedisCache(expire_time_seconds=300)

# Almacén de Feedback y Popularidad con SQLite
# El archivo de base de datos se creará en el mismo directorio que main.py
feedback_store = FeedbackStore(
    db_path=os.path.join(os.path.dirname(__file__), "feedback.db")
)

# Modelo de scoring con integración de feedback
autocomplete_scorer = AutocompleteScorer(feedback_store=feedback_store)


# --- Rutas de la Aplicación ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Sirve el archivo index.html.
    """
    html_file_path = os.path.join("static", "index.html")
    if not os.path.exists(html_file_path):
        raise HTTPException(
            status_code=404,
            detail="index.html no encontrado en el directorio 'static'.",
        )
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/autocomplete", dependencies=[Depends(rate_limit_dependency)])
async def autocomplete(query: str):
    """
    Maneja las solicitudes de autocompletado, usando caché, Nominatim y el modelo de scoring.
    """
    try:
        # Intentar obtener la respuesta de la caché de Redis primero
        cached_suggestions = redis_cache.get(query.lower())
        if cached_suggestions:
            print(f"Cargando sugerencias de caché para: {query}")
            return cached_suggestions

        # Si no está en caché, consultar a Nominatim
        print(f"Consultando Nominatim para: {query}")
        nominatim_suggestions = nominatim_client.search(query)

        # Post-procesar y ordenar las sugerencias usando el modelo de scoring
        processed_suggestions = autocomplete_scorer.sort_suggestions(
            query, nominatim_suggestions
        )

        # Limitar el número de resultados para el frontend (ej. 10 o 20)
        final_suggestions = processed_suggestions[:20]

        # Guardar la respuesta en la caché de Redis
        redis_cache.set(query.lower(), final_suggestions)

        return final_suggestions

    except ConnectionError as e:
        raise HTTPException(
            status_code=500, detail=f"Error de conexión con Nominatim: {e}"
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=500, detail=f"Error de procesamiento de datos: {e}"
        ) from e
    except HTTPException:  # Re-raise HTTPExceptions from rate_limit_dependency
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ocurrió un error inesperado en el autocompletado: {e}",
        ) from e


@app.post("/feedback")
async def record_feedback(feedback_data: Dict[str, Any]):
    """
    Endpoint para recibir feedback del cliente (por ejemplo, la sugerencia seleccionada).
    """
    query = feedback_data.get("query")
    selected_item = feedback_data.get("selected_item")

    if not query or not selected_item:
        raise HTTPException(
            status_code=400, detail="Faltan datos de feedback (query o selected_item)."
        )

    try:
        feedback_store.record_selection(query, selected_item)
        return {"message": "Feedback registrado exitosamente."}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al registrar feedback: {e}"
        ) from e


# --- Ejecución de la Aplicación ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
