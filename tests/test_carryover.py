import uuid
import unittest

from tests.support import GraphCase

from baton.core import rules, sessions
from baton.hooks import events
from baton.hooks.config import Config


class RuleExtractionTests(unittest.TestCase):
    def test_project_level_statements_are_captured(self):
        text = ("Add a refund function to shop.api. FYI the deploy target has a read-only filesystem: never use "
                "sqlite, only write under shop/data/. Every new public function must raise ShopError.")
        got = rules.extract(text)
        self.assertTrue(any("sqlite" in g for g in got), got)
        self.assertTrue(any("ShopError" in g for g in got), got)

    def test_ordinary_task_wording_is_not_a_rule(self):
        boilerplate = ("You are an engineer working in the Python project at /app. Do not touch anything outside it, "
                       "do not install packages, no network. Keep the change small. Add slugify(text) that lowercases "
                       "the text. The function must return a string.")
        self.assertEqual(rules.extract(boilerplate), [])

    def test_questions_and_short_fragments_are_ignored(self):
        self.assertEqual(rules.extract("Should we never use sqlite? ok"), [])

    def test_a_decision_with_an_alternative_counts(self):
        self.assertTrue(rules.extract("Don't call shop.batch, use the single item path instead."))


class CarryOverTests(GraphCase):
    def test_next_session_is_told_the_full_request_and_the_rules(self):
        s = self.store
        a, b = "ya-" + uuid.uuid4().hex[:6], "yb-" + uuid.uuid4().hex[:6]
        cfg = Config()
        events.on_session_start(s, {"session_id": a}, cfg, now=100)
        spec = ("Build the order import feature in six steps. Step 1: parser. Step 2: validator. Step 3: store. "
                "Step 4: dedupe by external id. Step 5: audit log line per import. Step 6: summary report. "
                "Do steps 1 to 3 today, the rest tomorrow. FYI never use sqlite here, the server is read-only.")
        events.on_prompt(s, {"session_id": a, "prompt": spec}, cfg, now=101)
        events.on_stop(s, {"session_id": a, "last_assistant_message": "Done with steps 1-3."}, cfg, now=200)
        events.on_session_end(s, {"session_id": a}, cfg, now=201)
        out = events.on_session_start(s, {"session_id": b}, cfg, now=300)
        text = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Step 4: dedupe", text)          # the part of the request that was not done yet
        self.assertIn("Step 6: summary report", text)
        self.assertIn("never use sqlite", text)        # the rule stated once
        self.assertIn("Rules and facts stated earlier", text)

    def test_a_sessions_own_rules_are_not_echoed_back_to_it(self):
        s = self.store
        a = "yc-" + uuid.uuid4().hex[:6]
        cfg = Config()
        events.on_prompt(s, {"session_id": a, "prompt": "FYI we never use sqlite in this project, remember that."}, cfg, now=100)
        text = sessions.briefing(s, a, now=110)
        self.assertNotIn("never use sqlite", text)


if __name__ == "__main__":
    unittest.main()


class RelevanceTests(GraphCase):
    def setUp(self):
        import os
        self._old = os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def tearDown(self):
        import os
        if self._old is not None:
            os.environ["CLAUDE_PROJECT_DIR"] = self._old

    def test_a_relevant_old_rule_is_found_among_many(self):
        s = self.store
        a, b = "ra-" + uuid.uuid4().hex[:6], "rb-" + uuid.uuid4().hex[:6]
        cfg = Config()
        needle = "We always cap refund amounts at the original order total and round half-even to whole cents."
        block = ["FYI we never log full card numbers in %s_module." % w for w in
                 ("email", "export", "cache", "cli", "report", "audit", "queue", "search")]
        events.on_prompt(s, {"session_id": a, "prompt": " ".join(block[:4] + [needle] + block[4:])}, cfg, now=100)
        # ten newer rules push the needle out of the 8 shown at session start
        for i in range(10):
            events.on_prompt(s, {"session_id": "ro%d-%s" % (i, uuid.uuid4().hex[:4]),
                                 "prompt": "FYI we always use pattern%d_widget naming in this project." % i}, cfg, now=200 + i)
        start = events.on_session_start(s, {"session_id": b}, cfg, now=500)
        self.assertNotIn("refund amounts", start["hookSpecificOutput"]["additionalContext"])
        out = events.on_prompt(s, {"session_id": b, "prompt": "Add shop.api.refund_order(order_id, amount_cents) for refund amounts."},
                               cfg, now=501)
        self.assertIn("refund amounts at the original order total", out["hookSpecificOutput"]["additionalContext"])

    def test_unrelated_request_gets_no_extra_rules(self):
        s = self.store
        a, b = "rc-" + uuid.uuid4().hex[:6], "rd-" + uuid.uuid4().hex[:6]
        cfg = Config()
        events.on_prompt(s, {"session_id": a, "prompt": "FYI we never log full card numbers in the email module."}, cfg, now=100)
        out = events.on_prompt(s, {"session_id": b, "prompt": "Rename the helper that formats prices."}, cfg, now=200)
        self.assertIsNone(out)

    def test_rule_naming_a_file_surfaces_when_that_file_is_edited(self):
        import os, tempfile
        s = self.store
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "shop"))
        with open(os.path.join(d, "shop", "batch.py"), "w") as f:
            f.write("def run():\n    pass\n")
        a, b = "re-" + uuid.uuid4().hex[:6], "rf-" + uuid.uuid4().hex[:6]
        cfg = Config()
        events.on_prompt(s, {"session_id": a, "cwd": d,
                             "prompt": "We tried shop.batch and it deadlocks under load, do not build on it."}, cfg, now=100)
        out = events.on_pre_tool(s, {"session_id": b, "cwd": d, "tool_name": "Edit",
                                     "tool_input": {"file_path": os.path.join(d, "shop", "batch.py")}}, cfg, now=200)
        text = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("rule stated earlier", text)
        self.assertIn("deadlocks", text)
