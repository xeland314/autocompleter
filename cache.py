import threading
from datetime import datetime
import sqlite3

from typing import List, Dict, Any, Optional
import json
import redis


# --- Redis Cache para respuestas de Nominatim (cache de corto plazo) ---
class RedisCache:
    """Clase para manejar la caché de Redis para respuestas de Nominatim."""

    def __init__(
        self, host="localhost", port=6379, db=0, expire_time_seconds: int = 300
    ):
        self.expire_time = expire_time_seconds
        try:
            self.redis_client = redis.StrictRedis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=1,
            )
            self.redis_client.ping()
            print("Conectado a Redis con éxito.")
            self.enabled = True
        except redis.exceptions.ConnectionError as e:
            print(
                f"""Advertencia: No se pudo conectar a Redis ({e}).
                La caché de Redis estará deshabilitada."""
            )
            self.enabled = False
        # Removed broad Exception catch to avoid catching too general exception

    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        if not self.enabled:
            return None
        try:
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
        except redis.exceptions.RedisError as e:
            print(f"Error al leer de Redis: {e}")
        return None

    def set(self, key: str, value: List[Dict[str, Any]]):
        if not self.enabled:
            return
        try:
            self.redis_client.setex(key, self.expire_time, json.dumps(value))
        except redis.exceptions.RedisError as e:
            print(f"Error al escribir en Redis: {e}")


# --- SQLite Store para Feedback y Popularidad (cache de largo plazo / persistente) ---
class FeedbackStore:
    """Clase para manejar el almacenamiento de feedback y popularidad en SQLite."""

    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self._db_lock = threading.Lock()  # ¡Movido aquí, antes de _initialize_db!
        self._initialize_db()

    def _initialize_db(self):
        # El lock ya está inicializado en __init__
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    selected_osm_id TEXT NOT NULL,
                    selected_display_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    UNIQUE(query, selected_osm_id)
                )
            """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS popularity (
                    query_prefix TEXT NOT NULL,
                    osm_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (query_prefix, osm_id)
                )
            """
            )
            conn.commit()
            conn.close()

    def record_selection(self, query: str, selected_item: Dict[str, Any]):
        with self._db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            osm_id = str(selected_item.get("osm_id"))
            display_name = selected_item.get("display_name", "")

            cursor.execute(
                """INSERT OR IGNORE INTO selections
                (query, selected_osm_id, selected_display_name, timestamp)
                VALUES (?, ?, ?, ?)""",
                (query, osm_id, display_name, now),
            )

            query_prefix = query.lower()[:3]
            cursor.execute(
                """
                INSERT INTO popularity (query_prefix, osm_id, display_name, count, last_updated)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(query_prefix, osm_id) DO UPDATE SET
                    count = count + 1,
                    last_updated = ?
                """,
                (query_prefix, osm_id, display_name, now, now),
            )

            conn.commit()
            conn.close()

    def get_popular_results(
        self, query_prefix: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        with self._db_lock:  # También protege las lecturas si se realizan en hilos
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT osm_id, display_name, count
                FROM popularity
                WHERE query_prefix = ?
                ORDER BY count DESC
                LIMIT ?
                """,
                (query_prefix.lower(), limit),
            )
            results = [
                {"osm_id": row[0], "display_name": row[1], "count": row[2]}
                for row in cursor.fetchall()
            ]
            conn.close()
            return results
