import io
import json
import unittest
import uuid

from tests.support import DB_UP
from tests.ui_codeseed import seed_code
from tests.ui_seed import seed

from baton import cli, humancli
from baton.core import provenance
from baton.graph.client import Store


@unittest.skipUnless(DB_UP, "FalkorDB not reachable")
class HumanCliCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ws = "ui_" + uuid.uuid4().hex[:8]
        cls.store = Store(cls.ws)
        cls.store.bootstrap()
        cls.ids = seed(cls.store)

    @classmethod
    def tearDownClass(cls):
        cls.store.drop()

    def run_cmd(self, *argv, stdin=None):
        buf = io.StringIO()
        out = humancli.Out(buf, color=False)
        cmd = argv[0]
        if cmd == "retract":
            code = humancli.cmd_retract(list(argv[1:]) + ["--workspace", self.ws], out, stdin=io.StringIO(stdin or ""))
        else:
            code = humancli.COMMANDS[cmd](list(argv[1:]) + ["--workspace", self.ws], out)
        return code, buf.getvalue()

    def test_status(self):
        code, text = self.run_cmd("status")
        self.assertEqual(code, 0)
        self.assertIn("2 live session(s)", text)
        self.assertIn("shop/db.py", text)
        self.assertNotIn("\033[", text)
        code, text = self.run_cmd("status", "--json")
        self.assertEqual(json.loads(text)["counts"]["collisions"], 1)

    def test_why_and_missing(self):
        code, text = self.run_cmd("why", self.ids["d2"])
        self.assertEqual(code, 0)
        self.assertIn("use sqlite for order storage", text)
        self.assertIn("Orders must survive restarts", text)
        code, text = self.run_cmd("why", "nope")
        self.assertEqual((code, text.strip()), (1, "not found: nope"))

    def test_handoff(self):
        code, text = self.run_cmd("handoff")
        self.assertEqual(code, 0)
        self.assertIn("HANDOFF", text)

    def test_color_only_on_tty(self):
        class Tty(io.StringIO):
            def isatty(self):
                return True
        self.assertIn("\033[", humancli.Out(Tty(), color=None).c("31", "x"))
        self.assertNotIn("\033[", humancli.Out(io.StringIO()).c("31", "x"))

    def test_retract_flow(self):
        code, text = self.run_cmd("retract", self.ids["finding"], "--reason", "stale", stdin="n\n")
        self.assertEqual(code, 1)
        self.assertIn("would taint 2".replace("would taint 2", "This would taint 2"), text)
        self.assertEqual(provenance.get_finding(self.store, self.ids["finding"])["status"], "open")
        code, text = self.run_cmd("retract", self.ids["finding"], "--reason", "stale", "--yes")
        self.assertEqual(code, 0)
        self.assertIn("tainted 2 decision(s)", text)
        self.assertEqual(provenance.get_finding(self.store, self.ids["finding"])["status"], "retracted")
        code, text = self.run_cmd("status")
        self.assertIn("tainted", text)

    def test_impact_and_status_code_line(self):
        other = Store("ui_" + uuid.uuid4().hex[:8])
        other.bootstrap()
        self.addCleanup(other.drop)
        seed_code(other)
        self.ws = other.workspace  # instance attribute only; the class workspace is untouched
        code, text = self.run_cmd("impact", "shop/db.py")
        self.assertEqual(code, 0)
        self.assertIn("shop/api.py", text)
        self.assertIn("being edited by sess-B", text)
        self.assertIn("fetch_order calls get_order", text)
        code, text = self.run_cmd("impact", "shop/nothing.py")
        self.assertIn("Nothing indexed", text)
        code, text = self.run_cmd("status")
        self.assertRegex(text, r"code graph: \d+ file\(s\) indexed")

    def test_dispatch_from_main_cli(self):
        self.assertTrue(callable(cli.main))


if __name__ == "__main__":
    unittest.main()
