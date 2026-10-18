"""Python symbol extraction and call resolution with the standard `ast` module (no dependencies).

Pure functions: no database, no filesystem except `scan_project`. The graph writer is
`baton.core.codegraph`.

A symbol id is "<relative path>::<qualified name>", for example "shop/db.py::get_order" or
"shop/models.py::Order.total". Calls are resolved statically and conservatively: a call is linked only
when its target can be named from imports and top-level definitions. Method calls on objects of unknown
type are not linked (that would guess).
"""

from __future__ import annotations

import ast
import hashlib
import os
from typing import Dict, List, Optional, Set, Tuple

MAX_FILE_BYTES = 200 * 1024
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "site-packages", "build",
             "dist", ".tox", ".mypy_cache", ".pytest_cache", ".idea", ".vscode"}


def module_name(rel: str) -> str:
    rel = rel.replace("\\", "/")
    if rel.endswith("/__init__.py"):
        rel = rel[: -len("/__init__.py")]
    elif rel.endswith(".py"):
        rel = rel[:-3]
    return rel.replace("/", ".")


def _package_of(rel: str) -> str:
    mod = module_name(rel)
    return mod if rel.endswith("__init__.py") else mod.rpartition(".")[0]


def content_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:16]


def _params(args: ast.arguments) -> List[Tuple[str, str, bool]]:
    """[(name, kind, has_default)] with kind in pos|kwonly|vararg|varkw."""
    out: List[Tuple[str, str, bool]] = []
    pos = list(args.posonlyargs) + list(args.args)
    defaults = [False] * (len(pos) - len(args.defaults)) + [True] * len(args.defaults)
    for a, d in zip(pos, defaults):
        out.append((a.arg, "pos", d))
    if args.vararg:
        out.append((args.vararg.arg, "vararg", True))
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        out.append((a.arg, "kwonly", d is not None))
    if args.kwarg:
        out.append((args.kwarg.arg, "varkw", True))
    return out


def _sig(name: str, params: List[Tuple[str, str, bool]]) -> str:
    parts = []
    for n, kind, dflt in params:
        if n in ("self", "cls"):
            continue
        s = {"vararg": "*" + n, "varkw": "**" + n}.get(kind, n)
        parts.append(s + ("=..." if dflt and kind in ("pos", "kwonly") else ""))
    return "%s(%s)" % (name, ", ".join(parts))


class _Defs(ast.NodeVisitor):
    """Top-level functions, classes and methods (nested functions belong to their parent)."""

    def __init__(self) -> None:
        self.items: List[Dict] = []

    def run(self, tree: ast.AST) -> List[Dict]:
        for node in getattr(tree, "body", []):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._fn(node, node.name, "function")
            elif isinstance(node, ast.ClassDef):
                self.items.append({"qual": node.name, "name": node.name, "kind": "class", "line": node.lineno,
                                   "params": [], "node": node})
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self._fn(sub, "%s.%s" % (node.name, sub.name), "method")
        return self.items

    def _fn(self, node, qual: str, kind: str) -> None:
        self.items.append({"qual": qual, "name": node.name, "kind": kind, "line": node.lineno,
                           "params": _params(node.args), "node": node})


def _imports(tree: ast.AST, rel: str, modules: Dict[str, str]) -> Dict[str, Tuple[str, str]]:
    """alias -> ("module", module_name) | ("symbol", "<path>::<name>")."""
    out: Dict[str, Tuple[str, str]] = {}
    pkg = _package_of(rel)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    out[a.asname] = ("module", a.name)
                else:
                    out[a.name.split(".")[0]] = ("module", a.name.split(".")[0])
                    out[a.name] = ("module", a.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                parts = pkg.split(".") if pkg else []
                parts = parts[: max(0, len(parts) - (node.level - 1))]
                base = ".".join(parts + ([base] if base else []))
            for a in node.names:
                alias = a.asname or a.name
                if base + "." + a.name in modules:
                    out[alias] = ("module", base + "." + a.name)
                elif base in modules:
                    out[alias] = ("symbol", "%s::%s" % (modules[base], a.name))
    return out


def _chain(node: ast.AST) -> Optional[List[str]]:
    parts: List[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return list(reversed(parts))
    return None


def _resolve(chain: List[str], rel: str, imports: Dict[str, Tuple[str, str]], modules: Dict[str, str],
             local: Set[str], cls: Optional[str]) -> Optional[str]:
    head = chain[0]
    if cls and head in ("self", "cls") and len(chain) == 2 and "%s.%s" % (cls, chain[1]) in local:
        return "%s::%s.%s" % (rel, cls, chain[1])
    if len(chain) == 1:
        if head in imports and imports[head][0] == "symbol":
            return imports[head][1]
        if head in local:
            return "%s::%s" % (rel, head)
        return None
    if head in imports:
        kind, target = imports[head]
        if kind == "module":
            # longest module prefix: a.b.c.f with module a.b.c
            mod = target
            i = 1
            while i < len(chain) - 1 and mod + "." + chain[i] in modules:
                mod = mod + "." + chain[i]
                i += 1
            if mod in modules:
                rest = chain[i:]
                return "%s::%s" % (modules[mod], ".".join(rest)) if rest else None
        elif kind == "symbol":
            return "%s.%s" % (target, ".".join(chain[1:]))  # Class.method on an imported class
    if head in local and len(chain) == 2:
        return "%s::%s" % (rel, ".".join(chain))
    return None


def parse_file(text: str, rel: str, modules: Dict[str, str]) -> Optional[Dict]:
    """{"path","hash","defs":[{id,qual,name,kind,line,sig,params}], "edges":[(from_id,to_id)]} or None."""
    if not text or len(text) > MAX_FILE_BYTES:
        return None
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return None
    defs = _Defs().run(tree)
    local = {d["qual"] for d in defs}
    imports = _imports(tree, rel, modules)
    out_defs = [{"id": "%s::%s" % (rel, d["qual"]), "qual": d["qual"], "name": d["name"], "kind": d["kind"],
                 "line": d["line"], "sig": _sig(d["name"], d["params"]) if d["kind"] != "class" else d["name"],
                 "params": d["params"]} for d in defs]
    module_id = "%s::<module>" % rel
    out_defs.append({"id": module_id, "qual": "<module>", "name": "<module>", "kind": "module", "line": 1,
                     "sig": "<module>", "params": []})
    edges: Set[Tuple[str, str]] = set()

    def collect(owner_id: str, body_nodes, cls: Optional[str]) -> None:
        for top in body_nodes:
            for node in ast.walk(top):
                if isinstance(node, ast.Call):
                    chain = _chain(node.func)
                    if chain:
                        target = _resolve(chain, rel, imports, modules, local, cls)
                        if target and target != owner_id:
                            edges.add((owner_id, target))

    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            collect("%s::%s" % (rel, node.name), [node], None)
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    collect("%s::%s.%s" % (rel, node.name, sub.name), [sub], node.name)
                else:
                    collect(module_id, [sub], node.name)
        else:
            collect(module_id, [node], None)
    return {"path": rel, "hash": content_hash(text), "defs": out_defs, "edges": sorted(edges)}


def breaking_changes(old_text: str, new_text: str) -> List[Dict[str, str]]:
    """Public functions/methods whose call shape changed incompatibly (or that disappeared).

    Compatible: adding parameters with defaults at the end, adding *args/**kwargs, renaming nothing.
    """
    def table(text: str) -> Optional[Dict[str, List]]:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            return None
        return {d["qual"]: d["params"] for d in _Defs().run(tree) if d["kind"] != "class"
                and not d["name"].startswith("_")}

    old, new = table(old_text or ""), table(new_text or "")
    if old is None or new is None:
        return []
    out: List[Dict[str, str]] = []
    for qual, oparams in old.items():
        name = qual.rsplit(".", 1)[-1]
        if qual not in new:
            out.append({"qual": qual, "name": name, "reason": "removed or renamed"})
            continue
        nparams = new[qual]
        oldpos = [p[0] for p in oparams if p[1] == "pos" and p[0] not in ("self", "cls")]
        newpos = [p[0] for p in nparams if p[1] == "pos" and p[0] not in ("self", "cls")]
        problems = []
        if newpos[: len(oldpos)] != oldpos:
            problems.append("positional parameters changed (%s -> %s)" % (", ".join(oldpos), ", ".join(newpos)))
        newnames = {p[0]: p for p in nparams}
        for p in oparams:
            if p[1] == "kwonly" and p[0] not in newnames:
                problems.append("keyword parameter %s removed" % p[0])
            if p[1] in ("vararg", "varkw") and not any(q[1] == p[1] for q in nparams):
                problems.append("%s removed" % ("*" + p[0] if p[1] == "vararg" else "**" + p[0]))
        oldnames = {p[0] for p in oparams}
        for p in nparams:
            if p[0] not in oldnames and p[1] in ("pos", "kwonly") and not p[2] and p[0] not in ("self", "cls"):
                problems.append("new required parameter %s" % p[0])
        if problems:
            out.append({"qual": qual, "name": name, "reason": "; ".join(problems)})
    return out


def scan_project(project: str, max_files: int = 600) -> Dict[str, str]:
    """{relative path: absolute path} of Python files, skipping vendored and build directories."""
    found: Dict[str, str] = {}
    for root, dirs, files in os.walk(project):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if f.endswith(".py"):
                ap = os.path.join(root, f)
                try:
                    if os.path.getsize(ap) > MAX_FILE_BYTES:
                        continue
                except OSError:
                    continue
                found[os.path.relpath(ap, project).replace(os.sep, "/")] = ap
                if len(found) >= max_files:
                    return found
    return found


def module_table(paths: List[str]) -> Dict[str, str]:
    return {module_name(p): p for p in paths}
