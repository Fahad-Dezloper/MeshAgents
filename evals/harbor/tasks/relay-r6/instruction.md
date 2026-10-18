# Sequential sessions (R6): A needle in a pile of rules: one decisive refund rule among 20 pasted conventions

Two engineers work on the `shop` package at `/app/project`, one after the other (yesterday's
session, then today's), in the same checkout. This task is scored on whether the SECOND session's
deliverable is correct, including anything that was only said in the first session.

```json
{
  "level": "R6",
  "mode": "relay",
  "fixture": "/opt/relay/fixture",
  "workers": {
    "S1": "In shop/utils.py add initials(name): return the uppercase first letters of the words in name, e.g. initials('ada king lovelace') == 'AKL'; return '' for an empty or blank name. Add a unit test in tests/test_initials.py. FYI, unrelated to this task, here are the team conventions from our wiki, pasted for reference:\n- We never log full card numbers; only the last four digits may appear in logs.\n- Every email template lives in shop/emails/ and its subject line is at most 60 characters.\n- CSV exports always use semicolons as the delimiter and a UTF-8 BOM.\n- Cache keys are prefixed with the module name, e.g. 'orders:'.\n- Module names are lowercase_with_underscores; class names are CamelCase.\n- Every CLI flag has a long form, and long flags use dashes, not underscores.\n- Log lines are single-line JSON.\n- In this project timestamps are UTC, never local time.\n- Retries use exponential backoff with a maximum of 5 attempts.\n- Refund amounts are always capped at the original order total and rounded half-even to whole cents; never negative.\n- Feature flags are read only through shop/config.py.\n- Public functions get a one-line docstring.\n- Dates in user-facing text are formatted as YYYY-MM-DD.\n- Test files are named test_<module>.py and live in tests/.\n- Background jobs must be idempotent so they are safe to run twice.\n- Pagination defaults to 50 items per page, with a maximum of 200.\n- Webhook payloads are signed with HMAC-SHA256 and the signature is checked before parsing.\n- User-visible strings are English only for now; translation comes later.\n- Environment variable names start with SHOP_.\n- Release notes are written in the imperative mood, e.g. 'Add X'.",
    "S2": "In shop/api.py add refund_order(order_id, amount_cents): it refunds part or all of an existing order. amount_cents may be fractional (for example 1050.5, when it was computed from a percentage). It returns {'id': order_id, 'refunded_cents': <the amount refunded, as an int number of cents>}, or None when the order does not exist. Add a unit test in tests/test_refund.py."
  }
}
```
