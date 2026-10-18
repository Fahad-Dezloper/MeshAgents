"""Best-effort: which project files will a shell command write? (pure, never raises)

Edits made through the host's Bash tool (`sed -i`, `cat > f <<E`, `python3 - <<E ... open(p,'w')`) never reach
the edit hooks. `is_write_like` is a cheap check for "this command may change files"; `target_paths`
extracts the project-relative files it will most likely write. A missed path is acceptable (the snapshot
diff in `shellsnap` is the safety net); a wrong path should be rare, so everything uncertain is dropped.
"""

from __future__ import annotations

import glob
import os
import re
from typing import Dict, List, Optional, Tuple

from baton.core.paths import normalize_path

MAX_TARGETS = 20
MAX_CMD_CHARS = 200_000
_SKIP_PARTS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
_JUNK_EXT = {".pyc", ".pyo", ".log", ".tmp", ".swp", ".pid", ".lock", ".out", ".bak", ".orig"}
_KNOWN_NAMES = {"makefile", "dockerfile", "license", "procfile", "gemfile", "rakefile", "readme", "jenkinsfile"}

# ---------------------------------------------------------------------------------------------
# is_write_like: cheap prefilter
# ---------------------------------------------------------------------------------------------
_DEVNULL = re.compile(r"(?:&|\d*)>>?\s*/dev/(?:null|stderr|stdout)|\d*>&\s*\d+|\d*>&-")
_HEREDOC_START = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w.-]*)\1")
_QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
_SH_REDIRECT = re.compile(r"(?:>>|>\||&>|>)")
_SH_WORDS = re.compile(
    r"(?:^|[\s;&|(`])(?:sudo\s+)?(?:tee|install|patch|truncate|rm|cp|mv|ln|shred|rsync|unlink)\s")
_SED_I = re.compile(r"(?:^|[\s;&|(])(?:sed|perl)\b[^|;&\n]*?\s(?:-[A-Za-z]*i[A-Za-z.]*|--in-place\S*)(?:\s|$)")
_GIT_W = re.compile(
    r"(?:^|[\s;&|(])git\s+(?:-C\s+\S+\s+)?(?:apply|checkout|restore|stash|reset|clean|mv|rm|merge|rebase|"
    r"pull|cherry-pick|revert|switch|am|commit\s+-a)\b")
_DD = re.compile(r"(?:^|[\s;&|(])dd\s[^|;&\n]*\bof=")
_INTERP = re.compile(r"\b(?:python[\d.]*|node|nodejs|ruby|perl)\b")
_CODE_W = re.compile(
    r"open\s*\([^)]*['\"][wax][bt+]*['\"]|\.write_text\s*\(|\.write_bytes\s*\(|shutil\.|os\.(?:rename|replace)\s*\("
    r"|writeFile|appendFile|copyFile|renameSync|File\.(?:write|open|rename)|open\s*\(?\s*(?:my\s+)?\$?\w+\s*,\s*['\"]>"
    r"|\.write\s*\(")
_SH_C = re.compile(r"\b(?:ba|z)?sh\s+-l?c\b")


def _skeleton(cmd: str) -> str:
    """The command with heredoc bodies and quoted strings removed (what the shell itself sees)."""
    lines = cmd.split("\n")
    out: List[str] = []
    tag: Optional[str] = None
    for ln in lines:
        if tag is not None:
            if ln.strip() == tag:
                tag = None
            continue
        out.append(ln)
        m = _HEREDOC_START.search(ln)
        if m:
            tag = m.group(2)
    s = "\n".join(out)
    s = _QUOTED.sub("''", s)
    return _DEVNULL.sub(" ", s)


def is_write_like(cmd: str) -> bool:
    """Cheap, liberal: could this shell command change files? False positives only cost a snapshot."""
    try:
        if not cmd or len(cmd) > MAX_CMD_CHARS:
            return False
        sk = _skeleton(cmd)
        if (_SH_REDIRECT.search(sk) or _SH_WORDS.search(sk) or _SED_I.search(sk) or _GIT_W.search(sk)
                or _DD.search(sk)):
            return True
        if _INTERP.search(cmd) and _CODE_W.search(cmd):
            return True
        if _SH_C.search(cmd):
            return bool(_SH_REDIRECT.search(_DEVNULL.sub(" ", cmd)) or _SH_WORDS.search(cmd)
                        or _SED_I.search(cmd) or _GIT_W.search(cmd) or _CODE_W.search(cmd))
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------------------------
# a small shell tokenizer: words, operators, heredoc bodies
# ---------------------------------------------------------------------------------------------
_OPS3 = ("<<<", "&>>", "<<-")
_OPS2 = ("&&", "||", ";;", ">>", ">|", ">&", "&>", "<<", "<&", "|&")
_SEP = {";", "&&", "||", "|", "&", "|&", "\n", ";;", "(", ")"}
_REDIR_OUT = {">", ">>", ">|", "&>", "&>>"}


def _skip_balanced(s: str, i: int, open_c: str, close_c: str) -> int:
    depth = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == open_c:
            depth += 1
        elif c == close_c:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _tokenize(s: str) -> Tuple[List[tuple], List[str]]:
    """Tokens: ('w', text) word | ('o', op, fd) operator | ('h', body_index) heredoc / here-string."""
    toks: List[tuple] = []
    bodies: List[str] = []
    pending: List[Tuple[int, str, bool]] = []  # (body index, tag, dash)
    i, n = 0, len(s)
    buf: List[str] = []
    has = False
    expect_tag: Optional[bool] = None  # None, or dash flag when the next word is a heredoc tag
    expect_str = False

    def flush():
        nonlocal buf, has, expect_tag, expect_str
        if not has:
            return
        w = "".join(buf)
        buf, has = [], False
        if expect_tag is not None:
            bodies.append("")
            pending.append((len(bodies) - 1, w, expect_tag))
            toks.append(("h", len(bodies) - 1))
            expect_tag = None
        elif expect_str:
            bodies.append(w)
            toks.append(("h", len(bodies) - 1))
            expect_str = False
        else:
            toks.append(("w", w))

    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 < n and s[i + 1] == "\n":
                i += 2
                continue
            if i + 1 < n:
                buf.append(s[i + 1])
                has = True
            i += 2
            continue
        if c == "'":
            j = s.find("'", i + 1)
            j = n if j < 0 else j
            buf.append(s[i + 1:j])
            has = True
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            part: List[str] = []
            while j < n and s[j] != '"':
                if s[j] == "\\" and j + 1 < n and s[j + 1] in '"\\$`\n':
                    if s[j + 1] != "\n":
                        part.append(s[j + 1])
                    j += 2
                    continue
                if s[j] == "$" and j + 1 < n and s[j + 1] == "(":
                    k = _skip_balanced(s, j + 1, "(", ")")
                    part.append(s[j:k])
                    j = k
                    continue
                part.append(s[j])
                j += 1
            buf.append("".join(part))
            has = True
            i = j + 1
            continue
        if c == "$" and i + 1 < n and s[i + 1] == "(":
            k = _skip_balanced(s, i + 1, "(", ")")
            buf.append(s[i:k])
            has = True
            i = k
            continue
        if c == "`":
            j = s.find("`", i + 1)
            j = n - 1 if j < 0 else j
            buf.append(s[i:j + 1])
            has = True
            i = j + 1
            continue
        if c == "#" and not has:
            j = s.find("\n", i)
            i = n if j < 0 else j
            continue
        if c in " \t\r":
            flush()
            i += 1
            continue
        if c == "\n":
            flush()
            toks.append(("o", "\n", ""))
            i += 1
            for idx, tag, dash in pending:
                lines: List[str] = []
                while i <= n and i < n + 1:
                    j = s.find("\n", i)
                    ln = s[i:] if j < 0 else s[i:j]
                    i = n + 1 if j < 0 else j + 1
                    cand = ln.lstrip("\t") if dash else ln
                    if cand.rstrip("\r") == tag:
                        break
                    lines.append(ln)
                    if j < 0:
                        break
                bodies[idx] = "\n".join(lines)
            pending = []
            continue
        if c in ";&|<>()":
            fd = ""
            if has and c in "<>" and "".join(buf).isdigit() and not expect_tag:
                fd = "".join(buf)
                buf, has = [], False
            else:
                flush()
            op = c
            for cand in _OPS3:
                if s.startswith(cand, i):
                    op = cand
                    break
            else:
                for cand in _OPS2:
                    if s.startswith(cand, i):
                        op = cand
                        break
            i += len(op)
            if op in ("<<", "<<-"):
                expect_tag = op == "<<-"
            elif op == "<<<":
                expect_str = True
            else:
                toks.append(("o", op, fd))
            continue
        buf.append(c)
        has = True
        i += 1
    flush()
    return toks, bodies


class _Seg:
    __slots__ = ("words", "redirs", "heredocs", "sep")

    def __init__(self):
        self.words: List[str] = []
        self.redirs: List[Tuple[str, str, str]] = []
        self.heredocs: List[int] = []
        self.sep = ""


def _segments(toks: List[tuple]) -> List[_Seg]:
    segs: List[_Seg] = []
    cur = _Seg()
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        if t[0] == "w":
            cur.words.append(t[1])
        elif t[0] == "h":
            cur.heredocs.append(t[1])
        else:
            op = t[1]
            if op in _SEP:
                cur.sep = op
                if cur.words or cur.redirs or cur.heredocs:
                    segs.append(cur)
                cur = _Seg()
            elif op in _REDIR_OUT or op in (">&", "<", "<&"):
                if i + 1 < n and toks[i + 1][0] == "w":
                    cur.redirs.append((op, t[2], toks[i + 1][1]))
                    i += 1
        i += 1
    if cur.words or cur.redirs or cur.heredocs:
        segs.append(cur)
    return segs


# ---------------------------------------------------------------------------------------------
# code analysis (python / node / ruby / perl)
# ---------------------------------------------------------------------------------------------
_LIT = r"""(?:'[^'\\\n]*'|"[^"\\\n]*"|`[^`\\\n$]*`)"""
_PATHCALL = r"(?:pathlib\.)?Path\(\s*" + _LIT + r"\s*\)"
_JOIN = r"os\.path\.join\(\s*" + _LIT + r"(?:\s*,\s*" + _LIT + r")*\s*\)"
_ARG = r"(?:" + _JOIN + "|" + _PATHCALL + "|" + _LIT + r"|[A-Za-z_]\w*)"
_ASSIGN = re.compile(r"(?<![\w.])([A-Za-z_]\w*)\s*(?::\s*\w+\s*)?=(?!=)\s*(" + _JOIN + "|" + _PATHCALL + "|" + _LIT + ")?")
_FOR = re.compile(r"\bfor\s+([A-Za-z_]\w*)\s+in\s+[\[(]((?:\s*" + _LIT + r"\s*,?)+)[\])]")
_LITS = re.compile(_LIT)

_PY_W = [
    re.compile(r"\bopen\(\s*(" + _ARG + r")\s*,\s*(?:mode\s*=\s*)?(['\"])([wax][bt+]*)\2"),
    re.compile(r"\bopen\(\s*(" + _ARG + r")\s*,\s*(?:mode\s*=\s*)?(['\"])(r\+[bt]*)\2"),
    re.compile(r"(" + _PATHCALL + r"|(?<![\w.])[A-Za-z_]\w*)\s*\.\s*(write_text|write_bytes)\s*\("),
    re.compile(r"\bshutil\.(?:copy|copy2|copyfile|move)\(\s*" + _ARG + r"\s*,\s*(" + _ARG + r")"),
    re.compile(r"\bos\.(?:rename|replace)\(\s*(" + _ARG + r")\s*,\s*(" + _ARG + r")"),
]
_JS_W = [
    re.compile(r"\b(?:writeFileSync|writeFile|appendFileSync|appendFile|createWriteStream)\(\s*(" + _ARG + r")"),
    re.compile(r"\b(?:copyFileSync|copyFile|renameSync|rename)\(\s*" + _ARG + r"\s*,\s*(" + _ARG + r")"),
]
_RB_W = [
    re.compile(r"\bFile\.(?:write|binwrite)\(\s*(" + _ARG + r")"),
    re.compile(r"\bFile\.open\(\s*(" + _ARG + r")\s*,\s*['\"][wa]"),
    re.compile(r"\bFile\.rename\(\s*" + _ARG + r"\s*,\s*(" + _ARG + r")"),
]
_PERL_W = [re.compile(r"\bopen\s*\(?\s*(?:my\s+)?\$?\w+\s*,\s*['\"]>>?['\"]\s*,\s*(" + _ARG + r")")]


def _lit_value(tok: str) -> Optional[str]:
    tok = tok.strip()
    if len(tok) >= 2 and tok[0] in "'\"`" and tok[-1] == tok[0]:
        return tok[1:-1]
    return None


def _eval_arg(arg: str, env: Dict[str, List[str]]) -> List[str]:
    arg = arg.strip()
    v = _lit_value(arg)
    if v is not None:
        return [v]
    m = re.fullmatch(r"(?:pathlib\.)?Path\(\s*(" + _LIT + r")\s*\)", arg)
    if m:
        v = _lit_value(m.group(1))
        return [v] if v is not None else []
    if arg.startswith("os.path.join("):
        parts = [_lit_value(x) for x in _LITS.findall(arg)]
        if parts and all(p is not None for p in parts):
            return ["/".join(p.strip("/") if i else p for i, p in enumerate(parts))]  # type: ignore[union-attr]
        return []
    return list(env.get(arg, []))


def _code_writes(code: str, lang: str) -> List[str]:
    """Literal paths a short script opens for writing, tracking simple variable assignments in order."""
    if lang == "python":
        patterns = _PY_W
    elif lang == "node":
        patterns = _JS_W
    elif lang == "ruby":
        patterns = _RB_W
    else:
        patterns = _PERL_W
    events: List[Tuple[int, int, str, tuple]] = []
    for m in _ASSIGN.finditer(code):
        events.append((m.start(), 0, "assign", (m.group(1), m.group(2))))
    for m in _FOR.finditer(code):
        events.append((m.start(), 0, "for", (m.group(1), m.group(2))))
    for pi, pat in enumerate(patterns):
        for m in pat.finditer(code):
            args = (m.group(1), m.group(2)) if (lang == "python" and pi == 4) else (m.group(1),)
            events.append((m.start(), 1, "w", args))
    events.sort(key=lambda e: (e[0], e[1]))
    env: Dict[str, List[str]] = {}
    out: List[str] = []
    for _, _, kind, data in events:
        if kind == "assign":
            name, val = data
            if val:
                vals = _eval_arg(val, env)
                if vals:
                    env[name] = vals
                    continue
            env.pop(name, None)
        elif kind == "for":
            name, items = data
            vals = [x for x in (_lit_value(t) for t in _LITS.findall(items)) if x is not None]
            if vals:
                env[name] = vals
        else:
            for arg in data:
                for v in _eval_arg(arg, env):
                    if v not in out:
                        out.append(v)
    return out


# ---------------------------------------------------------------------------------------------
# per-command extraction
# ---------------------------------------------------------------------------------------------
_PY = re.compile(r"python[\d.]*")
_ENV_ASSIGN = re.compile(r"[A-Za-z_]\w*=")
_WRAPPERS = {"sudo", "env", "command", "time", "nohup", "exec", "builtin", "nice"}
_SED_IN_PLACE = re.compile(r"-[nEerszu]*i.*|--in-place.*")


def _positional(args: List[str], takes_value: Tuple[str, ...] = ()) -> List[str]:
    out: List[str] = []
    skip = False
    after_dd = False
    for a in args:
        if skip:
            skip = False
            continue
        if after_dd:
            out.append(a)
        elif a == "--":
            after_dd = True
        elif a in takes_value:
            skip = True
        elif a.startswith("-") and len(a) > 1:
            continue
        else:
            out.append(a)
    return out


def _interp_code(name: str, args: List[str], heredocs: List[str]) -> Optional[Tuple[str, str]]:
    """(language, code) when the command runs inline code (-c / -e / stdin heredoc)."""
    if _PY.fullmatch(name):
        lang, flags = "python", ("-c",)
    elif name in ("node", "nodejs"):
        lang, flags = "node", ("-e", "--eval", "-p", "--print")
    elif name == "ruby":
        lang, flags = "ruby", ("-e",)
    elif name == "perl":
        lang, flags = "perl", ("-e", "-E")
    else:
        return None
    i = 0
    while i < len(args):
        a = args[i]
        if a in flags and i + 1 < len(args):
            return lang, args[i + 1]
        if lang == "python" and a == "-m":
            return None
        if lang == "python" and a in ("-W", "-X"):
            i += 2
            continue
        if a == "-" and heredocs:
            return lang, "\n".join(heredocs)
        if not a.startswith("-"):
            return None  # runs a script file: contents unknown
        i += 1
    if heredocs:
        return lang, "\n".join(heredocs)
    return None


def _command_writes(seg: _Seg, bodies: List[str], depth: int) -> Tuple[List[str], List[str]]:
    """(paths the segment writes, paths whose rename/removal it performs). Raw strings, base-relative."""
    words = seg.words
    i = 0
    while i < len(words) and (_ENV_ASSIGN.match(words[i]) or words[i] in _WRAPPERS):
        i += 1
    if i >= len(words):
        return [], []
    name = os.path.basename(words[i])
    args = words[i + 1:]
    heredocs = [bodies[k] for k in seg.heredocs if 0 <= k < len(bodies)]
    out: List[str] = []

    if name == "git":
        j = 0
        while j < len(args) and args[j].startswith("-"):
            j += 2 if args[j] in ("-C", "-c") else 1
        sub = args[j] if j < len(args) else ""
        rest = args[j + 1:]
        if sub == "mv":
            pos = _positional(rest)
            return _move_targets(pos, rest)
        if sub == "rm":
            return [p for p in _positional(rest)], []
        if sub in ("checkout", "restore"):
            if "--" in rest:
                return rest[rest.index("--") + 1:], []
            if sub == "restore":
                return _positional(rest, ("-s", "--source")), []
        return [], []
    if name == "tee":
        return _positional(args), []
    if name == "sed":
        in_place = any(_SED_IN_PLACE.fullmatch(a) for a in args if a.startswith("-") and not a.startswith("--")
                       ) or any(a.startswith("--in-place") for a in args)
        if not in_place:
            return [], []
        have_script = False
        rest: List[str] = []
        k = 0
        while k < len(args):
            a = args[k]
            if a in ("-e", "-f", "--expression", "--file"):
                have_script = True
                k += 2
                continue
            if a.startswith("--expression=") or a.startswith("--file="):
                have_script = True
            elif a == "--":
                rest += args[k + 1:]
                break
            elif a.startswith("-") and len(a) > 1:
                pass
            elif a == "":
                pass
            else:
                rest.append(a)
            k += 1
        return (rest if have_script else rest[1:]), []
    if name == "perl":
        in_place = any(re.fullmatch(r"-[A-Za-z]*i[^\s]*", a) for a in args if a.startswith("-") and not a.startswith("--"))
        if in_place:
            have_e = any(a in ("-e", "-E") for a in args)
            rest = _positional(args, ("-e", "-E", "-I", "-M", "-m"))
            if have_e:
                return rest, []
            return rest[1:], []
    if name in ("cp", "install", "ln", "mv"):
        return _move_targets(_positional(args, ("-t", "--target-directory", "-m", "--mode", "-o", "-g", "-S")), args,
                             move=(name == "mv"), name=name)
    if name == "dd":
        return [a[3:] for a in args if a.startswith("of=")], []
    if name == "truncate":
        return _positional(args, ("-s", "--size", "-r", "--reference")), []
    if name == "rm":
        return [p for p in _positional(args)], []
    if name == "patch":
        pos = _positional(args, ("-p", "-i", "-d", "-o", "-r", "-F"))
        return pos[:1], []
    if name in ("bash", "sh", "zsh"):
        if depth < 2:
            if "-c" in args and args.index("-c") + 1 < len(args):
                return _analyze_text(args[args.index("-c") + 1], depth + 1), []
            if heredocs:
                return [p for h in heredocs for p in _analyze_text(h, depth + 1)], []
        return [], []
    code = _interp_code(name, args, heredocs)
    if code:
        lang, text = code
        return _code_writes(text, lang), []
    return [], []


def _move_targets(pos: List[str], args: List[str], move: bool = True, name: str = "mv"):
    """Destinations of cp/mv/install/ln (and, for mv, the sources, like the existing rename handling)."""
    tdir = None
    for k, a in enumerate(args):
        if a in ("-t", "--target-directory") and k + 1 < len(args):
            tdir = args[k + 1]
        elif a.startswith("--target-directory="):
            tdir = a.split("=", 1)[1]
    if tdir is not None:
        out = [tdir.rstrip("/") + "/" + os.path.basename(s.rstrip("/")) for s in pos]
        return out, []
    if len(pos) < 2:
        return [], []
    srcs, dst = pos[:-1], pos[-1]
    out = [("DIR:" + dst + "|" + os.path.basename(s.rstrip("/"))) for s in srcs]  # resolved against the fs later
    if move and name == "mv":
        out += srcs
    return out, []


def _analyze_text(text: str, depth: int = 0) -> List[str]:
    """Context-free: every raw target in `text`, without cd handling (used for nested shells)."""
    toks, bodies = _tokenize(text)
    out: List[str] = []
    for seg in _segments(toks):
        out += _seg_targets(seg, bodies, depth)
    return out


def _seg_targets(seg: _Seg, bodies: List[str], depth: int) -> List[str]:
    out: List[str] = []
    for op, fd, target in seg.redirs:
        if op in _REDIR_OUT and fd in ("", "1"):
            out.append(target)
    w, _ = _command_writes(seg, bodies, depth)
    return out + w


def _clean(p: str) -> Optional[str]:
    p = p.strip().strip("'\"")
    if not p or p == "-" or "$" in p or "`" in p or "{" in p or "\n" in p or len(p) > 400:
        return None
    return p


def _inside(abs_p: str, project: str) -> Optional[str]:
    abs_p = os.path.normpath(abs_p)
    project = os.path.normpath(project)
    if abs_p == project or not abs_p.startswith(project + os.sep):
        return None
    rel = normalize_path(os.path.relpath(abs_p, project))
    parts = rel.split("/")
    if rel.startswith("..") or any(x in _SKIP_PARTS or (x.startswith(".git") and x != ".gitignore") for x in parts[:-1]):
        return None
    if parts[-1] in (".git", ".") or parts[-1].startswith(".git") and parts[-1] not in (".gitignore", ".gitattributes"):
        return None
    return rel


def _looks_like_file(abs_p: str, rel: str) -> bool:
    if os.path.isdir(abs_p):
        return False
    if os.path.isfile(abs_p):
        return True
    base = os.path.basename(rel)
    ext = os.path.splitext(base)[1].lower()
    if ext and ext not in _JUNK_EXT and not base.endswith("."):
        return True
    return base.lower() in _KNOWN_NAMES


def target_paths(cmd: str, cwd: Optional[str], project: str) -> List[str]:
    """Project-relative files `cmd` will (most likely) write. Never raises; [] when unsure."""
    try:
        return _target_paths(cmd, cwd, project)
    except Exception:
        return []


def _target_paths(cmd: str, cwd: Optional[str], project: str) -> List[str]:
    if not cmd or len(cmd) > MAX_CMD_CHARS or not project:
        return []
    project = os.path.abspath(project)
    base = os.path.abspath(cwd) if cwd else project
    toks, bodies = _tokenize(cmd)
    out: List[str] = []

    def add(raw: str, at: str) -> None:
        if len(out) >= MAX_TARGETS:
            return
        dir_form = None
        if raw.startswith("DIR:"):
            d, _, b = raw[4:].partition("|")
            dir_form = (d, b)
            raw = d
        p = _clean(raw)
        if p is None or p.startswith("/dev/"):
            return
        p = os.path.expanduser(p)
        ap = p if os.path.isabs(p) else os.path.join(at, p)
        if dir_form:
            if os.path.isdir(ap) or dir_form[0].endswith("/"):
                ap = os.path.join(ap, dir_form[1])
        cands = [ap]
        if any(ch in os.path.basename(ap) or ch in ap for ch in "*?["):
            cands = [g for g in sorted(glob.glob(ap)) if os.path.isfile(g)][:MAX_TARGETS]
        for c in cands:
            rel = _inside(c, project)
            if rel and _looks_like_file(os.path.normpath(c), rel) and rel not in out:
                out.append(rel)

    cur = base
    for seg in _segments(toks):
        w = seg.words
        if w and w[0] == "cd" and len(w) >= 2 and seg.sep in ("&&", ";", "\n", ""):
            d = _clean(w[1])
            if d:
                d = os.path.expanduser(d)
                cur = os.path.normpath(d if os.path.isabs(d) else os.path.join(cur, d))
            continue
        for raw in _seg_targets(seg, bodies, 0):
            add(raw, cur)
    return out
