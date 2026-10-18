# Quickstart

Needs: Docker, Python 3.10+, Claude Code. Takes about 2 minutes.

```sh
git clone <repo-url> meshagents && cd meshagents
docker compose up -d && python3 -m venv .venv && .venv/bin/pip install -e .   # FalkorDB + MeshAgents
.venv/bin/meshagents doctor && .venv/bin/python demo/run_demo.py                    # check, then scripted demo
```

Then open http://localhost:3000, pick graph `baton_demo`, and run the queries in
`demo/queries.cypher`.

To use it with Claude Code (any project, no other setup):

```sh
claude --plugin-dir /path/to/meshagents/plugin
```

The plugin launchers find the repo's `.venv` on their own. If that fails, hooks stay silent (they
never block a session); run `meshagents doctor` to see why.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `doctor`: FalkorDB not reachable | container not running, or port 6379 taken by another Redis | `docker compose up -d`; if 6379 is busy, stop the other server or edit the left side of the port in `docker-compose.yml` and set `MESHAGENTS_FALKORDB_PORT` |
| `doctor`: package not importable | pip install not run, or wrong venv | `python3 -m venv .venv && .venv/bin/pip install -e .` and run `.venv/bin/meshagents doctor` |
| `pip install` says requires Python >=3.10 | old `python3` | use `python3.11` (or newer) to create the venv |
| `meshagents: command not found` | venv not activated | use `.venv/bin/meshagents` or `source .venv/bin/activate` |
| Plugin loaded but nothing happens, no graph appears | hooks failed open (store down, or no Python with MeshAgents) | `meshagents doctor`; set `MESHAGENTS_DEBUG_LOG=/tmp/meshagents.log` and look for `error` lines |
| Demo prints nothing about Browser graphs | Browser shows only existing graphs | run the demo first, then reload http://localhost:3000 |
| Demo clobbers my graph `baton_demo` | the demo drops and recreates its workspace | `MESHAGENTS_DEMO_WORKSPACE=mydemo .venv/bin/python demo/run_demo.py` |
| Hooks use the wrong Python | several interpreters on the machine | `export MESHAGENTS_PYTHON=/path/to/python` (needs MeshAgents + falkordb installed) |

Launcher order for finding Python: `$MESHAGENTS_PYTHON`, `<repo>/.venv`, the interpreter of the `meshagents`
command on PATH, then `python3`/`python` if they can import baton and falkordb.

## Add MeshAgents to an existing project

Nothing is installed into the project. Start Claude Code in it with the plugin directory:

```sh
cd ~/my-project
claude --plugin-dir /path/to/meshagents/plugin
```

Each project directory gets its own graph (`baton_<dirname>-<hash>`). Optional per-project settings
go in `.baton.json` (`policy`: `warn` | `ask` | `deny`, `lease_seconds`, `capture`, `enabled`). To
see what fired: `MESHAGENTS_DEBUG_LOG=/tmp/meshagents.log claude --plugin-dir ...` and read the file; one line per
hook event.

## Turn it off

- One session: start Claude Code without `--plugin-dir`.
- One project: put `{"enabled": false}` in `.baton.json`.
- Everywhere, for a shell: `export MESHAGENTS_DISABLED=1`.
- Remove data: delete the graph in the Browser, or `docker compose down -v`.

## Remote FalkorDB

```sh
export MESHAGENTS_FALKORDB_HOST=db.example.com
export MESHAGENTS_FALKORDB_PORT=6379
.venv/bin/meshagents doctor
```

Every `MESHAGENTS_*` variable is also read under its old name (`MESHAGENTS_X` works as `BATON_X`; an explicit `BATON_X` wins), and the old `baton` command still works.
Set these in the environment Claude Code is started from; hooks and the MCP server inherit them.
Connections use the Redis protocol with short timeouts (1 s connect for hooks). For a remote FalkorDB set
`MESHAGENTS_FALKORDB_HOST`, `MESHAGENTS_FALKORDB_PORT`, `MESHAGENTS_FALKORDB_PASSWORD` (and `MESHAGENTS_FALKORDB_USERNAME`), and
`MESHAGENTS_FALKORDB_SSL=1` for TLS. These are not covered by automated tests against a real TLS server yet, so
prefer a private network or a tunnel (`ssh -L 6379:localhost:6379 host`) for anything important.
