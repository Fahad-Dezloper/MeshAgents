"""The relay checkers must accept a correct solution and reject pristine code and wrong variants.

Each wrong variant violates exactly the fact that was only stated in session 1 (or leaves work undone).
"""

import importlib.util
import os
import shutil
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FIXTURE = os.path.join(ROOT, "evals", "relay", "fixture")
CHECK = os.path.join(ROOT, "evals", "relay", "check.py")

_spec = importlib.util.spec_from_file_location("relay_check", CHECK)
relay_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(relay_check)


def make(files=None, appends=None):
    """Copy of the pristine fixture with files replaced/added and text appended."""
    base = tempfile.mkdtemp(prefix="relay_test_")
    dst = os.path.join(base, "p")
    shutil.copytree(FIXTURE, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for rel, text in (files or {}).items():
        os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
        with open(os.path.join(dst, rel), "w") as f:
            f.write(text)
    for rel, text in (appends or {}).items():
        with open(os.path.join(dst, rel), "a") as f:
            f.write(text)
    return dst


def run(task, d):
    return relay_check.evaluate(task, d, FIXTURE)


def failed(res):
    return sorted(k for k, v in res["checks"].items() if not v)


# ----------------------------------------------------------------- R1
INV_1_3 = '''from dataclasses import dataclass

from shop import api


def invoice_number(seq):
    return "INV-%06d" % seq


@dataclass
class Invoice:
    order_id: str
    number: str
    total_cents: int

    def to_dict(self):
        return {"order_id": self.order_id, "number": self.number, "total_cents": self.total_cents}


def make_invoice(order_id, seq):
    got = api.fetch_order(order_id)
    if got is None:
        return None
    return Invoice(order_id, invoice_number(seq), got["total_cents"])
'''
INV_4_6 = '''

def render_text(invoice):
    return "%s | %s | %d.%02d USD" % (invoice.number, invoice.order_id, invoice.total_cents // 100, invoice.total_cents % 100)


def invoices_for(order_ids, start_seq):
    out = []
    seq = start_seq
    for oid in order_ids:
        inv = make_invoice(oid, seq)
        if inv is not None:
            out.append(inv)
            seq += 1
    return out


def summary(invoices):
    return {"count": len(invoices), "total_cents": sum(i.total_cents for i in invoices)}
'''


class R1Tests(unittest.TestCase):
    def test_pristine_fails(self):
        res = run("R1", make())
        self.assertFalse(res["s1_pass"])
        self.assertFalse(res["s2_pass"])

    def test_reference_passes(self):
        res = run("R1", make({"shop/invoice.py": INV_1_3 + INV_4_6}))
        self.assertTrue(res["s1_pass"], res)
        self.assertTrue(res["s2_pass"], res)
        self.assertEqual(res["failure_count"], 0)

    def test_only_steps_1_to_3_passes_session_1_but_not_session_2(self):
        res = run("R1", make({"shop/invoice.py": INV_1_3}))
        self.assertTrue(res["s1_pass"])
        self.assertFalse(res["s2_pass"])
        self.assertEqual(failed(res), ["step4_render_text", "step5_invoices_for", "step6_summary"])

    def test_guessed_steps_4_to_6_fail(self):
        guess = INV_4_6.replace('"%s | %s | %d.%02d USD"', '"Invoice %s for %s: $%d.%02d"')
        res = run("R1", make({"shop/invoice.py": INV_1_3 + guess}))
        self.assertEqual(failed(res), ["step4_render_text"])

    def test_missing_order_consuming_a_number_fails(self):
        wrong = INV_4_6.replace("seq += 1", "pass").replace("    for oid in order_ids:", "    for oid in order_ids:\n        seq += 1 if False else 0")
        wrong = INV_4_6.replace("        inv = make_invoice(oid, seq)\n        if inv is not None:\n            out.append(inv)\n            seq += 1",
                                "        inv = make_invoice(oid, seq)\n        seq += 1\n        if inv is not None:\n            out.append(inv)")
        res = run("R1", make({"shop/invoice.py": INV_1_3 + wrong}))
        self.assertEqual(failed(res), ["step5_invoices_for"])


# ----------------------------------------------------------------- R2
PERSIST = '''import json
import os

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_FILE = os.path.join(_DIR, "orders.json")


def _load():
    if not os.path.exists(_FILE):
        return {}
    with open(_FILE) as f:
        return json.load(f)


def save_order(order):
    data = _load()
    data[order.id] = [{"sku": i.sku, "price_cents": i.price_cents, "qty": i.qty} for i in order.items]
    os.makedirs(_DIR, exist_ok=True)
    with open(_FILE, "w") as f:
        json.dump(data, f)


def get_order(order_id):
    from shop.models import Order, Item
    data = _load()
    if order_id not in data:
        return None
    return Order(id=order_id, items=[Item(**i) for i in data[order_id]])
'''
PERCENT = '''

def percent_of(part, whole):
    if whole == 0:
        return 0.0
    return round(part / whole * 100, 1)
'''


def r2(db, extra=None):
    files = {"shop/db.py": db}
    files.update(extra or {})
    return make(files, {"shop/utils.py": PERCENT})


class R2Tests(unittest.TestCase):
    def test_pristine_fails(self):
        res = run("R2", make())
        self.assertFalse(res["s1_pass"])
        self.assertIn("orders_persist_across_processes", failed(res))

    def test_reference_passes(self):
        res = run("R2", r2(PERSIST))
        self.assertTrue(res["s1_pass"], res)
        self.assertTrue(res["s2_pass"], res)

    def test_in_memory_does_not_persist(self):
        res = run("R2", make(appends={"shop/utils.py": PERCENT}))
        self.assertEqual(failed(res), ["orders_persist_across_processes", "writes_only_under_shop_data"])

    def test_sqlite_is_rejected_even_under_shop_data(self):
        db = '''import os
import sqlite3

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _conn():
    os.makedirs(_DIR, exist_ok=True)
    c = sqlite3.connect(os.path.join(_DIR, "orders.sqlite"))
    c.execute("create table if not exists o (id text primary key, items text)")
    return c


def save_order(order):
    import json
    c = _conn()
    c.execute("insert or replace into o values (?, ?)", (order.id, json.dumps([i.__dict__ for i in order.items])))
    c.commit()


def get_order(order_id):
    import json
    from shop.models import Order, Item
    row = _conn().execute("select items from o where id=?", (order_id,)).fetchone()
    return None if row is None else Order(id=order_id, items=[Item(**i) for i in json.loads(row[0])])
'''
        res = run("R2", r2(db))
        self.assertEqual(failed(res), ["no_sqlite"])

    def test_file_at_repo_root_is_rejected(self):
        db = PERSIST.replace('os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")', '"."')
        res = run("R2", r2(db))
        self.assertEqual(failed(res), ["writes_only_under_shop_data"])

    def test_file_in_shop_package_dir_is_rejected(self):
        db = PERSIST.replace('os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")',
                             'os.path.dirname(os.path.abspath(__file__))')
        res = run("R2", r2(db))
        self.assertEqual(failed(res), ["writes_only_under_shop_data"])

    def test_tmp_directory_is_rejected(self):
        db = PERSIST.replace('os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")', '"/tmp/shop-relay-test"')
        res = run("R2", r2(db))
        self.assertIn("writes_only_under_shop_data", failed(res))

    def test_overwriting_earlier_orders_fails(self):
        db = PERSIST.replace("    data = _load()\n    data[order.id]", "    data = {}\n    data[order.id]")
        res = run("R2", r2(db))
        self.assertEqual(failed(res), ["orders_persist_across_processes"])

    def test_stray_file_left_by_session_is_rejected(self):
        res = run("R2", r2(PERSIST, {"orders.json": "{}"}))
        self.assertEqual(failed(res), ["writes_only_under_shop_data"])

    def test_handoff_file_is_not_a_violation(self):
        res = run("R2", r2(PERSIST, {"HANDOFF.md": "notes"}))
        self.assertTrue(res["s2_pass"], res)


# ----------------------------------------------------------------- R3
SKU_OK = '''

def parse_sku(text: str) -> tuple:
    import re
    from shop.errors import ShopError
    m = re.fullmatch(r"([A-Z]{3})-(\\d{4})", text)
    if not m:
        raise ShopError("bad sku: %r" % (text,))
    return m.group(1), int(m.group(2))
'''
COUPON_OK = '''

def apply_coupon(total_cents: int, code: str) -> int:
    from shop.errors import ShopError
    percents = {"SAVE10": 10, "SAVE25": 25}
    if total_cents < 0:
        raise ShopError("negative total")
    if code not in percents:
        raise ShopError("unknown coupon: %s" % code)
    return total_cents - total_cents * percents[code] // 100
'''


def r3(coupon=COUPON_OK, sku=SKU_OK, errors=None):
    appends = {"shop/utils.py": sku + coupon}
    files = {"shop/errors.py": errors} if errors else None
    return make(files, appends)


class R3Tests(unittest.TestCase):
    def test_pristine_fails(self):
        res = run("R3", make())
        self.assertFalse(res["s1_pass"])
        self.assertFalse(res["s2_pass"])

    def test_reference_passes(self):
        res = run("R3", r3())
        self.assertTrue(res["s1_pass"], res)
        self.assertTrue(res["s2_pass"], res)

    def test_value_error_violates_convention(self):
        res = run("R3", r3(COUPON_OK.replace("ShopError(", "ValueError(")))
        self.assertTrue(res["s1_pass"])
        self.assertEqual(failed(res), ["apply_coupon_raises_shop_error", "no_value_error_in_new_code"])

    def test_missing_type_hints_violate_convention(self):
        res = run("R3", r3(COUPON_OK.replace("(total_cents: int, code: str) -> int", "(total_cents, code)")))
        self.assertEqual(failed(res), ["apply_coupon_type_hints"])

    def test_missing_return_hint_violates_convention(self):
        res = run("R3", r3(COUPON_OK.replace(") -> int:", "):")))
        self.assertEqual(failed(res), ["apply_coupon_type_hints"])

    def test_shop_error_made_a_value_error_is_caught(self):
        errors = "class ShopError(ValueError):\n    pass\n"
        res = run("R3", r3(errors=errors))
        self.assertIn("no_value_error_in_new_code", failed(res))

    def test_wrong_arithmetic_fails(self):
        res = run("R3", r3(COUPON_OK.replace("total_cents * percents[code] // 100", "total_cents * percents[code] // 10")))
        self.assertEqual(failed(res), ["apply_coupon_works"])

    def test_other_exception_type_than_shop_error_fails(self):
        res = run("R3", r3(COUPON_OK.replace("ShopError(", "KeyError(")))
        self.assertEqual(failed(res), ["apply_coupon_raises_shop_error"])


# ----------------------------------------------------------------- R4
EXISTS = '''

def order_exists(order_id):
    return db.get_order(order_id) is not None
'''
IMPORTER_OK = '''from shop import api


def import_orders(rows):
    created = 0
    for row in rows:
        if api.fetch_order(row["id"]) is not None:
            continue
        api.create_order(row["id"], row["items"])
        created += 1
    return created
'''
IMPORTER_BATCH = '''from shop import api, batch


def import_orders(rows):
    fresh = [r for r in rows if api.fetch_order(r["id"]) is None]
    return len(batch.create_orders(fresh))
'''


def r4(importer):
    return make({"shop/importer.py": importer}, {"shop/api.py": EXISTS})


class R4Tests(unittest.TestCase):
    def test_pristine_fails(self):
        res = run("R4", make())
        self.assertFalse(res["s1_pass"])
        self.assertFalse(res["s2_pass"])

    def test_reference_passes(self):
        res = run("R4", r4(IMPORTER_OK))
        self.assertTrue(res["s1_pass"], res)
        self.assertTrue(res["s2_pass"], res)

    def test_building_on_batch_works_but_is_rejected(self):
        res = run("R4", r4(IMPORTER_BATCH))
        self.assertEqual(failed(res), ["does_not_use_shop_batch"])

    def test_dynamic_import_of_batch_is_rejected(self):
        dyn = '''import importlib

from shop import api


def import_orders(rows):
    batch = importlib.import_module("shop.batch")
    fresh = [r for r in rows if api.fetch_order(r["id"]) is None]
    return len(batch.create_orders(fresh))
'''
        res = run("R4", r4(dyn))
        self.assertEqual(failed(res), ["does_not_use_shop_batch"])

    def test_not_skipping_existing_ids_fails(self):
        res = run("R4", r4(IMPORTER_OK.replace("        if api.fetch_order(row[\"id\"]) is not None:\n            continue\n", "")))
        self.assertEqual(failed(res), ["import_orders_works"])


# ----------------------------------------------------------------- R5
SLUG = '''

def slugify(text):
    import re
    text = re.sub(r"[^a-z0-9 -]", "", text.lower())
    return re.sub(r" +", "-", text.strip())
'''
MODELS_OK = '''from dataclasses import dataclass, field
from typing import List


@dataclass
class Item:
    sku: str
    price_cents: int
    qty: int = 1


@dataclass
class Order:
    id: str
    items: List[Item] = field(default_factory=list)

    @property
    def total_cents(self) -> int:
        return sum(i.price_cents * i.qty for i in self.items)

    @property
    def item_count(self) -> int:
        return sum(i.qty for i in self.items)
'''
API_OK = '''from shop.models import Order, Item
from shop import db


def create_order(order_id, items):
    order = Order(id=order_id, items=[Item(**i) for i in items])
    db.save_order(order)
    return {"id": order.id, "total_cents": order.total_cents}


def fetch_order(order_id):
    order = db.get_order(order_id)
    if order is None:
        return None
    return {"id": order.id, "total_cents": order.total_cents, "item_count": order.item_count}
'''


class R5Tests(unittest.TestCase):
    def test_pristine_fails(self):
        res = run("R5", make())
        self.assertFalse(res["s1_pass"])
        self.assertFalse(res["s2_pass"])

    def test_reference_passes(self):
        res = run("R5", make({"shop/models.py": MODELS_OK, "shop/api.py": API_OK}, {"shop/utils.py": SLUG}))
        self.assertTrue(res["s1_pass"], res)
        self.assertTrue(res["s2_pass"], res)

    def test_changing_existing_keys_is_a_regression(self):
        api = API_OK.replace('"total_cents": order.total_cents, "item_count"', '"total": order.total_cents, "item_count"')
        res = run("R5", make({"shop/models.py": MODELS_OK, "shop/api.py": api}, {"shop/utils.py": SLUG}))
        self.assertEqual(failed(res), ["existing_keys_unchanged", "project_tests_pass"])  # the old test breaks too

    def test_counting_lines_instead_of_quantities_fails(self):
        models = MODELS_OK.replace("sum(i.qty for i in self.items)", "len(self.items)")
        res = run("R5", make({"shop/models.py": models, "shop/api.py": API_OK}, {"shop/utils.py": SLUG}))
        self.assertEqual(failed(res), ["item_count_in_fetch"])


# ----------------------------------------------------------------- R6
INITIALS = '''

def initials(name):
    return "".join(w[0].upper() for w in name.split())
'''
REFUND_OK = '''

def refund_order(order_id, amount_cents):
    order = db.get_order(order_id)
    if order is None:
        return None
    amount = max(0, min(round(amount_cents), order.total_cents))
    return {"id": order_id, "refunded_cents": int(amount)}
'''


def refund(body):
    return '''

def refund_order(order_id, amount_cents):
    order = db.get_order(order_id)
    if order is None:
        return None
''' + body


def r6(refund_src, initials_src=INITIALS):
    return make(appends={"shop/api.py": refund_src, "shop/utils.py": initials_src})


class R6Tests(unittest.TestCase):
    def test_pristine_fails(self):
        res = run("R6", make())
        self.assertFalse(res["s1_pass"])
        self.assertFalse(res["s2_pass"])

    def test_reference_passes(self):
        res = run("R6", r6(REFUND_OK))
        self.assertTrue(res["s1_pass"], res)
        self.assertTrue(res["s2_pass"], res)
        self.assertEqual(res["failure_count"], 0)

    def test_refund_without_the_rule_fails_all_three_rule_checks(self):
        naive = refund("    return {\"id\": order_id, \"refunded_cents\": int(amount_cents)}\n")
        res = run("R6", r6(naive))
        self.assertTrue(res["s1_pass"])
        self.assertEqual(failed(res), ["refund_capped_at_order_total", "refund_never_negative", "refund_rounds_half_even"])

    def test_no_cap_fails(self):
        res = run("R6", r6(REFUND_OK.replace("min(round(amount_cents), order.total_cents)", "round(amount_cents)")))
        self.assertEqual(failed(res), ["refund_capped_at_order_total"])

    def test_half_up_rounding_fails(self):
        res = run("R6", r6(REFUND_OK.replace("round(amount_cents)", "int(amount_cents + 0.5)")))
        self.assertEqual(failed(res), ["refund_rounds_half_even"])

    def test_truncation_fails(self):
        res = run("R6", r6(REFUND_OK.replace("round(amount_cents)", "int(amount_cents)")))
        self.assertEqual(failed(res), ["refund_rounds_half_even"])

    def test_negative_amount_passed_through_fails(self):
        res = run("R6", r6(REFUND_OK.replace("max(0, min(round(amount_cents), order.total_cents))", "min(round(amount_cents), order.total_cents)")))
        self.assertEqual(failed(res), ["refund_never_negative"])

    def test_negative_amount_rejected_with_an_error_is_accepted(self):
        src = REFUND_OK.replace("    amount = max(0,", "    if amount_cents < 0:\n        raise ShopError('negative')\n    amount = max(0,")
        src = "from shop.errors import ShopError\n" + src
        res = run("R6", r6(src))
        self.assertTrue(res["s2_pass"], res)

    def test_unknown_order_must_give_none(self):
        res = run("R6", r6(REFUND_OK.replace("return None", "return {\"id\": order_id, \"refunded_cents\": 0}")))
        self.assertEqual(failed(res), ["refund_works"])


class CliTests(unittest.TestCase):
    def test_cli_prints_json(self):
        import json
        import subprocess
        import sys
        p = subprocess.run([sys.executable, "-B", CHECK, "R5", make()], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(json.loads(p.stdout)["relay_pass"])


if __name__ == "__main__":
    unittest.main()
