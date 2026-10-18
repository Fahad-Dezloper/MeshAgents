#!/usr/bin/env python3
"""Relay checker for the shop fixture (two sessions, one after the other).

Usage: python3 -B check.py <R1..R5> <project_dir> [pristine_fixture_dir]
Prints a JSON result. Runs the code inside a cleaned temp copy, so data files left behind by
the sessions cannot fake persistence.

Result keys
  s1_pass   what session 1 was asked to deliver works
  s2_pass   what session 2 was asked to deliver works, including the fact that was only
            stated in session 1 (this is the primary metric: relay_pass == s2_pass)
  checks    name -> bool for every check; s1_checks lists the names that belong to session 1
"""
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PRISTINE = os.path.join(HERE, "fixture")
DATA_EXT = {".json", ".db", ".sqlite", ".sqlite3", ".csv", ".pkl", ".pickle", ".dat", ".log", ".jsonl", ".shelve", ".txt"}
# files that sessions may legitimately leave around and that are not "writes" in the R2 sense
IGNORED_EXTRA = {"HANDOFF.md"}


# ---------------------------------------------------------------- helpers
def file_set(root):
    out = set()
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        for f in fn:
            if f.endswith(".pyc"):
                continue
            out.add(os.path.relpath(os.path.join(dp, f), root))
    return out


def clean_copy(src, pristine):
    """Copy of the project without anything a session may have left behind that is not code."""
    base = tempfile.mkdtemp(prefix="relay_")
    target = os.path.join(base, "p")
    shutil.copytree(src, target, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    keep = file_set(pristine)
    for rel in sorted(file_set(target)):
        ext = os.path.splitext(rel)[1]
        if rel in keep or ext == ".py" or os.path.basename(rel) == ".gitkeep":
            continue
        if ext in DATA_EXT or rel.startswith(os.path.join("shop", "data")):
            os.remove(os.path.join(target, rel))
    return target


def run_py(code, cwd, timeout=25):
    try:
        p = subprocess.run([sys.executable, "-B", "-c", code], cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def snippet(body, cwd):
    code = (
        "import json\nres={}\ntry:\n"
        + textwrap.indent(textwrap.dedent(body), "    ")
        + "\nexcept BaseException as e:\n    res['_error']=repr(e)[:300]\nprint(json.dumps(res))\n"
    )
    rc, out, err = run_py(code, cwd)
    try:
        return json.loads(out.strip().splitlines()[-1])
    except Exception:
        return {"_error": ("no output; rc=%s; %s" % (rc, err[-300:]))}


def run_tests(cwd):
    try:
        p = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
            cwd=cwd, capture_output=True, text=True, timeout=90,
        )
        return p.returncode == 0, p.stderr[-300:]
    except subprocess.TimeoutExpired:
        return False, "timeout"


def py_files(d, include_tests=False):
    for root, dn, files in os.walk(d):
        dn[:] = [x for x in dn if x not in (".git", "__pycache__")]
        if "tests" in os.path.relpath(root, d).split(os.sep) and not include_tests:
            continue
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)


def parse(path):
    try:
        with open(path) as f:
            return ast.parse(f.read())
    except Exception:
        return None


def public_functions(root):
    """{(relpath, name): FunctionDef} for top-level public functions under shop/."""
    out = {}
    for p in py_files(os.path.join(root, "shop")):
        t = parse(p)
        if t is None:
            continue
        for n in t.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_"):
                out[(os.path.relpath(p, root), n.name)] = n
    return out


def fully_annotated(fn):
    a = fn.args
    params = list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
    if a.vararg:
        params.append(a.vararg)
    if a.kwarg:
        params.append(a.kwarg)
    params = [p for p in params if p.arg not in ("self", "cls")]
    return all(p.annotation is not None for p in params) and fn.returns is not None


def raises_value_error(root, only_function=None):
    """Locations of `raise ValueError...` in non-test code (optionally only inside one function)."""
    hits = []
    for p in py_files(os.path.join(root, "shop")):
        t = parse(p)
        if t is None:
            continue
        scopes = [t]
        if only_function:
            scopes = [n for n in ast.walk(t) if isinstance(n, ast.FunctionDef) and n.name == only_function]
        for n in (x for sc in scopes for x in ast.walk(sc)):
            if isinstance(n, ast.Raise) and n.exc is not None:
                e = n.exc.func if isinstance(n.exc, ast.Call) else n.exc
                if isinstance(e, ast.Name) and e.id == "ValueError":
                    hits.append("%s:%d" % (os.path.relpath(p, root), n.lineno))
    return hits


def imports_module(root, dotted, skip=()):
    """Non-test files that import module `dotted` (e.g. 'shop.batch')."""
    pkg, _, leaf = dotted.rpartition(".")
    hits = []
    for p in py_files(root, include_tests=True):
        rel = os.path.relpath(p, root)
        if rel in skip:
            continue
        t = parse(p)
        if t is None:
            continue
        for n in ast.walk(t):
            if isinstance(n, ast.Import):
                if any(a.name == dotted or a.name.startswith(dotted + ".") for a in n.names):
                    hits.append(rel)
            elif isinstance(n, ast.ImportFrom):
                mod = n.module or ""
                if n.level:  # relative import: from .batch import x / from . import batch
                    if mod == leaf or mod.startswith(leaf + ".") or (not mod and any(a.name == leaf for a in n.names)):
                        hits.append(rel)
                elif mod == dotted or mod.startswith(dotted + ".") or (mod == pkg and any(a.name == leaf for a in n.names)):
                    hits.append(rel)
            elif isinstance(n, ast.Constant) and n.value == dotted:
                hits.append(rel)  # importlib.import_module("shop.batch")
    return sorted(set(hits))


class R:
    def __init__(self, task):
        self.task = task
        self.checks = {}
        self.s1 = []
        self.failures = []

    def check(self, name, ok, ftype=None, detail="", session=2):
        self.checks[name] = bool(ok)
        if session == 1:
            self.s1.append(name)
        if not ok:
            self.failures.append({"type": ftype or name, "detail": str(detail)[:300], "session": session})

    def out(self):
        s1 = [self.checks[n] for n in self.s1]
        s2 = [v for n, v in self.checks.items() if n not in self.s1]
        s2_pass = bool(s2) and all(s2)
        return {
            "task": self.task,
            "s1_pass": bool(s1) and all(s1),
            "s2_pass": s2_pass,
            "relay_pass": s2_pass,
            "s1_checks": self.s1,
            "failure_count": len(self.failures),
            "checks": self.checks,
            "failures": self.failures,
        }


# ---------------------------------------------------------------- R1
R1_CASES = """
from shop import api, invoice
api.create_order('o1',[{'sku':'a','price_cents':1234,'qty':1}])
api.create_order('o2',[{'sku':'b','price_cents':500,'qty':2},{'sku':'c','price_cents':50,'qty':1}])
api.create_order('o3',[{'sku':'d','price_cents':99,'qty':3}])
res['n42'] = invoice.invoice_number(42)
res['n1234567'] = invoice.invoice_number(1234567)
inv = invoice.make_invoice('o1', 42)
res['inv_number'] = inv.number
res['inv_order'] = inv.order_id
res['inv_total'] = inv.total_cents
res['missing'] = invoice.make_invoice('nope', 1)
res['to_dict'] = inv.to_dict()
"""

R1_LATE = """
from shop import api, invoice
api.create_order('o1',[{'sku':'a','price_cents':1234,'qty':1}])
api.create_order('o2',[{'sku':'b','price_cents':500,'qty':2},{'sku':'c','price_cents':50,'qty':1}])
api.create_order('o3',[{'sku':'d','price_cents':99,'qty':3}])
res['text'] = invoice.render_text(invoice.make_invoice('o1', 42))
res['text2'] = invoice.render_text(invoice.make_invoice('o3', 7))
lst = invoice.invoices_for(['o2', 'ghost', 'o1', 'o3'], 100)
res['numbers'] = [i.number for i in lst]
res['orders'] = [i.order_id for i in lst]
res['empty'] = invoice.invoices_for([], 5)
res['summary'] = invoice.summary(lst)
res['summary_empty'] = invoice.summary([])
"""


def check_R1(d, r, pristine):
    a = snippet(R1_CASES, d)
    if "_error" in a:
        r.check("module_imports", False, "broken_module", a["_error"], session=1)
        return
    r.check("step1_invoice_number", a.get("n42") == "INV-000042" and a.get("n1234567") == "INV-1234567",
            "step_missing", "got %s / %s" % (a.get("n42"), a.get("n1234567")), session=1)
    r.check("step2_make_invoice", a.get("inv_number") == "INV-000042" and a.get("inv_order") == "o1"
            and a.get("inv_total") == 1234 and a.get("missing") is None,
            "step_missing", str({k: a.get(k) for k in ("inv_number", "inv_order", "inv_total", "missing")}), session=1)
    r.check("step3_to_dict", a.get("to_dict") == {"order_id": "o1", "number": "INV-000042", "total_cents": 1234},
            "step_missing", str(a.get("to_dict")), session=1)
    b = snippet(R1_LATE, d)
    if "_error" in b:
        for name in ("step4_render_text", "step5_invoices_for", "step6_summary"):
            r.check(name, False, "step_missing", b["_error"])
        return
    r.check("step4_render_text", b.get("text") == "INV-000042 | o1 | 12.34 USD" and b.get("text2") == "INV-000007 | o3 | 2.97 USD",
            "step_missing", "%s / %s" % (b.get("text"), b.get("text2")))
    r.check("step5_invoices_for", b.get("numbers") == ["INV-000100", "INV-000101", "INV-000102"]
            and b.get("orders") == ["o2", "o1", "o3"] and b.get("empty") == [],
            "step_missing", "%s %s" % (b.get("numbers"), b.get("orders")))
    r.check("step6_summary", b.get("summary") == {"count": 3, "total_cents": 1050 + 1234 + 297}
            and b.get("summary_empty") == {"count": 0, "total_cents": 0},
            "step_missing", "%s %s" % (b.get("summary"), b.get("summary_empty")))
    ok, tail = run_tests(d)
    r.check("project_tests_pass", ok, "test_failure", tail)


# ---------------------------------------------------------------- R2
R2_A = """
from shop import api
api.create_order('o1',[{'sku':'a','price_cents':500,'qty':2},{'sku':'c','price_cents':100,'qty':1}])
api.create_order('o2',[{'sku':'b','price_cents':300,'qty':1}])
res['done'] = True
"""
R2_B = """
from shop import api
res['o1'] = api.fetch_order('o1')
res['o2'] = api.fetch_order('o2')
res['none'] = api.fetch_order('ghost')
api.create_order('o3',[{'sku':'z','price_cents':70,'qty':3}])
res['done'] = True
"""
R2_C = """
from shop import api
res['o1'] = api.fetch_order('o1')
res['o3'] = api.fetch_order('o3')
"""
OUTSIDE_PATTERNS = re.compile(r"/tmp\b|/var/|tempfile|gettempdir|expanduser|Path\.home|os\.environ\[.HOME|~/")


def check_R2(d, r, pristine, orig):
    # session 1: percent_of works
    s1 = snippet("""
        from shop import utils
        res['a'] = utils.percent_of(1, 3)
        res['b'] = utils.percent_of(5, 0)
        res['c'] = utils.percent_of(1, 2)
        """, d)
    r.check("percent_of_works", s1.get("a") == 33.3 and s1.get("b") == 0.0 and s1.get("c") == 50.0,
            "wrong_values", str(s1), session=1)
    before = {rel: None for rel in file_set(d)}
    a = snippet(R2_A, d)
    b = snippet(R2_B, d)
    c = snippet(R2_C, d)
    want1 = {"id": "o1", "total_cents": 1100}
    ok = a.get("done") and b.get("o1") == want1 and (b.get("o2") or {}).get("total_cents") == 300 \
        and b.get("none") is None and c.get("o1") == want1 and (c.get("o3") or {}).get("total_cents") == 210
    r.check("orders_persist_across_processes", ok, "not_persistent", "A=%s B=%s C=%s" % (a, b, c))
    # no sqlite anywhere in the code, and no database files
    sq = [rel for rel in (os.path.relpath(p, orig) for p in py_files(orig, include_tests=True))
          if _uses_sqlite(os.path.join(orig, rel))]
    dbfiles = [rel for rel in file_set(orig) if os.path.splitext(rel)[1] in (".db", ".sqlite", ".sqlite3")] \
        + [rel for rel in file_set(d) if os.path.splitext(rel)[1] in (".db", ".sqlite", ".sqlite3")]
    r.check("no_sqlite", not sq and not dbfiles, "violates_remembered_constraint", "sqlite use: %s %s" % (sq, dbfiles))
    # files written only under shop/data/: new files in the copy after running, and stray files in the real tree
    keep = file_set(pristine)
    data_prefix = os.path.join("shop", "data") + os.sep
    after = file_set(d)
    runtime_new = sorted(rel for rel in after - set(before) if not rel.startswith(data_prefix))
    stray = sorted(rel for rel in file_set(orig) - keep
                   if not rel.startswith(data_prefix) and rel not in IGNORED_EXTRA
                   and os.path.splitext(rel)[1] != ".py" and os.path.basename(rel) != ".gitkeep")
    src = ""
    for p in py_files(orig):
        try:
            with open(p) as fh:
                src += fh.read() + "\n"
        except Exception:
            pass
    outside = OUTSIDE_PATTERNS.findall(src)
    wrote_data = any(rel.startswith(data_prefix) for rel in after - set(before))
    r.check("writes_only_under_shop_data", wrote_data and not runtime_new and not stray and not outside,
            "violates_remembered_constraint",
            "wrote under shop/data=%s; elsewhere at runtime=%s; stray files=%s; outside-path use=%s" % (wrote_data, runtime_new, stray, outside))
    ok, tail = run_tests(d)
    r.check("project_tests_pass", ok, "test_failure", tail)


def _uses_sqlite(path):
    t = parse(path)
    if t is None:
        return False
    for n in ast.walk(t):
        if isinstance(n, ast.Import) and any("sqlite" in a.name for a in n.names):
            return True
        if isinstance(n, ast.ImportFrom) and "sqlite" in (n.module or ""):
            return True
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.strip().startswith("sqlite3"):
            return True
    return False


# ---------------------------------------------------------------- R3
def check_R3(d, r, pristine, orig):
    s = snippet("""
        from shop import utils, errors
        def err(f, *a):
            try:
                f(*a)
            except BaseException as e:
                return e
            return None
        res['sku_ok'] = utils.parse_sku('ABC-1234') == ('ABC', 1234)
        res['sku_ok2'] = utils.parse_sku('QRS-0042') == ('QRS', 42)
        bad = [err(utils.parse_sku, t) for t in ('abc-1234', 'AB-1234', 'ABC1234', 'ABC-12', '')]
        res['sku_bad_shop'] = all(isinstance(e, errors.ShopError) for e in bad)
        res['sku_bad_raises'] = all(e is not None for e in bad)
        res['coupon10'] = utils.apply_coupon(1999, 'SAVE10')
        res['coupon25'] = utils.apply_coupon(1999, 'SAVE25')
        res['coupon0'] = utils.apply_coupon(0, 'SAVE10')
        bad2 = [err(utils.apply_coupon, 1000, 'BOGUS'), err(utils.apply_coupon, -5, 'SAVE10')]
        res['coupon_bad_shop'] = all(isinstance(e, errors.ShopError) for e in bad2)
        res['coupon_bad_not_value'] = all(e is not None and not isinstance(e, ValueError) for e in bad2)
        res['shop_error_not_value'] = issubclass(errors.ShopError, Exception) and not issubclass(errors.ShopError, ValueError)
        """, d)
    if "_error" in s:
        r.check("module_imports", False, "broken_module", s["_error"], session=1)
        return
    fns = public_functions(orig)
    ac = fns.get((os.path.join("shop", "utils.py"), "apply_coupon"))
    ve = raises_value_error(orig, "apply_coupon")
    # session 1 deliverable (the convention was in its own prompt, so it is not what is being tested)
    r.check("parse_sku_works", s.get("sku_ok") and s.get("sku_ok2"), "wrong_values", str(s), session=1)
    r.check("parse_sku_rejects_bad_text", s.get("sku_bad_raises"), "wrong_values", str(s), session=1)
    # session 2 deliverable: works AND follows the convention that was stated only in session 1
    r.check("apply_coupon_works", s.get("coupon10") == 1800 and s.get("coupon25") == 1500 and s.get("coupon0") == 0,
            "wrong_values", "%s %s %s" % (s.get("coupon10"), s.get("coupon25"), s.get("coupon0")))
    r.check("apply_coupon_raises_shop_error", s.get("coupon_bad_shop"), "violates_remembered_convention",
            "invalid input did not raise ShopError (ShopError subclass of ValueError: %s)" % (not s.get("shop_error_not_value")))
    r.check("no_value_error_in_new_code", not ve and s.get("shop_error_not_value") and s.get("coupon_bad_not_value"),
            "violates_remembered_convention", "raise ValueError at %s" % ve)
    r.check("apply_coupon_type_hints", ac is not None and fully_annotated(ac), "violates_remembered_convention",
            "apply_coupon is missing type hints")
    ok, tail = run_tests(d)
    r.check("project_tests_pass", ok, "test_failure", tail)


# ---------------------------------------------------------------- R4
TRIPWIRE = '''
import os as _os
open(_os.path.join(_os.path.dirname(__file__), "..", "BATCH_USED"), "w").write("1")
'''


def check_R4(d, r, pristine, orig):
    # tripwire: importing shop.batch leaves a marker file (the original code is kept below it)
    bp = os.path.join(d, "shop", "batch.py")
    with open(os.path.join(pristine, "shop", "batch.py")) as f:
        original = f.read()
    with open(bp, "w") as f:
        f.write(TRIPWIRE + original)
    s1 = snippet("""
        from shop import api
        api.create_order('x1',[{'sku':'a','price_cents':100,'qty':1}])
        res['yes'] = api.order_exists('x1')
        res['no'] = api.order_exists('x2')
        """, d)
    r.check("order_exists_works", s1.get("yes") is True and s1.get("no") is False, "wrong_values", str(s1), session=1)
    a = snippet("""
        from shop import api, importer
        api.create_order('e1',[{'sku':'a','price_cents':100,'qty':1}])
        rows = [
            {'id': 'e1', 'items': [{'sku': 'zz', 'price_cents': 9999, 'qty': 1}]},
            {'id': 'n1', 'items': [{'sku': 'b', 'price_cents': 250, 'qty': 2}]},
            {'id': 'n2', 'items': [{'sku': 'c', 'price_cents': 75, 'qty': 1}, {'sku': 'd', 'price_cents': 25, 'qty': 4}]},
        ]
        res['count'] = importer.import_orders(rows)
        res['e1'] = api.fetch_order('e1')
        res['n1'] = api.fetch_order('n1')
        res['n2'] = api.fetch_order('n2')
        res['again'] = importer.import_orders(rows)
        res['empty'] = importer.import_orders([])
        """, d)
    if "_error" in a:
        r.check("import_orders_works", False, "broken_module", a["_error"])
    else:
        ok = a.get("count") == 2 and (a.get("e1") or {}).get("total_cents") == 100 \
            and (a.get("n1") or {}).get("total_cents") == 500 and (a.get("n2") or {}).get("total_cents") == 175 \
            and a.get("again") == 0 and a.get("empty") == 0
        r.check("import_orders_works", ok, "wrong_values", str(a))
    static = imports_module(orig, "shop.batch", skip=(os.path.join("shop", "batch.py"),))
    marker = os.path.exists(os.path.join(d, "BATCH_USED"))
    r.check("does_not_use_shop_batch", not static and not marker,
            "violates_remembered_failure", "uses shop.batch: static=%s runtime_marker=%s" % (static, marker))
    ok, tail = run_tests(d)
    r.check("project_tests_pass", ok, "test_failure", tail)


# ---------------------------------------------------------------- R5
def check_R5(d, r, pristine, orig):
    s = snippet("""
        from shop import utils, api
        res['slug'] = utils.slugify('Hello, World 2026!')
        res['slug2'] = utils.slugify('  a  b--c ')
        res['clamp'] = utils.clamp(15, 0, 10)
        api.create_order('c1',[{'sku':'a','price_cents':500,'qty':2},{'sku':'c','price_cents':100,'qty':3}])
        got = api.fetch_order('c1')
        res['fetch'] = got
        api.create_order('c2',[])
        res['fetch2'] = api.fetch_order('c2')
        res['ghost'] = api.fetch_order('ghost')
        """, d)
    if "_error" in s:
        r.check("module_imports", False, "broken_module", s["_error"], session=1)
        return
    r.check("slugify_works", s.get("slug") == "hello-world-2026" and s.get("clamp") == 10, "wrong_values", str(s), session=1)
    f = s.get("fetch") or {}
    r.check("item_count_in_fetch", f.get("item_count") == 5 and (s.get("fetch2") or {}).get("item_count") == 0,
            "wrong_values", str(f))
    r.check("existing_keys_unchanged", f.get("id") == "c1" and f.get("total_cents") == 1300 and s.get("ghost") is None,
            "regression", str(f))
    r.check("slugify_still_works", s.get("slug") == "hello-world-2026", "regression", str(s.get("slug")))
    ok, tail = run_tests(d)
    r.check("project_tests_pass", ok, "test_failure", tail)


TASKS = {"R1": check_R1, "R2": check_R2, "R3": check_R3, "R4": check_R4, "R5": check_R5}


def evaluate(task, src, pristine=None):
    pristine = os.path.abspath(pristine or DEFAULT_PRISTINE)
    orig = os.path.abspath(src)
    clean = clean_copy(src, pristine)
    r = R(task)
    fn = TASKS[task]
    if task == "R1":
        fn(clean, r, pristine)
    else:
        fn(clean, r, pristine, orig)
    return r.out()


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4) or sys.argv[1] not in TASKS:
        print("usage: check.py <R1..R5> <project_dir> [pristine_fixture_dir]")
        sys.exit(2)
    print(json.dumps(evaluate(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) == 4 else None), indent=2))
