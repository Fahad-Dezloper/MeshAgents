import os
import tempfile
import uuid
import unittest

from tests.support import GraphCase

from baton.core import notices, sessions
from baton.hooks import events
from baton.hooks.config import Config


def told(store, actor):
    rows = store.rows("MATCH (a:Actor {id: $a})-[:WAS_TOLD]->(n:Notice) RETURN n.kind, n.summary, n.detail, n.files "
                      "ORDER BY n.at", {"a": actor}, read_only=True)
    return [(r[0], r[1], r[2], r[3]) for r in rows]


class NoticeTests(GraphCase):
    def setUp(self):
        self._old = os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def tearDown(self):
        if self._old is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = self._old

    def test_record_is_plain_and_bounded(self):
        a = "na-" + uuid.uuid4().hex[:6]
        nid = notices.record(self.store, a, "collision", "Another helper is working in db.py", "x" * 5000, ["shop/db.py"])
        self.assertTrue(nid.startswith("ntc_"))
        k, s, d, f = told(self.store, a)[0]
        self.assertEqual((k, s, f), ("collision", "Another helper is working in db.py", ["shop/db.py"]))
        self.assertLessEqual(len(d), 600)

    def test_names_helper(self):
        self.assertEqual(notices.names(["shop/db.py", "shop/api.py", "a/db.py"]), "db.py, api.py")
        self.assertEqual(notices.names(["a.py", "b.py", "c.py", "d.py", "e.py"]), "a.py, b.py, c.py and 2 more")

    def test_collision_and_briefing_are_recorded_for_the_helper_that_was_told(self):
        a, b = "nb-" + uuid.uuid4().hex[:6], "nc-" + uuid.uuid4().hex[:6]
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "shop"))
        for n in ("db.py", "api.py"):
            with open(os.path.join(d, "shop", n), "w") as f:
                f.write("def get_order(order_id):\n    return order_id\n")
        cfg = Config()
        events.on_session_start(self.store, {"session_id": a, "cwd": d}, cfg, now=100)
        events.on_prompt(self.store, {"session_id": a, "cwd": d, "prompt": "FYI never use sqlite, the server is read-only."}, cfg, now=101)
        events.on_post_tool(self.store, {"session_id": a, "cwd": d, "tool_name": "Edit",
                                         "tool_input": {"file_path": os.path.join(d, "shop/db.py")},
                                         "tool_response": {"originalFile": "def get_order(order_id):\n    return order_id\n"}}, cfg, now=110)
        out = events.on_session_start(self.store, {"session_id": b, "cwd": d}, cfg, now=120)
        self.assertIsNotNone(out)
        kinds = [x[0] for x in told(self.store, b)]
        self.assertIn("briefing", kinds)
        self.assertTrue(any("1 rule" in x[1] for x in told(self.store, b) if x[0] == "briefing"))
        events.on_pre_tool(self.store, {"session_id": b, "cwd": d, "tool_name": "Edit",
                                        "tool_input": {"file_path": os.path.join(d, "shop/db.py")}}, cfg, now=130)
        summaries = [x[1] for x in told(self.store, b)]
        self.assertTrue(any("Another helper" in s and "db.py" in s for s in summaries), summaries)

    def test_goal_time_is_stored(self):
        a = "nd-" + uuid.uuid4().hex[:6]
        sessions.begin_session(self.store, a, now=100)
        sessions.set_goal(self.store, a, "Add a function that does a thing for the demo", now=150)
        rows = self.store.rows("MATCH (t:Task {id: $id}) RETURN t.goal_at", {"id": sessions.session_task_id(a)}, read_only=True)
        self.assertEqual(rows[0][0], 150)


if __name__ == "__main__":
    unittest.main()
