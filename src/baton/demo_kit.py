"""`meshagents demo`: a clean sample project plus a running dashboard, for a screen-recorded demo.

    meshagents demo          set up (or reset) ~/meshagents-demo, start the dashboard, print what to type
    meshagents demo reset    same, from a clean slate
    meshagents demo status   is the dashboard up, how many helpers it has seen
    meshagents demo stop     stop the dashboard

Environment (for tests): MESHAGENTS_DEMO_DIR (project folder), MESHAGENTS_DEMO_PID (pid file),
MESHAGENTS_DEMO_PORT (first port to try), BATON_WORKSPACE (force the workspace name).
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from typing import Any, Dict, List, Optional

MARKER = ".meshagents-demo"
PROMPTS = (
    "In shop/db.py change get_order so it also needs a tenant name. "
    "Rule for this project: never use sqlite, the server filesystem is read-only.",
    "Add a function fetch_order_for(order_id, tenant) in shop/api.py that uses get_order.",
    "Make orders survive a restart.",
)


def repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def demo_dir() -> str:
    return os.path.abspath(os.path.expanduser(os.environ.get("MESHAGENTS_DEMO_DIR") or "~/meshagents-demo"))


def pid_file() -> str:
    return os.path.abspath(os.path.expanduser(os.environ.get("MESHAGENTS_DEMO_PID") or "~/.meshagents-demo.pid"))


def log_file() -> str:
    return pid_file()[: -len(".pid")] + ".log" if pid_file().endswith(".pid") else pid_file() + ".log"


def plugin_dir() -> str:
    return os.path.join(repo_root(), "plugin")


def fixture_dir() -> str:
    return os.path.join(repo_root(), "evals", "clash", "fixture")


def workspace_for(project: str) -> str:
    """The name hooks compute for this project (BATON_WORKSPACE wins, as it does in the hooks)."""
    from baton.service import default_workspace

    return os.environ.get("BATON_WORKSPACE") or default_workspace(project)


def plugin_installed_globally() -> bool:
    """True when `claude plugin list` mentions the plugin; quiet and best effort."""
    try:
        out = subprocess.run(["claude", "plugin", "list"], capture_output=True, text=True, timeout=8).stdout
    except Exception:
        return False
    return "meshagents" in out.lower() or "baton" in out.lower()


def instructions(project: str, url: str, plugin: str, global_plugin: bool = False) -> str:
    home = os.path.expanduser("~")
    shown = "~" + project[len(home):] if project.startswith(home + os.sep) else project
    cmd = "cd %s && claude" % shown if global_plugin else "cd %s && claude --plugin-dir %s" % (shown, plugin)
    lines = [
        "",
        "MeshAgents demo is ready",
        "  Project    %s" % shown,
        "  Dashboard  %s" % url,
        "",
        "Open three terminals, one after the other. In each, run:",
        "  %s" % cmd,
        "",
        "Then type:",
        "  Terminal 1   %s" % PROMPTS[0],
        "  Terminal 2   %s" % PROMPTS[1],
        "  Terminal 3   %s" % PROMPTS[2],
        "",
        "Start terminal 2 while terminal 1 is still working. Start terminal 3 after both finish.",
        "Start over:  meshagents demo reset      Stop:  meshagents demo stop",
        "",
    ]
    return "\n".join(lines)


def _say(msg: str) -> None:
    print(msg, flush=True)


def _git(project: str, *args: str) -> None:
    subprocess.run(["git", "-C", project, "-c", "user.name=demo", "-c", "user.email=demo@example.com", *args],
                   check=True, capture_output=True, text=True)


def create_project(project: str) -> None:
    """Fresh copy of the sample shop project with one git commit. Refuses to wipe a folder it did not make."""
    if os.path.exists(project):
        if not os.path.exists(os.path.join(project, MARKER)):
            raise RuntimeError("%s exists and is not a demo folder; move it away first" % project)
        shutil.rmtree(project)
    shutil.copytree(fixture_dir(), project, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "README.md"))
    with open(os.path.join(project, MARKER), "w") as f:
        f.write("created by meshagents demo\n")
    with open(os.path.join(project, ".gitignore"), "w") as f:
        f.write("__pycache__/\n*.pyc\n%s\n" % MARKER)
    _git(project, "init", "-q")
    _git(project, "add", "-A")
    _git(project, "commit", "-q", "-m", "sample shop project")


def falkordb_reachable(wait_s: float = 3.0) -> bool:
    from baton.graph.client import connection_settings

    s = connection_settings()
    end = time.time() + wait_s
    while True:
        try:
            with socket.create_connection((s["host"], s["port"]), timeout=1):
                return True
        except OSError:
            if time.time() >= end:
                return False
            time.sleep(0.5)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid() -> Optional[Dict[str, Any]]:
    try:
        with open(pid_file()) as f:
            data = json.loads(f.read())
        return data if isinstance(data, dict) and isinstance(data.get("pid"), int) else None
    except (OSError, ValueError):
        return None


def stop_dashboard() -> bool:
    info = read_pid()
    stopped = False
    if info and _alive(info["pid"]):
        try:
            os.kill(info["pid"], signal.SIGTERM)
            for _ in range(20):
                if not _alive(info["pid"]):
                    break
                time.sleep(0.1)
            stopped = True
        except OSError:
            pass
    try:
        os.remove(pid_file())
    except OSError:
        pass
    return stopped


def _port_free(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def free_port(start: int) -> int:
    for p in range(start, start + 50):
        if _port_free(p):
            return p
    raise RuntimeError("no free port near %d" % start)


def start_dashboard(workspace: str, port: int) -> subprocess.Popen:
    code = "import sys; from baton.ui.server import main; sys.exit(main(sys.argv[1:]))"
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(repo_root(), "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    log = open(log_file(), "ab")
    proc = subprocess.Popen([sys.executable, "-B", "-c", code, "--workspace", workspace, "--port", str(port)],
                            stdin=subprocess.DEVNULL, stdout=log, stderr=log, env=env, start_new_session=True)
    with open(pid_file(), "w") as f:
        f.write(json.dumps({"pid": proc.pid, "port": port, "workspace": workspace}))
    return proc


def fetch_state(port: int, timeout: float = 2.0) -> Optional[dict]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/state" % port, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def wait_dashboard(port: int, wait_s: float = 10.0) -> bool:
    end = time.time() + wait_s
    while time.time() < end:
        if fetch_state(port) is not None:
            return True
        time.sleep(0.3)
    return False


def setup(open_browser: bool = True) -> int:
    from baton.graph.client import Store

    if not falkordb_reachable():
        _say("FalkorDB is not running.\n  Start it:  docker compose up -d   (in %s)\nThen run this again." % repo_root())
        return 1
    project = demo_dir()
    stop_dashboard()
    try:
        create_project(project)
    except (RuntimeError, subprocess.CalledProcessError, OSError) as e:
        _say("Could not set up the demo project: %s" % (getattr(e, "stderr", None) or e))
        return 1
    ws = workspace_for(project)
    store = Store(ws)
    store.drop()
    try:
        store.bootstrap()
    except Exception as e:
        _say("Could not reach FalkorDB (%s: %s).\n  Start it:  docker compose up -d" % (type(e).__name__, e))
        return 1
    port = free_port(int(os.environ.get("MESHAGENTS_DEMO_PORT") or 7777))
    start_dashboard(ws, port)
    if not wait_dashboard(port):
        _say("The dashboard did not start. Look at %s" % log_file())
        return 1
    url = "http://127.0.0.1:%d" % port
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    _say(instructions(project, url, plugin_dir(), plugin_installed_globally()))
    if os.environ.get("BATON_WORKSPACE"):
        _say("(workspace forced to %s)" % ws)
    return 0


def status() -> int:
    info = read_pid()
    if not info or not _alive(info["pid"]):
        _say("Dashboard: not running.  Start it with: meshagents demo")
        return 1
    state = fetch_state(info["port"])
    if state is None:
        _say("Dashboard: process %d is alive but not answering on port %d." % (info["pid"], info["port"]))
        return 1
    helpers = len(state.get("sessions") or [])
    _say("Dashboard: up at http://127.0.0.1:%d  (workspace %s)\nHelpers seen: %d" % (info["port"], info.get("workspace"), helpers))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    sub = argv[0] if argv and not argv[0].startswith("-") else "start"
    if sub in ("start", "reset"):
        return setup(open_browser="--no-browser" not in argv)
    if sub == "status":
        return status()
    if sub == "stop":
        _say("Dashboard stopped." if stop_dashboard() else "Dashboard was not running.")
        return 0
    _say("usage: meshagents demo [reset|status|stop]")
    return 2


if __name__ == "__main__":
    sys.exit(main())
