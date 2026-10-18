import os
import shutil
import tempfile
import unittest
import uuid

from tests.support import GraphCase

from baton.capture import symbols
from baton.core import codegraph, sessions
from baton.hooks import events
from baton.hooks.config import Config

def _read(path):
    with open(path) as f:
        return f.read()


def _write(path, text):
    with open(path, "w") as f:
        f.write(text)


FIXTURE = os.path.join(os.path.dirname(__file__), "..", "evals", "clash", "fixture")


class ParserTests(unittest.TestCase):
    MODS = {"shop.db": "shop/db.py", "shop.api": "shop/api.py", "shop": "shop/__init__.py",
            "shop.models": "shop/models.py"}

    def test_resolves_module_alias_and_imported_names(self):
        src = ("from shop.models import Order\nfrom shop import db\n\n"
               "def create(oid):\n    o = Order(oid)\n    db.save_order(o)\n    return db.get_order(oid)\n")
        p = symbols.parse_file(src, "shop/api.py", self.MODS)
        self.assertIn(("shop/api.py::create", "shop/db.py::save_order"), p["edges"])
        self.assertIn(("shop/api.py::create", "shop/db.py::get_order"), p["edges"])
        self.assertIn(("shop/api.py::create", "shop/models.py::Order"), p["edges"])

    def test_methods_and_self_calls_and_relative_imports(self):
        src = ("from . import db\n\nclass S:\n    def a(self):\n        return self.b()\n    def b(self):\n"
               "        return db.get_order(1)\n")
        p = symbols.parse_file(src, "shop/svc.py", self.MODS)
        self.assertIn(("shop/svc.py::S.a", "shop/svc.py::S.b"), p["edges"])
        self.assertIn(("shop/svc.py::S.b", "shop/db.py::get_order"), p["edges"])

    def test_unknown_receivers_are_not_guessed(self):
        p = symbols.parse_file("def f(x):\n    return x.get_order()\n", "shop/api.py", self.MODS)
        self.assertEqual(p["edges"], [])

    def test_syntax_errors_and_huge_files_are_skipped(self):
        self.assertIsNone(symbols.parse_file("def (:\n", "a.py", {}))
        self.assertIsNone(symbols.parse_file("x=1\n" * 100000, "a.py", {}))


class BreakingChangeTests(unittest.TestCase):
    def b(self, old, new):
        return [(x["qual"], x["reason"]) for x in symbols.breaking_changes(old, new)]

    def test_compatible_changes_are_silent(self):
        self.assertEqual(self.b("def f(a):\n pass\n", "def f(a, b=1):\n pass\n"), [])
        self.assertEqual(self.b("def f(a):\n pass\n", "def f(a, *args, **kw):\n pass\n"), [])
        self.assertEqual(self.b("def f(a):\n pass\n", "def f(a):\n return 1\n"), [])

    def test_breaking_changes_are_reported(self):
        self.assertTrue(self.b("def f(a):\n pass\n", "def f(a, b):\n pass\n"))        # new required
        self.assertTrue(self.b("def f(a, b):\n pass\n", "def f(b, a):\n pass\n"))     # reordered
        self.assertTrue(self.b("def f(a):\n pass\n", "def g(a):\n pass\n"))           # renamed
        self.assertTrue(self.b("def f(a, *, k=1):\n pass\n", "def f(a):\n pass\n"))   # kw removed

    def test_private_names_ignored(self):
        self.assertEqual(self.b("def _f(a):\n pass\n", "def _f(a, b):\n pass\n"), [])


class CodeGraphTests(GraphCase):
    def setUp(self):
        from baton.graph.client import Store
        self.store = Store("cg_" + uuid.uuid4().hex[:8])
        self.store.bootstrap()

    def tearDown(self):
        self.store.drop()

    def project(self):
        d = tempfile.mkdtemp(prefix="cg_")
        p = os.path.join(d, "p")
        shutil.copytree(FIXTURE, p)
        return p

    def test_project_index_links_callers(self):
        p = self.project()
        res = codegraph.index_project(self.store, p)
        self.assertGreater(res["indexed"], 3)
        callers = codegraph.callers_of(self.store, "shop/db.py", ["get_order"])
        self.assertTrue(any(c["path"] == "shop/api.py" for c in callers), callers)
        again = codegraph.index_project(self.store, p)
        self.assertEqual(again["indexed"], 0)  # incremental: unchanged files are skipped

    def test_breaking_edit_names_callers_and_who_is_in_them(self):
        p = self.project()
        a, b = "ga-" + uuid.uuid4().hex[:6], "gb-" + uuid.uuid4().hex[:6]
        os.environ["CLAUDE_PROJECT_DIR"] = p
        try:
            cfg = Config()
            events.on_session_start(self.store, {"session_id": a, "cwd": p}, cfg, now=100)
            sessions.begin_session(self.store, b, now=101)
            events.on_post_tool(self.store, {"session_id": b, "cwd": p, "tool_name": "Edit",
                                             "tool_input": {"file_path": os.path.join(p, "shop/api.py"),
                                                            "old_string": "x", "new_string": "y"},
                                             "tool_response": {"originalFile": _read(os.path.join(p, "shop/api.py"))}},
                                cfg, now=110)
            old = _read(os.path.join(p, "shop/db.py"))
            new = old.replace("def get_order(order_id):", "def get_order(order_id, tenant):")
            _write(os.path.join(p, "shop/db.py"), new)
            out = events.on_post_tool(self.store, {"session_id": a, "cwd": p, "tool_name": "Edit",
                                                   "tool_input": {"file_path": os.path.join(p, "shop/db.py"),
                                                                  "old_string": "def get_order(order_id):",
                                                                  "new_string": "def get_order(order_id, tenant):"},
                                                   "tool_response": {"originalFile": old}}, cfg, now=120)
            text = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("shop/api.py", text)
            self.assertIn("new required parameter tenant", text)
            self.assertIn("working in it now", text)
            # the same warning is not repeated
            again = events.on_post_tool(self.store, {"session_id": a, "cwd": p, "tool_name": "Edit",
                                                     "tool_input": {"file_path": os.path.join(p, "shop/db.py"),
                                                                    "old_string": "def get_order(order_id):",
                                                                    "new_string": "def get_order(order_id, tenant):"},
                                                     "tool_response": {"originalFile": old}}, cfg, now=125)
            self.assertIsNone(again)
        finally:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def test_compatible_change_is_silent(self):
        p = self.project()
        a = "gc-" + uuid.uuid4().hex[:6]
        codegraph.index_project(self.store, p)
        old = _read(os.path.join(p, "shop/db.py"))
        new = old.replace("def get_order(order_id):", "def get_order(order_id, default=None):")
        self.assertIsNone(codegraph.impact(self.store, a, "shop/db.py", symbols.breaking_changes(old, new)))


if __name__ == "__main__":
    unittest.main()
