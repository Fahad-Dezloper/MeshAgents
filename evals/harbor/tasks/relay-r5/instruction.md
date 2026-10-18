# Sequential sessions (R5): Negative control: session 2 is unrelated to session 1

Two engineers work on the `shop` package at `/app/project`, one after the other (yesterday's
session, then today's), in the same checkout. This task is scored on whether the SECOND session's
deliverable is correct, including anything that was only said in the first session.

```json
{
  "level": "R5",
  "mode": "relay",
  "fixture": "/opt/relay/fixture",
  "workers": {
    "S1": "In shop/utils.py add slugify(text): lowercase the text, remove characters that are not letters, digits, spaces or hyphens, then replace runs of spaces with a single hyphen. Example: slugify('Hello, World 2026!') == 'hello-world-2026'. Add a unit test in tests/test_slugify.py.",
    "S2": "Add an item_count property to Order in shop/models.py (the sum of the quantities of its items) and include it as 'item_count' in the dict returned by shop.api.fetch_order. The existing keys of that dict must stay unchanged."
  }
}
```
