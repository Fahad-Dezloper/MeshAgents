import io
import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid

from tests.support import DB_UP
from tests.test_cochange import make_repo

from baton import humancli
from baton.core import cochange, provenance, rules, sessions
from baton.graph.client import Store
from baton.hooks import events
from baton.hooks.config import Config
from baton.ui import server, state

SPEC = ("Build the order import feature in six steps. Step 1: parser. Step 2: validator. Step 3: store. "
        "Step 4: dedupe by external id. Step 5: audit log line per import. Step 6: summary report. "
        "Do steps 1 to 3 today, the rest tomorrow. FYI never use sqlite here, the server is read-only.")


@unittest.skipUnless(DB_UP, "FalkorDB not reachable")
class MemoryUiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = "ui_" + uuid.uuid4().hex[:8]
        cls.store = Store(cls.ws)
        cls.store.bootstrap()
        cls.empty = Store("ui_" + uuid.uuid4().hex[:8])
        cls.empty.bootstrap()
        cls.a = "ma-" + uuid.uuid4().hex[:6]
        cfg = Config()
        t = time.time()
        events.on_session_start(cls.store, {"session_id": cls.a}, cfg, now=t - 300)
        events.on_prompt(cls.store, {"session_id": cls.a, "prompt": SPEC}, cfg, now=t - 290)
        events.on_prompt(cls.store, {"session_id": cls.a, "prompt": "Step 4: dedupe by external id, then also add a CSV export."}, cfg, now=t - 200)
        events.on_stop(cls.store, {"session_id": cls.a, "last_assistant_message": "Done with steps 1-3."}, cfg, now=t - 100)
        events.on_session_end(cls.store, {"session_id": cls.a}, cfg, now=t - 90)
        cls.tmp = tempfile.TemporaryDirectory()
        make_repo(cls.tmp.name)
        cochange.index_project(cls.store, cls.tmp.name, budget_s=10)
        cls.srv = server.make_server(server.App(cls.ws), "127.0.0.1", 0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.store.drop()
        cls.empty.drop()
        cls.tmp.cleanup()

    def get(self, path):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.port, path)) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            e.read()
            return e.code, None

    def test_memory_matches_the_briefing_and_is_read_only(self):
        t = time.time()
        m = state.memory_state(self.store, now=t)
        before = self.store.rows("MATCH (h:Handoff) RETURN h.imported_by", read_only=True)
        self.assertFalse(m["empty"])
        self.assertEqual(m["text"], sessions.briefing(self.store, "__preview__", now=t))
        self.assertEqual(m["tokens"], round(m["chars"] / 4.0))
        self.assertTrue(any("never use sqlite" in r["text"] for r in m["rules"]))
        self.assertTrue(m["rules"][0]["id"].startswith("dec_rule_"))
        self.assertIn("Step 4: dedupe", m["handoff"]["spec"])
        self.assertEqual(m["handoff"]["note"], "Done with steps 1-3.")
        # building the preview did not mark the handoff as imported
        self.assertEqual([r[0] for r in before], [None])

    def test_empty_memory(self):
        m = state.memory_state(self.empty)
        self.assertTrue(m["empty"] and m["connected"])
        self.assertEqual((m["text"], m["tokens"], m["rules"]), ("", 0, []))

    def test_api_memory_and_together(self):
        code, m = self.get("/api/memory")
        self.assertEqual(code, 200)
        self.assertTrue(m["rules"] and m["handoff"])
        code, t = self.get("/api/together?path=shop/db.py")
        self.assertEqual(code, 200)
        got = {p["path"]: p for p in t["partners"]}
        self.assertEqual(t["total"], 12)
        self.assertEqual(got["tests/test_db.py"]["n"], 11)
        self.assertAlmostEqual(got["tests/test_db.py"]["ratio"], 11 / 12, places=2)
        self.assertLessEqual(len(t["partners"]), 10)

    def test_together_validates_the_path(self):
        for bad in ("", "/etc/passwd", "../x", "a/../../b", "a;b", "x" * 300, "a\\b"):
            self.assertEqual(self.get("/api/together?path=" + urllib.request.quote(bad))[0], 400, bad)
        self.assertEqual(self.get("/api/together")[0], 400)
        code, t = self.get("/api/together?path=nope/none.py")
        self.assertEqual((code, t["total"], t["partners"]), (200, 0, []))

    def run_cmd(self, ws, *argv):
        buf = io.StringIO()
        code = humancli.COMMANDS[argv[0]](list(argv[1:]) + ["--workspace", ws], humancli.Out(buf, color=False))
        return code, buf.getvalue()

    def test_cli_brief_and_rules(self):
        code, text = self.run_cmd(self.ws, "brief")
        self.assertEqual(code, 0)
        self.assertIn("Rules and facts stated earlier", text)
        self.assertRegex(text, r"about \d+ tokens")
        code, text = self.run_cmd(self.empty.workspace, "brief")
        self.assertIn("Nothing yet", text)
        code, text = self.run_cmd(self.ws, "rules")
        self.assertIn("dec_rule_", text)
        self.assertIn("never use sqlite", text)
        code, text = self.run_cmd(self.empty.workspace, "rules")
        self.assertIn("No rules captured yet", text)

    def test_retracted_rule_leaves_the_briefing(self):
        ws = Store("ui_" + uuid.uuid4().hex[:8])
        ws.bootstrap()
        self.addCleanup(ws.drop)
        rules.record(ws, "x-actor", "FYI we never use sqlite in this project, remember that.", now=time.time() - 50)
        rid = state.memory_state(ws)["rules"][0]["id"]
        provenance.retract(ws, rid, "human", reason="wrong")
        self.assertEqual(state.memory_state(ws)["rules"], [])


if __name__ == "__main__":
    unittest.main()
