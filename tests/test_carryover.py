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
