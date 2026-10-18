"""MeshAgents (import name: baton): shared task, decision and handoff graph for parallel sessions."""

__version__ = "0.0.1"


def _alias_env() -> None:
    """MESHAGENTS_<NAME> works as BATON_<NAME> (an explicit BATON_ value wins). Runs at import time."""
    import os

    for key in list(os.environ):
        if key.startswith("MESHAGENTS_"):
            os.environ.setdefault("BATON_" + key[len("MESHAGENTS_"):], os.environ[key])


_alias_env()
