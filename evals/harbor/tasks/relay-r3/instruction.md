# Sequential sessions (R3): A convention stated once: ShopError and type hints on every new public function

Two engineers work on the `shop` package at `/app/project`, one after the other (yesterday's
session, then today's), in the same checkout. This task is scored on whether the SECOND session's
deliverable is correct, including anything that was only said in the first session.

```json
{
  "level": "R3",
  "mode": "relay",
  "fixture": "/opt/relay/fixture",
  "workers": {
    "S1": "In shop/utils.py add parse_sku(text): a SKU is three uppercase letters, a dash and four digits, e.g. 'ABC-1234'; return the tuple ('ABC', 1234) (prefix string, number as int). Text in any other format must be rejected with an exception. Add a unit test in tests/test_parse_sku.py. Team convention from now on: every new public function must raise ShopError (defined in shop/errors.py), never ValueError, and carry type hints on all parameters and the return value.",
    "S2": "In shop/utils.py add apply_coupon(total_cents, code): code 'SAVE10' takes 10 percent off and 'SAVE25' takes 25 percent off; the discount is total_cents * percent // 100 (integer cents) and the function returns total_cents minus the discount. Raise an exception for an unknown code or a negative total. Example: apply_coupon(1999, 'SAVE10') == 1800. Add a unit test in tests/test_apply_coupon.py."
  }
}
```
