import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(env_extra, code):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("BATON_", "MESHAGENTS_"))}
    env.update(env_extra)
    env["PYTHONPATH"] = os.path.join(ROOT, "src")
    return subprocess.run([sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, timeout=30)


class EnvAliasTest(unittest.TestCase):
    def test_new_name_sets_old_name(self):
        r = _run({"MESHAGENTS_WORKSPACE": "ws1", "MESHAGENTS_FALKORDB_HOST": "h1"},
                 "import os, baton; print(os.environ['BATON_WORKSPACE'], os.environ['BATON_FALKORDB_HOST'])")
        self.assertEqual(r.stdout.split(), ["ws1", "h1"], r.stderr)

    def test_explicit_old_name_wins(self):
        r = _run({"MESHAGENTS_WORKSPACE": "new", "BATON_WORKSPACE": "old"},
                 "import os, baton; print(os.environ['BATON_WORKSPACE'])")
        self.assertEqual(r.stdout.strip(), "old", r.stderr)

    def test_old_name_alone_still_works(self):
        r = _run({"BATON_WORKSPACE": "old"}, "import os, baton; print(os.environ['BATON_WORKSPACE'])")
        self.assertEqual(r.stdout.strip(), "old", r.stderr)

    def test_workspace_resolution_uses_alias(self):
        r = _run({"MESHAGENTS_WORKSPACE": "via_alias"},
                 "import os, baton; print(os.environ.get('BATON_WORKSPACE'))")
        self.assertEqual(r.stdout.strip(), "via_alias", r.stderr)


if __name__ == "__main__":
    unittest.main()
