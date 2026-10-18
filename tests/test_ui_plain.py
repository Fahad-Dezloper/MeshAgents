import json
import os
import threading
import time
import unittest
import urllib.request
import uuid

from tests.support import DB_UP
from tests.ui_seed import HOSTILE, seed

from baton.core import notices, sessions
from baton.graph.client import Store
from baton.ui import plain, server, state

STATIC = os.path.join(os.path.dirname(server.__file__), "static", "index.html")
PRE = "You are an engineer working in /work/shop. Your ticket: "


class PlainWordsCase(unittest.TestCase):
    def test_task_line_skips_preamble_and_label(self):
        self.assertEqual(plain.plain_task(PRE + "Ticket 12: add a tenant flag to get_order"), "Add a tenant flag to get_order")
        self.assertEqual(plain.plain_task("You are an engineer working in the shop repo. Add a CSV export. Do not touch tests."), "Add a CSV export")
        long = plain.plain_task("Ticket 3: " + "make the report page much faster for large accounts " * 3)
        self.assertLessEqual(len(long), 61)
        self.assertTrue(long.endswith("…"))
        self.assertEqual(plain.plain_task("session x (no prompt yet)", has_goal=False), "Waiting for its first task")
        self.assertNotIn("You are", plain.plain_task("You are an engineer working in /x."))

    def test_change_sentences(self):
        t = "interface change in shop/db.py; signature changed: get_order(order_id) -> get_order(order_id, tenant)"
        self.assertEqual(plain.plain_change("interface", t, ["shop/db.py"]), "changed get_order: it now needs a tenant")
        self.assertEqual(plain.plain_change("rule", "never use sqlite"), "noted a rule: never use sqlite")
        self.assertEqual(plain.plain_change("rename", "renamed/moved a/x.py -> b/y.py"), "moved x.py to y.py")


@unittest.skipUnless(DB_UP, "FalkorDB not reachable")
class FriendlyStateCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store("ui_" + uuid.uuid4().hex[:8])
        cls.store.bootstrap()
        cls.empty = Store("ui_" + uuid.uuid4().hex[:8])
        cls.empty.bootstrap()
        cls.t = time.time()
        cls.ids = seed(cls.store, now=cls.t, hostile=True)
        notices.record(cls.store, cls.ids["B"], "collision", "Another helper is working in db.py", "exact text", ["shop/db.py"], now=cls.t - 20)
        notices.record(cls.store, cls.ids["B"], "hint", HOSTILE, HOSTILE, [], now=cls.t - 10)
        cls.srv = server.make_server(server.App(cls.store.workspace), "127.0.0.1", 0)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.store.drop()
        cls.empty.drop()

    def api(self):
        with urllib.request.urlopen("http://127.0.0.1:%d/api/state" % self.srv.server_address[1]) as r:
            return json.loads(r.read())

    def test_helpers_are_numbered_by_start_time(self):
        st = state.build_state(self.store, now=self.t)
        by = {s["owner"]: s["name"] for s in st["sessions"]}
        self.assertEqual((by[self.ids["C"]], by[self.ids["A"]], by[self.ids["B"]]), ("Helper 1", "Helper 2", "Helper 3"))
        again = state.build_state(self.store, now=self.t + 5)
        self.assertEqual({s["owner"]: s["name"] for s in again["sessions"]}, by)
        a = next(s for s in st["sessions"] if s["owner"] == self.ids["A"])
        self.assertLessEqual(len(a["task"]), 61)
        self.assertNotIn("Ticket 12", a["task"])

    def test_notices_and_feed(self):
        st = self.api()
        self.assertEqual(len(st["notices"]), 2)
        self.assertEqual(st["notices"][0]["at"] >= st["notices"][1]["at"], True)  # newest first
        self.assertEqual(st["notices"][0]["helper_name"], "Helper 3")
        self.assertIn(HOSTILE, [n["summary"] for n in st["notices"]])  # raw JSON, inert
        texts = [e["text"] for e in st["feed"]]
        self.assertIn("Helper 3 was told: Another helper is working in db.py", texts)
        self.assertIn("Helper 1 started", texts)
        self.assertTrue(any(t.startswith("Helper 2 changed") or t.startswith("Helper 2 now") for t in texts))
        self.assertEqual([e["at"] for e in st["feed"]], sorted((e["at"] for e in st["feed"]), reverse=True))
        self.assertLessEqual(len(st["feed"]), state.MAX_FEED)
        self.assertTrue(any(e["kind"] == "finish" and e["text"].startswith("Helper 1 finished") for e in st["feed"]))

    def test_missing_notices_are_empty_not_errors(self):
        st = state.build_state(self.empty)
        self.assertTrue(st["connected"])
        self.assertEqual((st["notices"], st["feed"]), ([], []))
        sessions.begin_session(self.empty, "sess-new", now=self.t)  # just started, no task yet
        st = state.build_state(self.empty, now=self.t + 1)
        s = st["sessions"][0]
        self.assertEqual((s["name"], s["has_goal"], s["task"]), ("Helper 1", False, "Waiting for its first task"))
        self.assertEqual([e["text"] for e in st["feed"]], ["Helper 1 started"])

    def test_page_uses_plain_words(self):
        src = open(STATIC, encoding="utf-8").read()
        for want in ("Working now", "Needs a look", "Finished", "Another helper is also in ", "Changing this may break ",
                     "Built on a note that was taken back", "Was warned and adjusted", "Live feed", "What the next helper will be told",
                     "Rules you told earlier", "Who else is busy", "What changed recently", "Where the last helper stopped",
                     "words of notes", "show the exact message", "Waiting for the first helper."):
            self.assertIn(want, src)
        for old in ("Handed off", "Needs attention", "may break callers", "builds on a retracted decision"):
            self.assertNotIn(old, src)
        self.assertNotIn("innerHTML", src)


if __name__ == "__main__":
    unittest.main()
