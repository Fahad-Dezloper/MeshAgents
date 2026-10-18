# Sequential sessions (R4): A failed approach: do not build on shop.batch

Two engineers work on the `shop` package at `/app/project`, one after the other (yesterday's
session, then today's), in the same checkout. This task is scored on whether the SECOND session's
deliverable is correct, including anything that was only said in the first session.

```json
{
  "level": "R4",
  "mode": "relay",
  "fixture": "/opt/relay/fixture",
  "workers": {
    "S1": "In shop/api.py add order_exists(order_id) returning True when an order with that id has been saved and False otherwise. Add a unit test in tests/test_order_exists.py. FYI, unrelated to this task: we tried the batch endpoint (shop/batch.py) and it deadlocks under load, so do not build on shop.batch; use the single-item path, shop.api.create_order, instead.",
    "S2": "Add a bulk import feature: a new module shop/importer.py with import_orders(rows), where rows is a list of dicts {'id': str, 'items': [item dicts as accepted by shop.api.create_order]}. Create an order for every row whose id does not exist yet, skip rows whose id already exists, and return the number of orders created. Add a unit test in tests/test_importer.py."
  }
}
```
