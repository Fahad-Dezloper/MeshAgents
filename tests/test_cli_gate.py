"""The hook command's early exit must let shell writes through (the logic tests call handlers directly)."""

import io
import json
import os
import tempfile
import uuid
import unittest

from tests.support import GraphCase

from baton.hooks import cli
from baton.core import sessions


class CliGateTests(GraphCase):
    def setUp(self):
        self.ws = "gate_" + uuid.uuid4().hex[:8]
        self.old = {k: os.environ.get(k) for k in ("BATON_WORKSPACE", "CLAUDE_PROJECT_DIR")}
        os.environ["BATON_WORKSPACE"] = self.ws
        self.d = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.d, "shop"))
        with open(os.path.join(self.d, "shop", "config.py"), "w") as f:
            f.write("CONFIG = {'a': 1}\n")
        os.environ["CLAUDE_PROJECT_DIR"] = self.d

    def tearDown(self):
        from baton.graph.client import Store
        Store(self.ws).drop()
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _fire(self, event, cmd, sid="gs-1"):
        payload = {"session_id": sid, "cwd": self.d, "tool_name": "Bash", "tool_input": {"command": cmd},
                   "tool_response": {}}
        return cli.main([event], stdin=io.StringIO(json.dumps(payload)))

    def test_a_shell_write_is_recorded_through_the_real_entry_point(self):
        from baton.graph.client import Store
        cmd = "sed -i 's/a/b/' shop/config.py"
        self.assertEqual(self._fire("pre-tool", cmd), 0)
        with open(os.path.join(self.d, "shop", "config.py"), "w") as f:  # what the command does
            f.write("CONFIG = {'a': 2}\n")
        self.assertEqual(self._fire("post-tool", cmd), 0)
        rows = Store(self.ws).rows("MATCH (t:Task)-[:TOUCHES]->(a:Artifact) RETURN a.path", read_only=True)
        self.assertIn("shop/config.py", [r[0] for r in rows])

    def test_read_only_shell_commands_skip_the_database(self):
        from baton.graph.client import Store
        self.assertEqual(self._fire("pre-tool", "cat shop/config.py"), 0)
        self.assertEqual(self._fire("post-tool", "cat shop/config.py"), 0)
        # the graph was never even created: nothing was written for a read-only command
        from falkordb import FalkorDB
        self.assertNotIn("baton_" + self.ws, FalkorDB().list_graphs())


if __name__ == "__main__":
    unittest.main()
