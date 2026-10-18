"""Create many orders in one call."""
import threading

from shop import api

_LOCK = threading.Lock()


def create_orders(rows):
    """rows: list of {"id": str, "items": [item dicts]}. Returns the list of created order ids."""
    created = []
    with _LOCK:
        for row in rows:
            api.create_order(row["id"], row["items"])
            created.append(row["id"])
    return created
