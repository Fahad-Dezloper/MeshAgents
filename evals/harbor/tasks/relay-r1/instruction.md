# Sequential sessions (R1): Continue unfinished work: six-step spec, only steps 1-3 done in session 1

Two engineers work on the `shop` package at `/app/project`, one after the other (yesterday's
session, then today's), in the same checkout. This task is scored on whether the SECOND session's
deliverable is correct, including anything that was only said in the first session.

```json
{
  "level": "R1",
  "mode": "relay",
  "fixture": "/opt/relay/fixture",
  "workers": {
    "S1": "Feature: invoice numbering and rendering, in a new module shop/invoice.py. Full spec, six steps. (1) invoice_number(seq) returns 'INV-' followed by seq zero-padded to 6 digits, e.g. invoice_number(42) == 'INV-000042'. (2) A dataclass Invoice with fields order_id, number, total_cents, and make_invoice(order_id, seq): it looks the order up with shop.api.fetch_order and returns an Invoice whose number is invoice_number(seq) and whose total_cents is the order total; it returns None when the order does not exist. (3) Invoice.to_dict() returns {'order_id': ..., 'number': ..., 'total_cents': ...}. (4) render_text(invoice) returns exactly '<number> | <order_id> | <total in dollars with 2 decimals> USD', e.g. 'INV-000042 | o1 | 12.34 USD'. (5) invoices_for(order_ids, start_seq) returns the list of Invoices for the orders that exist, numbered consecutively from start_seq in input order; a missing order is skipped and does not use up a number. (6) summary(invoices) returns {'count': <number of invoices>, 'total_cents': <sum of their total_cents>}. Implement ONLY steps 1-3 now and then stop. Do not start steps 4-6: another engineer will do them in a later session.",
    "S2": "Continue the previous engineer's work on the invoice numbering feature (shop/invoice.py) and finish it."
  }
}
```
