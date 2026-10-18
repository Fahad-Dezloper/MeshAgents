import os
import unittest
from unittest import mock

from baton import demo_kit


class DemoKitTests(unittest.TestCase):
    def test_default_paths(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            for k in ("MESHAGENTS_DEMO_DIR", "MESHAGENTS_DEMO_PID"):
                os.environ.pop(k, None)
            self.assertEqual(demo_kit.demo_dir(), os.path.expanduser("~/meshagents-demo"))
            self.assertEqual(demo_kit.pid_file(), os.path.expanduser("~/.meshagents-demo.pid"))
            self.assertTrue(demo_kit.log_file().endswith(".meshagents-demo.log"))

    def test_env_overrides(self):
        with mock.patch.dict(os.environ, {"MESHAGENTS_DEMO_DIR": "/tmp/x-demo", "MESHAGENTS_DEMO_PID": "/tmp/p.pid"}):
            self.assertEqual(demo_kit.demo_dir(), "/tmp/x-demo")
            self.assertEqual(demo_kit.pid_file(), "/tmp/p.pid")

    def test_plugin_and_fixture_exist(self):
        self.assertTrue(os.path.isfile(os.path.join(demo_kit.plugin_dir(), "hooks", "hooks.json")))
        self.assertTrue(os.path.isfile(os.path.join(demo_kit.fixture_dir(), "shop", "db.py")))

    def test_workspace_matches_hooks(self):
        from baton.service import default_workspace

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BATON_WORKSPACE", None)
            self.assertEqual(demo_kit.workspace_for("/tmp/zz"), default_workspace("/tmp/zz"))
        with mock.patch.dict(os.environ, {"BATON_WORKSPACE": "demo_x"}):
            self.assertEqual(demo_kit.workspace_for("/tmp/zz"), "demo_x")

    def test_instructions(self):
        home = os.path.expanduser("~")
        text = demo_kit.instructions(home + "/meshagents-demo", "http://127.0.0.1:7777", "/repo/plugin")
        self.assertIn("cd ~/meshagents-demo && claude --plugin-dir /repo/plugin", text)
        self.assertIn("http://127.0.0.1:7777", text)
        for p in demo_kit.PROMPTS:
            self.assertIn(p, text)
        glob = demo_kit.instructions(home + "/meshagents-demo", "u", "/repo/plugin", global_plugin=True)
        self.assertNotIn("--plugin-dir", glob)

    def test_prompts_carry_the_rule(self):
        self.assertIn("never use sqlite", demo_kit.PROMPTS[0])
        self.assertIn("fetch_order_for(order_id, tenant)", demo_kit.PROMPTS[1])

    def test_create_project_and_refuse_foreign_dir(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            proj = os.path.join(tmp, "demo")
            demo_kit.create_project(proj)
            self.assertTrue(os.path.isdir(os.path.join(proj, ".git")))
            self.assertTrue(os.path.isfile(os.path.join(proj, "shop", "db.py")))
            self.assertFalse(os.path.exists(os.path.join(proj, "CLAUDE.md")))
            open(os.path.join(proj, "junk"), "w").close()
            demo_kit.create_project(proj)  # reset wipes our own folder
            self.assertFalse(os.path.exists(os.path.join(proj, "junk")))
            foreign = os.path.join(tmp, "mine")
            os.makedirs(foreign)
            with self.assertRaises(RuntimeError):
                demo_kit.create_project(foreign)

    def test_usage_error(self):
        self.assertEqual(demo_kit.main(["bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
