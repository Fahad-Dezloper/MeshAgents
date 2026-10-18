import json
import os
import re
import threading
import unittest
import urllib.error
import urllib.request
import uuid

from tests.support import DB_UP
from tests.ui_seed import HOSTILE, seed

from baton.graph.client import Store
from baton.ui import server, state

STATIC = os.path.join(os.path.dirname(server.__file__), "static", "index.html")


@unittest.skipUnless(DB_UP, "FalkorDB not reachable")
class UiCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.empty_ws = "ui_" + uuid.uuid4().hex[:8]
        cls.ws = "ui_" + uuid.uuid4().hex[:8]
        cls.empty = Store(cls.empty_ws)
        cls.empty.bootstrap()
        cls.store = Store(cls.ws)
        cls.store.bootstrap()
        cls.ids = seed(cls.store, hostile=True)
        cls.srv = server.make_server(server.App(cls.ws), "127.0.0.1", 0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.store.drop()
        cls.empty.drop()

    def get(self, path, method="GET", headers=None):
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers

    def test_empty_state_shape(self):
        st = state.build_state(self.empty)
        self.assertTrue(st["connected"])
        self.assertEqual(st["sessions"], [])
        self.assertEqual(st["counts"]["live_sessions"], 0)
        self.assertEqual(set(st), set(state.empty_state("x", 0)))

    def test_seeded_state(self):
        st = state.build_state(self.store)
        c = st["counts"]
        self.assertEqual((c["live_sessions"], c["open_decisions"], c["collisions"], c["handoffs"]), (2, 3, 1, 1))
        live = [s for s in st["sessions"] if s["status"] == "live"]
        self.assertEqual({s["owner"] for s in live}, {self.ids["A"], self.ids["B"]})
        self.assertTrue(all(s["collides_with"][0]["file"] == "shop/db.py" for s in live))
        self.assertEqual(st["files"][0]["path"], "shop/db.py")
        self.assertEqual(st["files"][0]["session_count"], 2)
        d2 = next(d for d in st["decisions"] if d["id"] == self.ids["d2"])
        self.assertEqual(d2["based_on"], [self.ids["d1"]])
        self.assertTrue(st["graph"]["nodes"] and st["graph"]["edges"])

    def test_db_down_is_graceful(self):
        st = state.build_state(Store(self.ws, host="127.0.0.1", port=1))
        self.assertFalse(st["connected"])
        self.assertTrue(st["error"])

    def test_provenance_preview_is_read_only(self):
        v = state.provenance_view(self.store, self.ids["finding"])
        self.assertEqual(len(v["would_taint"]), 2)
        again = state.provenance_view(self.store, self.ids["finding"])
        self.assertEqual(again["root"]["status"], "open")  # nothing was written
        self.assertIsNone(state.provenance_view(self.store, "nope"))

    def test_routes(self):
        code, body, hdr = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn(b"baton", body)
        self.assertIn("default-src 'none'", hdr["Content-Security-Policy"])
        code, body, _ = self.get("/api/state")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["workspace"], self.ws)
        code, body, _ = self.get("/api/why?id=" + self.ids["d2"])
        self.assertEqual(code, 200)
        self.assertEqual(len(json.loads(body)["upstream"]), 2)
        self.assertEqual(self.get("/api/why?id=nope")[0], 404)
        self.assertEqual(self.get("/api/why")[0], 400)
        self.assertEqual(self.get("/etc/passwd")[0], 404)
        self.assertEqual(self.get("/static/../server.py")[0], 404)

    def test_rejects_non_get_and_foreign_host(self):
        for m in ("POST", "PUT", "DELETE", "PATCH"):
            self.assertEqual(self.get("/api/state", method=m)[0], 405, m)
        self.assertEqual(self.get("/api/state", headers={"Host": "evil.example"})[0], 403)

    def test_hostile_text_stays_raw_json(self):
        code, body, hdr = self.get("/api/state")
        texts = [d["text"] for d in json.loads(body)["decisions"]]
        self.assertIn(HOSTILE, texts)
        self.assertTrue(hdr["Content-Type"].startswith("application/json"))

    def test_page_never_uses_innerhtml(self):
        src = open(STATIC, encoding="utf-8").read()
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            self.assertNotIn(bad, src)
        self.assertIsNone(re.search(r"https?://(?!127\.0\.0\.1|www\.w3\.org)", src))  # no CDN, works offline


if __name__ == "__main__":
    unittest.main()
