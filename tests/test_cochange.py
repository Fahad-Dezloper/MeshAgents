import os
import subprocess
import tempfile
import unittest
import uuid

from tests.support import DB_UP

from baton.core import cochange as cc
from baton.graph.client import Store
from baton.hooks import events
from baton.hooks.config import Config, load_config


def git(d, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@example.com", GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    subprocess.run(["git", "-C", d] + list(args), check=True, capture_output=True, env=env)


def commit(d, files, msg="c"):
    for rel, text in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a") as f:
            f.write(text + "\n")
    git(d, "add", "-A")
    git(d, "commit", "-q", "-m", msg)


def make_repo(d, rounds=11):
    """shop/db.py changes with tests/test_db.py every time, with shop/api.py in most rounds."""
    git(d, "init", "-q")
    for i in range(rounds):
        files = {"shop/db.py": "x%d" % i, "tests/test_db.py": "t%d" % i}
        if i % 3 != 2:
            files["shop/api.py"] = "a%d" % i
        commit(d, files)
    commit(d, {"README.md": "r"})
    commit(d, {"package-lock.json": "{}", "shop/db.py": "lock"})


class PureTests(unittest.TestCase):
    def test_skip_path(self):
        for p in ("package-lock.json", "web/yarn.lock", "node_modules/x/index.js", "vendor/lib.py", "app.min.js",
                  "api_pb2.py", "CHANGES.rst", "docs/logo.png", "Cargo.lock", "dist/a.js"):
            self.assertTrue(cc.skip_path(p), p)
        for p in ("shop/db.py", "tests/test_db.py", "docs/changes/guide.md", "src/build_index.py"):
            self.assertFalse(cc.skip_path(p), p)

    def test_parse_and_renames(self):
        log = ("\x01c3\nM\tnew/name.py\nM\ttests/t.py\n\n"
               "\x01c2\nR090\told/name.py\tnew/name.py\n\n"
               "\x01c1\nM\told/name.py\nD\tgone.py\nM\tpackage-lock.json\n")
        commits = cc.resolve_renames(cc.parse_log(log))
        self.assertEqual([c[0] for c in commits], ["c1", "c2", "c3"])  # oldest first
        self.assertEqual(commits[0][1], ["new/name.py"])  # rename followed, delete and lockfile dropped
        self.assertEqual(commits[2][1], ["new/name.py", "tests/t.py"])
        raw = cc.resolve_renames(cc.parse_log(log), follow=False)
        self.assertEqual(raw[0][1], ["old/name.py"])

    def test_aggregate_and_big_commits(self):
        commits = [("1", ["a", "b"]), ("2", ["a", "b", "c"]), ("3", ["a"]), ("4", ["f%d" % i for i in range(30)])]
        files, pairs = cc.aggregate(commits)
        self.assertEqual(files["a"], 3)
        self.assertEqual(pairs[("a", "b")], 2)
        self.assertNotIn("f0", files)  # the 30-file commit is a sweep
        edges = cc.directed_edges(files, pairs)
        self.assertEqual(edges["a"][0][:2], ("b", 2))
        self.assertAlmostEqual(edges["a"][0][2], 2 / 3)
        self.assertAlmostEqual(dict((p, r) for p, _n, r in edges["b"])["a"], 1.0)

    def test_rank_partners_thresholds_and_exclusion(self):
        cands = [("t.py", 9, 0.8), ("b.py", 3, 0.5), ("c.py", 2, 0.9), ("d.py", 5, 0.3), ("e.py", 4, 0.6)]
        got = cc.rank_partners(cands)
        self.assertEqual([c[0] for c in got], ["t.py", "e.py", "b.py"])
        self.assertEqual([c[0] for c in cc.rank_partners(cands, exclude=["t.py"])], ["e.py", "b.py"])
        self.assertEqual(len(cc.rank_partners(cands, 1, 0.0, limit=2)), 2)

    def test_format_hint(self):
        self.assertEqual(cc.format_hint("shop/db.py", [("tests/test_db.py", 9, .8), ("shop/api.py", 7, .6)], 11),
                         "Files that usually change with shop/db.py: tests/test_db.py (9 of 11 commits), "
                         "shop/api.py (7 of 11 commits).")

    def test_config_flag(self):
        self.assertTrue(Config().cochange)
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, ".baton.json"), "w") as f:
                f.write('{"cochange": false}')
            self.assertFalse(load_config(d).cochange)
        os.environ["BATON_COCHANGE"] = "0"
        try:
            self.assertFalse(load_config(None).cochange)
        finally:
            del os.environ["BATON_COCHANGE"]

    def test_history_of_real_git_repo(self):
        with tempfile.TemporaryDirectory() as d:
            make_repo(d)
            hist = cc.read_history(d)
            self.assertEqual(len(hist), 13)
            files, pairs = cc.aggregate(hist)
            self.assertEqual(files["shop/db.py"], 12)  # 11 + the lockfile commit (lockfile itself skipped)
            self.assertEqual(pairs[("shop/db.py", "tests/test_db.py")], 11)
            self.assertNotIn("package-lock.json", files)
            self.assertIsNone(cc.read_history(d, since="0" * 40))  # unknown sha
            self.assertIsNone(cc.read_history(os.path.join(d, "nope")))

    def test_rename_in_real_repo(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q")
            body = "\n".join("line %d" % i for i in range(40))
            commit(d, {"old.py": body, "t.py": "t"})
            git(d, "mv", "old.py", "new.py")
            git(d, "commit", "-q", "-m", "mv")
            commit(d, {"new.py": "more", "t.py": "more"})
            files, pairs = cc.aggregate(cc.read_history(d))
            self.assertEqual(files["new.py"], 3)
            self.assertNotIn("old.py", files)


@unittest.skipUnless(DB_UP, "FalkorDB not reachable on localhost:6379")
class GraphTests(unittest.TestCase):
    def setUp(self):
        self.store = Store("cc_" + uuid.uuid4().hex[:8])
        self.store.bootstrap()
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        make_repo(self.d)

    def tearDown(self):
        self.store.drop()
        self.tmp.cleanup()

    def test_index_query_incremental(self):
        r = cc.index_project(self.store, self.d, budget_s=5)
        self.assertEqual((r["commits"], r["status"]), (13, "ok"))
        info = cc.partners(self.store, "shop/db.py", 3, 0.5)
        got = {p: (n, round(ratio, 2)) for p, n, ratio in info["partners"]}
        self.assertEqual(info["total"], 12)
        self.assertEqual(got["tests/test_db.py"], (11, round(11 / 12, 2)))
        self.assertEqual(got["shop/api.py"][0], 8)
        self.assertEqual(cc.index_project(self.store, self.d)["status"], "up-to-date")
        commit(self.d, {"shop/db.py": "n", "tests/test_db.py": "n"})
        self.assertEqual(cc.index_project(self.store, self.d)["commits"], 1)
        info = cc.partners(self.store, "shop/db.py", 3, 0.5)
        self.assertEqual(info["total"], 13)
        self.assertEqual(dict((p, n) for p, n, _ in info["partners"])["tests/test_db.py"], 12)
        # the partner direction has its own ratio
        back = cc.partners(self.store, "tests/test_db.py", 3, 0.5)
        self.assertEqual(dict((p, n) for p, n, _ in back["partners"])["shop/db.py"], 12)

    def test_time_box_resumes(self):
        r = cc.index_project(self.store, self.d, budget_s=0)
        self.assertEqual(r["status"], "ok" if r["commits"] == 13 else "partial")
        old = cc.CHUNK_COMMITS
        cc.CHUNK_COMMITS = 5
        try:
            self.store.drop()
            self.store.bootstrap()
            r = cc.index_project(self.store, self.d, budget_s=0)
            self.assertEqual((r["commits"], r["remaining"], r["status"]), (5, 8, "partial"))
            r = cc.index_project(self.store, self.d, budget_s=0)
            self.assertEqual(r["commits"], 5)
            r = cc.index_project(self.store, self.d, budget_s=10)
            self.assertEqual(r["status"], "ok")
        finally:
            cc.CHUNK_COMMITS = old
        self.assertEqual(cc.partners(self.store, "shop/db.py", 3, 0.5)["total"], 12)  # nothing counted twice

    def test_rewritten_history_rebuilds(self):
        cc.index_project(self.store, self.d, budget_s=5)
        git(self.d, "reset", "-q", "--hard", "HEAD~6")
        commit(self.d, {"x.py": "1", "y.py": "1"})
        r = cc.index_project(self.store, self.d, budget_s=5)
        self.assertGreater(r["commits"], 0)
        self.assertEqual(cc.partners(self.store, "shop/db.py", 1, 0.0)["total"], 7)

    def test_not_a_repo_and_lock(self):
        with tempfile.TemporaryDirectory() as plain:
            self.assertEqual(cc.index_project(self.store, plain)["status"], "no-git")
        self.store.rows(cc.STATE_LOCK, {"now": 1000.0, "until": 2000.0})
        self.assertEqual(cc.index_project(self.store, self.d, now=1500.0)["status"], "busy")

    def test_hook_hint_once_and_policy(self):
        cc.index_project(self.store, self.d, budget_s=5)
        os.environ["CLAUDE_PROJECT_DIR"] = self.d
        try:
            sid = "cc-" + uuid.uuid4().hex[:8]
            payload = {"session_id": sid, "cwd": self.d, "tool_name": "Edit",
                       "tool_input": {"file_path": os.path.join(self.d, "shop/db.py")}}
            cfg = Config()
            out = events.on_pre_tool(self.store, payload, cfg)
            text = out["hookSpecificOutput"]["additionalContext"]
            self.assertIn("Files that usually change with shop/db.py: tests/test_db.py (11 of 12 commits)", text)
            self.assertIn("shop/api.py (8 of 12", text)
            self.assertEqual(text.count("\n"), 0)  # one line
            self.assertIsNone(events.on_pre_tool(self.store, payload, cfg))  # never repeated
            # a partner the session already touched is not suggested
            sid2 = "cc-" + uuid.uuid4().hex[:8]
            events.on_post_tool(self.store, {"session_id": sid2, "cwd": self.d, "tool_name": "Edit",
                                             "tool_input": {"file_path": os.path.join(self.d, "tests/test_db.py")}}, cfg)
            p2 = dict(payload, session_id=sid2)
            text2 = events.on_pre_tool(self.store, p2, cfg)["hookSpecificOutput"]["additionalContext"]
            self.assertNotIn("tests/test_db.py (", text2)
            self.assertIn("shop/api.py", text2)
            # disabled by flag
            off = Config()
            off.cochange = False
            p3 = dict(payload, session_id="cc-" + uuid.uuid4().hex[:8])
            self.assertIsNone(events.on_pre_tool(self.store, p3, off))
            # unknown / unrelated file: silence
            p4 = dict(payload, session_id="cc-" + uuid.uuid4().hex[:8],
                      tool_input={"file_path": os.path.join(self.d, "README.md")})
            self.assertIsNone(events.on_pre_tool(self.store, p4, cfg))
        finally:
            del os.environ["CLAUDE_PROJECT_DIR"]

    def test_hint_skips_deleted_partner(self):
        cc.index_project(self.store, self.d, budget_s=5)
        os.remove(os.path.join(self.d, "tests/test_db.py"))
        line = cc.hint_for(self.store, self.d, "shop/db.py")
        self.assertNotIn("test_db", line)
        self.assertIn("shop/api.py", line)

    def test_hot_flag_from_pagerank(self):
        s = self.store
        s.query("UNWIND range(0,19) AS i CREATE (:Artifact {path:'m'+toString(i)})-[:DEFINES]->(:Symbol {id:'s'+toString(i), path:'m'+toString(i)})")
        s.query("MATCH (s:Symbol {id:'s0'}) UNWIND range(1,19) AS i MATCH (c:Symbol {id:'s'+toString(i)}) CREATE (c)-[:CALLS]->(s)")
        self.assertTrue(cc.refresh_hot(s))
        self.assertFalse(cc.refresh_hot(s))  # cached
        self.assertEqual(cc.partners(s, "m0")["hot"], True)
        self.assertEqual(cc.partners(s, "m5")["hot"], False)
        self.assertEqual(cc.partners(s, "m0")["dep_files"], 19)
        self.assertIn("19 other files depend on m0", cc.hint_for(s, self.d, "m0"))


if __name__ == "__main__":
    unittest.main()
