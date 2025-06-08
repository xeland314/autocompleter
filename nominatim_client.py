from typing import List, Dict, Any
import requests


class NominatimClient:
    """Cliente para interactuar con el servicio de geocodificación Nominatim."""

    def __init__(self, base_url: str = "http://127.0.0.1:8088"):
        self.base_url = base_url

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Realiza una búsqueda de geocodificación en Nominatim.
        """
        url = f"{self.base_url}/search?q={query}&format=json"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Error al conectar con Nominatim: {e}") from e
        except ValueError as e:
            raise ValueError(
                f"Error al procesar la respuesta JSON de Nominatim: {e}"
            ) from e

    def __str__(self):
        return f"NominatimClient(base_url={self.base_url})"
