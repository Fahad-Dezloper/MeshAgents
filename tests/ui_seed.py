"""Seed a believable two-session scenario (plus a stale one) using the public core functions."""

import time

from baton.core import decisions, provenance, sessions

HOSTILE = "<img src=x onerror=alert(1)>"


def seed(store, now=None, hostile=False):
    t = time.time() if now is None else now
    A, B, C = "sess-A-storage", "sess-B-endpoint", "sess-C-old"
    sessions.begin_session(store, A, now=t - 600)
    sessions.set_goal(store, A, "Ticket 12: make get_order take an include_cancelled flag and keep orders in sqlite", now=t - 600)
    sessions.begin_session(store, B, now=t - 500)
    sessions.set_goal(store, B, "Ticket 15: add an order lookup endpoint that uses db.get_order", now=t - 500)
    sessions.begin_session(store, C, now=t - 5000)
    sessions.set_goal(store, C, "Refactor logging", now=t - 5000)
    sessions.touch(store, C, "shop/log.py", now=t - 4900)
    sessions.export_session_handoff(store, C, note="logging half done", now=t - 4700)
    sessions.end_session(store, C, now=t - 4600)
    sessions.touch(store, A, "shop/db.py", now=t - 120)
    sessions.touch(store, A, "shop/models.py", now=t - 100)
    sessions.touch(store, B, "shop/api.py", now=t - 60)
    sessions.touch(store, B, "shop/db.py", now=t - 30)
    f = provenance.add_finding(store, A, "Orders must survive restarts (requirements v1)", source="requirements v1", now=t - 400)
    d1 = decisions.post_decision(store, A, HOSTILE if hostile else "use sqlite for order storage", artifacts=["shop/db.py"],
                                 based_on=[f["id"]], kind="storage", now=t - 300)
    d2 = decisions.post_decision(store, B, "endpoint reads through db.get_order, no cache", artifacts=["shop/api.py"],
                                 based_on=[d1["id"]], kind="interface", now=t - 200)
    d3 = decisions.post_decision(store, A, "get_order gains include_cancelled=False", artifacts=["shop/db.py"],
                                 kind="interface", now=t - 150)
    return {"A": A, "B": B, "C": C, "finding": f["id"], "d1": d1["id"], "d2": d2["id"], "d3": d3["id"]}
