"""Edits made through shell commands (sed -i, heredocs, redirects) are tracked like edits made with the edit tools."""

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
import uuid
from unittest import mock

from tests.support import GraphCase

from baton.capture import shellsnap, shellwrites
from baton.core import sessions
from baton.graph.client import Store
from baton.hooks import events
from baton.hooks.config import Config, load_config

DATA = os.path.join(os.path.dirname(__file__), "data", "shell_commands.jsonl")
PROJECT = "/app/project"


def load_cases():
    with open(DATA) as f:
        return [json.loads(line) for line in f if line.strip()]


class ExtractionTests(unittest.TestCase):
    def test_fixture_is_substantial(self):
        cases = load_cases()
        self.assertGreaterEqual(len([c for c in cases if c["source"] == "real"]), 100)
        self.assertGreaterEqual(len([c for c in cases if not c["expected_writes"]]), 30)

    def test_targets_on_recorded_and_synthetic_commands(self):
        for c in load_cases():
            got = shellwrites.target_paths(c["command"], PROJECT, PROJECT)
            self.assertEqual(sorted(got), sorted(c["expected_writes"]), c["command"][:200])

    def test_prefilter_agrees(self):
        for c in load_cases():
            self.assertEqual(shellwrites.is_write_like(c["command"]), c["write_like"], c["command"][:200])

    def test_read_only_commands_have_no_targets(self):
        for cmd in ["cat shop/api.py", "grep -rn 'x' . --include=*.py", "ls -la shop", "git ls-files",
                    "git status --short", "git diff HEAD > /dev/null", "python3 -B -m unittest discover -s tests",
                    "python3 -c \"print(open('shop/a.py').read())\"", "sed -n '1,5p' shop/api.py",
                    "find . -name '*.py' | xargs wc -l", "echo hi 2>&1 | head", "ls shop > /dev/null"]:
            self.assertFalse(shellwrites.is_write_like(cmd), cmd)
            self.assertEqual(shellwrites.target_paths(cmd, PROJECT, PROJECT), [], cmd)

    def test_base_directory_and_project_bounds(self):
        self.assertEqual(shellwrites.target_paths("cd shop && echo x > a.py", PROJECT, PROJECT), ["shop/a.py"])
        self.assertEqual(shellwrites.target_paths("echo x > a.py", PROJECT + "/shop", PROJECT), ["shop/a.py"])
        self.assertEqual(shellwrites.target_paths("echo x > /tmp/a.py", PROJECT, PROJECT), [])
        self.assertEqual(shellwrites.target_paths("echo x > ../a.py", PROJECT, PROJECT), [])
        self.assertEqual(shellwrites.target_paths("echo x > $HOME/a.py", PROJECT, PROJECT), [])

    def test_never_raises(self):
        for junk in ["", "'", "\"unterminated", "cat <<E\nx", "a >", ">>>", "$(", "`", "x" * 5000]:
            self.assertEqual(shellwrites.target_paths(junk, PROJECT, PROJECT), [])
            shellwrites.is_write_like(junk)
        self.assertEqual(shellwrites.target_paths(None, PROJECT, PROJECT), [])  # type: ignore[arg-type]
        self.assertFalse(shellwrites.is_write_like(None))  # type: ignore[arg-type]

    def test_glob_expands_only_to_existing_files(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "shop"))
            for n in ("a.py", "b.py"):
                open(os.path.join(d, "shop", n), "w").close()
            self.assertEqual(shellwrites.target_paths("sed -i 's/a/b/' shop/*.py", d, d), ["shop/a.py", "shop/b.py"])
            self.assertEqual(shellwrites.target_paths("sed -i 's/a/b/' shop/*.js", d, d), [])
            self.assertEqual(shellwrites.target_paths("cp shop/a.py shop", d, d), ["shop/a.py"])
        finally:
            shutil.rmtree(d, ignore_errors=True)


def make_project(n_extra=0):
    d = tempfile.mkdtemp(prefix="shellw-")
    os.makedirs(os.path.join(d, "shop"))
    files = {
        "shop/__init__.py": "",
        "shop/db.py": "def get_order(order_id):\n    return {'id': order_id}\n",
        "shop/api.py": "from shop import db\n\n\ndef fetch(order_id):\n    return db.get_order(order_id)\n",
        "shop/config.py": 'CONFIG = {\n    "timeout_seconds": 30,\n}\n',
    }
    for rel, text in files.items():
        with open(os.path.join(d, rel), "w") as f:
            f.write(text)
    for i in range(n_extra):
        sub = os.path.join(d, "pkg%d" % (i % 10))
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "m%d.py" % i), "w") as f:
            f.write("def f%d(a, b):\n    return a + b\n" % i)
    return d


def bash_payload(session, project, command):
    return {"session_id": session, "cwd": project, "tool_name": "Bash", "tool_input": {"command": command}}


def run_shell(project, command):
    subprocess.run(["bash", "-c", command], cwd=project, check=True, capture_output=True)


CHANGE_SIG = (
    "sed -i.bak 's/30,/45,/' shop/config.py\n"
    "python3 - <<'EOT'\n"
    "p='shop/db.py'\n"
    "s=open(p).read()\n"
    "s=s.replace(\"def get_order(order_id):\",\"def get_order(order_id, tenant):\")\n"
    "open(p,'w').write(s)\n"
    "EOT\n"
)


class ShellEditIntegrationTests(GraphCase):
    def setUp(self):
        self.store = Store("t_" + uuid.uuid4().hex[:10])  # own graph per test: the paths below repeat
        self.store.bootstrap()
        self.project = make_project()
        os.environ["CLAUDE_PROJECT_DIR"] = self.project
        self.a = "A-" + uuid.uuid4().hex[:6]
        self.b = "B-" + uuid.uuid4().hex[:6]
        self.cfg = Config()

    def tearDown(self):
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        shellsnap.forget(events._snap_dir(self.a), self.a)
        shutil.rmtree(self.project, ignore_errors=True)
        self.store.drop()

    def hook(self, name, payload, now):
        return events.HANDLERS[name](self.store, payload, self.cfg, now=now)

    def touched(self, actor):
        rows = self.store.rows("MATCH (t:Task {id: $id})-[:TOUCHES]->(a:Artifact) RETURN a.path",
                               {"id": sessions.session_task_id(actor)}, read_only=True)
        return sorted(r[0] for r in rows)

    def test_shell_edit_is_recorded_and_collides_with_next_session(self):
        self.hook("session-start", {"session_id": self.a, "cwd": self.project}, 1_000_000)
        self.hook("session-start", {"session_id": self.b, "cwd": self.project}, 1_000_001)
        pre = bash_payload(self.a, self.project, CHANGE_SIG)
        self.assertIsNone(self.hook("pre-tool", pre, 1_000_010))  # nothing to warn about yet
        run_shell(self.project, CHANGE_SIG)
        out = self.hook("post-tool", pre, 1_000_020)
        self.assertEqual(self.touched(self.a), ["shop/config.py", "shop/db.py"])
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Callers elsewhere that may now break", ctx)
        self.assertIn("shop/api.py", ctx)
        self.assertIn("tenant", ctx)
        self.assertFalse(os.path.exists(shellsnap.snap_path(events._snap_dir(self.a), self.a)))  # consumed

        # session B now meets session A's work before writing the same file through the shell
        pre_b = bash_payload(self.b, self.project, "sed -i 's/get_order/fetch_order/' shop/db.py")
        out_b = self.hook("pre-tool", pre_b, 1_000_030)
        ctx_b = out_b["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Possible collision on shop/db.py", ctx_b)
        self.assertIn("interface decision by", ctx_b)
        self.assertIn("tenant", ctx_b)
        # the same warning is not repeated
        self.assertIsNone(self.hook("pre-tool", pre_b, 1_000_031))

    def test_config_change_becomes_a_decision(self):
        self.hook("session-start", {"session_id": self.a, "cwd": self.project}, 2_000_000)
        cmd = "sed -i.bak 's/30,/45,/' shop/config.py"
        pre = bash_payload(self.a, self.project, cmd)
        self.hook("pre-tool", pre, 2_000_001)
        run_shell(self.project, cmd)
        self.hook("post-tool", pre, 2_000_002)
        rows = self.store.rows("MATCH (d:Decision {author: $a, kind: 'config'}) RETURN d.text",
                               {"a": self.a}, read_only=True)
        self.assertTrue(rows and "timeout_seconds" in rows[0][0], rows)

    def test_new_file_via_redirect_is_touched_and_read_only_is_silent(self):
        self.hook("session-start", {"session_id": self.a, "cwd": self.project}, 3_000_000)
        cmd = "cat > shop/report.py <<'EOT'\ndef summary(o):\n    return o\nEOT"
        pre = bash_payload(self.a, self.project, cmd)
        self.hook("pre-tool", pre, 3_000_001)
        run_shell(self.project, cmd)
        self.hook("post-tool", pre, 3_000_002)
        self.assertIn("shop/report.py", self.touched(self.a))
        ro = bash_payload(self.a, self.project, "cat shop/db.py && git status --short")
        self.assertIsNone(self.hook("pre-tool", ro, 3_000_010))
        self.assertIsNone(self.hook("post-tool", ro, 3_000_011))
        self.assertFalse(os.path.exists(shellsnap.snap_path(events._snap_dir(self.a), self.a)))

    def test_without_snapshot_targets_are_still_touched(self):
        self.hook("session-start", {"session_id": self.a, "cwd": self.project}, 4_000_000)
        cmd = "echo '# note' >> shop/api.py"
        pre = bash_payload(self.a, self.project, cmd)
        with mock.patch.object(shellsnap, "take", return_value=False):
            self.hook("pre-tool", pre, 4_000_001)
        run_shell(self.project, cmd)
        self.hook("post-tool", pre, 4_000_002)
        self.assertEqual(self.touched(self.a), ["shop/api.py"])

    def test_policy_deny_applies_to_shell_writes(self):
        self.hook("session-start", {"session_id": self.a, "cwd": self.project}, 5_000_000)
        pre = bash_payload(self.a, self.project, "echo x >> shop/db.py")
        self.hook("pre-tool", pre, 5_000_001)
        run_shell(self.project, "echo x >> shop/db.py")
        self.hook("post-tool", pre, 5_000_002)
        cfg = Config(policy="deny")
        out = events.HANDLERS["pre-tool"](self.store, bash_payload(self.b, self.project, "sed -i 's/x/y/' shop/db.py"),
                                          cfg, now=5_000_010)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_switch_off(self):
        cfg = Config(shell_writes=False)
        pre = bash_payload(self.a, self.project, "echo x >> shop/db.py")
        self.assertIsNone(events.HANDLERS["pre-tool"](self.store, pre, cfg, now=6_000_000))
        self.assertFalse(os.path.exists(shellsnap.snap_path(events._snap_dir(self.a), self.a)))
        self.assertIsNone(events.HANDLERS["post-tool"](self.store, pre, cfg, now=6_000_001))
        self.assertEqual(self.touched(self.a), [])
        with mock.patch.dict(os.environ, {"BATON_SHELL_WRITES": "0"}):
            self.assertFalse(load_config(self.project).shell_writes)
        self.assertTrue(load_config(self.project).shell_writes)

    def test_unwritable_temp_dir_stays_fail_open(self):
        self.hook("session-start", {"session_id": self.a, "cwd": self.project}, 7_000_000)
        blocker = os.path.join(self.project, "not-a-dir")
        with open(blocker, "w") as f:
            f.write("x")

        def bad(actor):  # a directory cannot be created below a regular file
            return os.path.join(blocker, "sub", "warned-x.json")

        cmd = "echo x >> shop/api.py"
        pre = bash_payload(self.a, self.project, cmd)
        with mock.patch.object(events, "_warned_path", bad):
            self.assertIsNone(self.hook("pre-tool", pre, 7_000_001))
            run_shell(self.project, cmd)
            self.assertIsNone(self.hook("post-tool", pre, 7_000_002))
        self.assertEqual(self.touched(self.a), ["shop/api.py"])  # fell back to the command's own target


class SnapshotCostTests(unittest.TestCase):
    def setUp(self):
        self.dirs = []

    def tearDown(self):
        for d in self.dirs:
            shutil.rmtree(d, ignore_errors=True)

    def project(self, n):
        d = make_project(n)
        self.dirs.append(d)
        return d

    def test_snapshot_and_diff_of_300_files_is_fast_and_correct(self):
        proj = self.project(300)
        snapdir = tempfile.mkdtemp()
        self.dirs.append(snapdir)
        best = 1e9
        for i in range(3):
            t = time.perf_counter()
            self.assertTrue(shellsnap.take(proj, snapdir, "perf"))
            res = shellsnap.diff(proj, snapdir, "perf")
            best = min(best, time.perf_counter() - t)
            self.assertEqual(res, [])
        self.assertLess(best, 0.12, "snapshot+diff took %.0f ms" % (best * 1000))
        self.assertTrue(shellsnap.take(proj, snapdir, "perf"))
        time.sleep(0.01)
        with open(os.path.join(proj, "pkg1", "m1.py"), "w") as f:
            f.write("def f1(a, b, c):\n    return a\n")
        with open(os.path.join(proj, "shop", "new.py"), "w") as f:
            f.write("X = 1\n")
        res = shellsnap.diff(proj, snapdir, "perf")
        by = {r[0]: r for r in res}
        self.assertEqual(sorted(by), ["pkg1/m1.py", "shop/new.py"])
        self.assertIn("def f1(a, b):", by["pkg1/m1.py"][1])
        self.assertTrue(by["pkg1/m1.py"][3])
        self.assertFalse(by["shop/new.py"][3])

    def test_big_project_falls_back_safely(self):
        proj = self.project(5000)
        snapdir = tempfile.mkdtemp()
        self.dirs.append(snapdir)
        t = time.perf_counter()
        self.assertFalse(shellsnap.take(proj, snapdir, "big"))
        self.assertLess(time.perf_counter() - t, 0.5)
        self.assertFalse(os.path.exists(shellsnap.snap_path(snapdir, "big")))
        self.assertIsNone(shellsnap.diff(proj, snapdir, "big"))

    def test_skips_vendored_and_large_files(self):
        proj = self.project(0)
        os.makedirs(os.path.join(proj, "node_modules", "x"))
        os.makedirs(os.path.join(proj, ".hidden"))
        for rel in ("node_modules/x/a.js", ".hidden/b.py"):
            with open(os.path.join(proj, rel), "w") as f:
                f.write("1")
        with open(os.path.join(proj, "big.json"), "w") as f:
            f.write("x" * (shellsnap.MAX_FILE_BYTES + 1))
        files = shellsnap.scan(proj, with_content=False)
        self.assertEqual(sorted(files), ["shop/__init__.py", "shop/api.py", "shop/config.py", "shop/db.py"])


if __name__ == "__main__":
    unittest.main()
