"""`meshagents ui`: a read-only local dashboard. Standard library only, GET only, no write endpoints."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional
from urllib.parse import parse_qs, urlsplit

from baton.graph.client import Store
from baton.ui import state

MAX_BODY = 1_500_000  # bytes; responses are capped
CACHE_SECONDS = 0.7
PAGE = os.path.join(os.path.dirname(__file__), "static", "index.html")
CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
       "connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'")


class App:
    """Shared store + short cache so many open tabs do not multiply database load."""

    def __init__(self, workspace: str, store: Optional[Store] = None):
        self.workspace = workspace
        self._injected = store
        self.lock = threading.Lock()
        self._cache = (0.0, b"")

    def _store(self) -> Store:
        # Fresh handle per call: the driver caches schema ids, which go stale if the graph is
        # dropped and recreated while the dashboard keeps running.
        return self._injected or Store(self.workspace)

    def state_json(self) -> bytes:
        with self.lock:
            t, body = self._cache
            if body and time.time() - t < CACHE_SECONDS:
                return body
            body = json.dumps(state.build_state(self._store())).encode()
            if len(body) > MAX_BODY:
                body = json.dumps(state.empty_state(self.workspace, time.time(), "state too large")).encode()
            self._cache = (time.time(), body)
            return body

    def code_json(self) -> bytes:
        with self.lock:
            body = json.dumps(state.code_state(self._store())).encode()
        return body if len(body) <= MAX_BODY else json.dumps({"error": "too large"}).encode()

    def memory_json(self) -> bytes:
        with self.lock:
            return json.dumps(state.memory_state(self._store())).encode()

    def together_json(self, path: str) -> bytes:
        with self.lock:
            try:
                return json.dumps(state.together_view(self._store(), path)).encode()
            except Exception as e:
                return json.dumps({"path": path, "error": type(e).__name__, "total": 0, "hot": False,
                                   "dep_files": 0, "partners": []}).encode()

    def why_json(self, item_id: str) -> Optional[bytes]:
        with self.lock:
            try:
                view = state.provenance_view(self._store(), item_id)
            except Exception as e:
                return json.dumps({"error": "%s" % type(e).__name__}).encode()
        return None if view is None else json.dumps(view).encode()


def make_handler(app: App, allowed_hosts: set):
    class Handler(BaseHTTPRequestHandler):
        server_version = "meshagents-ui"
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):  # quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            return host in allowed_hosts  # blocks DNS-rebinding style requests

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, b'{"error":"forbidden host"}')
            u = urlsplit(self.path)
            if u.path in ("/", "/index.html"):
                with open(PAGE, "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/state":
                return self._send(200, app.state_json())
            if u.path == "/api/code":
                return self._send(200, app.code_json())
            if u.path == "/api/memory":
                return self._send(200, app.memory_json())
            if u.path == "/api/together":
                p = (parse_qs(u.query).get("path") or [""])[0]
                if not state.valid_path(p):
                    return self._send(400, b'{"error":"bad path"}')
                return self._send(200, app.together_json(p))
            if u.path == "/api/why":
                ident = (parse_qs(u.query).get("id") or [""])[0]
                if not ident or len(ident) > 80:
                    return self._send(400, b'{"error":"id required"}')
                body = app.why_json(ident)
                return self._send(404, b'{"error":"not found"}') if body is None else self._send(200, body)
            return self._send(404, b'{"error":"not found"}')

        def _no(self):
            self._send(405, b'{"error":"read-only"}')

        do_POST = do_PUT = do_DELETE = do_PATCH = do_HEAD = do_OPTIONS = _no

    return Handler


def make_server(app: App, host: str = "127.0.0.1", port: int = 7777) -> ThreadingHTTPServer:
    allowed = {"127.0.0.1", "localhost", "::1", host.lower()}
    srv = ThreadingHTTPServer((host, port), make_handler(app, allowed))
    srv.daemon_threads = True
    return srv


def main(argv: Optional[List[str]] = None) -> int:
    from baton.service import default_workspace

    p = argparse.ArgumentParser(prog="meshagents ui", description="Read-only dashboard for a MeshAgents workspace.")
    p.add_argument("--port", type=int, default=7777)
    p.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1; keep it local)")
    p.add_argument("--workspace", default=None)
    a = p.parse_args(argv)
    ws = a.workspace or os.environ.get("BATON_WORKSPACE") or default_workspace()
    try:
        srv = make_server(App(ws), a.host, a.port)
    except OSError as e:
        print("meshagents ui: cannot listen on %s:%d (%s)" % (a.host, a.port, e.strerror or e), file=sys.stderr)
        return 1
    print("meshagents ui: workspace %s\n  http://%s:%d   (read-only, Ctrl-C to stop)" % (ws, a.host, a.port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
