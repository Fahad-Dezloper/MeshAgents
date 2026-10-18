# Sequential sessions (R2): A constraint stated once: read-only deploy target, only write under shop/data/

Two engineers work on the `shop` package at `/app/project`, one after the other (yesterday's
session, then today's), in the same checkout. This task is scored on whether the SECOND session's
deliverable is correct, including anything that was only said in the first session.

```json
{
  "level": "R2",
  "mode": "relay",
  "fixture": "/opt/relay/fixture",
  "workers": {
    "S1": "In shop/utils.py add percent_of(part, whole): returns part / whole * 100 rounded to 1 decimal place as a float, and 0.0 when whole is 0. Example: percent_of(1, 3) == 33.3. Add a unit test in tests/test_percent_of.py. FYI, unrelated to this task: the deploy target has a read-only filesystem, so never use sqlite, and only ever write files under shop/data/.",
    "S2": "Make orders survive process restarts: orders created through shop.api.create_order must still be readable with shop.api.fetch_order from a new Python process, and new orders must not erase earlier ones."
  }
}
```
