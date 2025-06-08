from typing import List, Dict, Any

from fuzzywuzzy import fuzz

from cache import FeedbackStore


class AutocompleteScorer:
    """Modelo de puntuación personalizado para sugerencias de autocompletado."""

    def __init__(self, feedback_store: FeedbackStore):
        self.feedback_store = feedback_store
        # Pesos iniciales del algoritmo de puntuación.
        # Estos podrían ser ajustados por un modelo más complejo en el futuro.
        self.weights = {
            "fuzzy_match": 0.4,
            "partial_match": 0.3,
            "nominatim_relevance": 0.2,
            "prefix_match": 0.1,
            "type_priority": 0.05,
            "popularity_boost": 0.15,  # Nuevo peso para la popularidad
        }

        # Definición de prioridades por tipo de lugar
        self.type_priorities = {
            "city": 100,
            "town": 100,
            "village": 100,
            "hamlet": 100,
            "road": 50,
            "street": 50,
            "highway": 50,
            "house": 10,
            "house_number": 10,
            "building": 10,
        }

    def calculate_score(self, query: str, item: Dict[str, Any]) -> float:
        """
        Calcula un score de relevancia personalizado para una sugerencia.
        """
        display_name = item.get("display_name", "")

        query_lower = query.lower()
        display_name_lower = display_name.lower()

        # Coincidencia difusa
        fuzzy_score = fuzz.ratio(query_lower, display_name_lower)  # 0-100

        # Coincidencia parcial (útil para sufijos)
        partial_score = fuzz.partial_ratio(query_lower, display_name_lower)  # 0-100

        # Coincidencia de prefijo
        prefix_match_score = 0
        if display_name_lower.startswith(query_lower):
            prefix_match_score = 20  # Bonificación fija por prefijo exacto

        # Relevancia de Nominatim
        nominatim_relevance = (
            float(item.get("importance", 0.0)) * 100
        )  # Normalizar a 0-100

        # Prioridad por tipo de lugar
        type_priority = self.type_priorities.get(item.get("type", "").lower(), 0)

        # Popularidad basada en feedback de usuarios (nuestro "entrenamiento")
        # Obtener resultados populares para el prefijo de la consulta
        popularity_boost = 0
        query_prefix = query_lower[:3]  # Prefijo para la consulta de popularidad
        popular_results = self.feedback_store.get_popular_results(
            query_prefix, limit=10
        )

        for pop_item in popular_results:
            if str(pop_item["osm_id"]) == str(item.get("osm_id")):
                # Un impulso proporcional a la cuenta de popularidad.
                # Normaliza la cuenta para que el impulso no sea excesivamente grande.
                # Por ejemplo, si max_count es 100, y count es 50, boost = 50.
                max_count = (
                    max(p["count"] for p in popular_results) if popular_results else 1
                )
                popularity_boost = (
                    pop_item["count"] / max_count
                ) * 100  # Normalizar a 0-100
                break

        # Score combinado final
        custom_score = (
            (fuzzy_score * self.weights["fuzzy_match"])
            + (partial_score * self.weights["partial_match"])
            + (nominatim_relevance * self.weights["nominatim_relevance"])
            + (prefix_match_score * self.weights["prefix_match"])
            + (type_priority * self.weights["type_priority"])
            + (
                popularity_boost * self.weights["popularity_boost"]
            )  # Añadir el impulso de popularidad
        )

        return custom_score

    def sort_suggestions(
        self, query: str, suggestions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calcula scores para todas las sugerencias y las ordena.
        """
        for item in suggestions:
            item["custom_autocomplete_score"] = self.calculate_score(query, item)

        # Ordenar por score personalizado de forma descendente, luego por importancia de Nominatim
        suggestions.sort(
            key=lambda x: (x["custom_autocomplete_score"], x.get("importance", 0.0)),
            reverse=True,
        )

        return suggestions
