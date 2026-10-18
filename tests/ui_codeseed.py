import os
import shutil
import tempfile
import time

from baton.core import codegraph, decisions, sessions

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "evals", "clash", "fixture")


def seed_code(store):
    """Index the fixture project; session A changed db.get_order, session B is live in shop/api.py."""
    root = tempfile.mkdtemp(prefix="ui_code_")
    proj = os.path.join(root, "p")
    shutil.copytree(FIXTURE, proj)
    codegraph.index_project(store, proj)
    t = time.time()
    sessions.touch(store, "sess-A", "shop/db.py", now=t - 20)
    sessions.touch(store, "sess-B", "shop/api.py", now=t - 10)
    d = decisions.post_decision(
        store, "sess-A", "interface change in shop/db.py; signature changed: get_order(order_id) -> get_order(order_id, tenant)",
        artifacts=["shop/db.py"], kind="interface", now=t - 15)
    shutil.rmtree(root, ignore_errors=True)
    return d["id"]
