"""Checks that the marketing site only shows numbers that exist in site/facts.js.

Rules enforced:
  1. facts.js parses (strict JSON inside `window.FACTS = {...};`) and every group has a `_src` note.
  2. Every data-fact path used in index.html resolves to a value in facts.js.
  3. Every number in visible text is either inside a data-fact element and present in facts.js, or is a
     structural integer 0-10 (list numbers, "3 steps", level names) with no %, $ or decimals attached.
     Anything else (a percentage, dollar amount, decimal or larger number) outside a data-fact binding fails.
  4. Every element with class "big" or "n" carrying a number is bound with data-fact.
  5. The product name is not hard-coded in index.html (it comes from config.js).
"""
import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def load_facts():
    text = (SITE / "facts.js").read_text()
    m = re.search(r"window\.FACTS\s*=\s*(\{.*\})\s*;?\s*$", re.sub(r"/\*.*?\*/", "", text, flags=re.S), re.S)
    assert m, "facts.js must contain window.FACTS = {...};"
    return json.loads(m.group(1))


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            if k.startswith("_"):
                continue
            yield from walk(v, path + k + ".")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, path + str(i) + ".")
    else:
        yield path[:-1], node


def resolve(facts, path):
    cur = facts
    for k in path.split("."):
        cur = cur[int(k)] if isinstance(cur, list) else cur[k]
    return cur


def norm(tok):
    return tok.replace(",", "")


def number_forms(v):
    """All textual forms in which a fact value may legitimately appear."""
    forms = set()
    if isinstance(v, bool):
        return forms
    if isinstance(v, (int, float)):
        forms.add(norm(("%f" % v).rstrip("0").rstrip(".")))
        for dec in range(0, 5):
            forms.add("%.*f" % (dec, v))
        forms.add(str(v))
    else:
        forms.update(norm(t) for t in NUM.findall(str(v)))
    return forms


class Page(HTMLParser):
    SKIP = {"script", "style", "pre", "svg", "title", "head"}

    def __init__(self):
        super().__init__()
        self.stack = []          # (tag, is_fact, skip)
        self.fact_paths = []
        self.bound = []          # (path, text)
        self.unbound = []        # visible text outside bindings
        self.big_unbound = []
        self._cur_fact = None
        self.raw_text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("br", "img", "meta", "link", "input"):
            return
        is_fact = "data-fact" in a
        if is_fact:
            self.fact_paths.append(a["data-fact"])
        cls = (a.get("class") or "").split()
        bigish = "big" in cls
        self.stack.append((tag, a.get("data-fact"), tag in self.SKIP, bigish, "data-name" in a))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if any(s[2] for s in self.stack):
            return
        fact = next((s[1] for s in reversed(self.stack) if s[1]), None)
        if fact:
            self.bound.append((fact, data))
            return
        if any(s[3] for s in self.stack):
            self.big_unbound.append(data)
        self.unbound.append(data)


def parse_page():
    p = Page()
    p.feed((SITE / "index.html").read_text())
    return p


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facts = load_facts()
        cls.page = parse_page()
        cls.allowed = set()
        for _p, v in walk(cls.facts):
            cls.allowed |= number_forms(v)

    def test_facts_have_sources(self):
        for group, body in self.facts.items():
            self.assertIn("_src", body, "fact group %r has no _src note" % group)
            self.assertTrue(body["_src"].strip())

    def test_every_binding_resolves(self):
        self.assertGreater(len(self.page.fact_paths), 50)
        for path in self.page.fact_paths:
            try:
                v = resolve(self.facts, path)
            except (KeyError, IndexError, ValueError):
                self.fail("data-fact %r not found in facts.js" % path)
            self.assertNotIsInstance(v, (dict, list), path)

    def test_bound_text_matches_facts(self):
        for path, text in self.page.bound:
            v = resolve(self.facts, path)
            forms = number_forms(v)
            for tok in NUM.findall(text):
                self.assertIn(norm(tok), forms, "%r shows %r but fact is %r" % (path, text, v))

    def test_no_unbound_claims(self):
        bad = []
        for text in self.page.unbound:
            for m in NUM.finditer(text):
                tok = norm(m.group())
                before, after = text[max(0, m.start() - 1):m.start()], text[m.end():m.end() + 1]
                structural = "." not in tok and tok.isdigit() and int(tok) <= 10 and after != "%" and before != "$"
                if not structural:
                    bad.append((m.group(), text.strip()[:70]))
        self.assertEqual(bad, [], "numbers outside a data-fact binding: %s" % bad)

    def test_big_numerals_are_bound(self):
        for t in self.page.big_unbound:
            self.assertFalse(NUM.search(t), "big numeral without data-fact: %r" % t)

    def test_name_not_hard_coded(self):
        html = (SITE / "index.html").read_text()
        stripped = re.sub(r"<(pre|script|style)\b.*?</\1>", "", html, flags=re.S | re.I)
        name = re.search(r'name:\s*"([^"]+)"', (SITE / "config.js").read_text()).group(1)
        self.assertNotIn(name.lower(), stripped.lower(), "product name is hard-coded in index.html")

    def test_calc_defaults_and_no_external_resources(self):
        html = (SITE / "index.html").read_text()
        self.assertNotRegex(html, r'(?:src|href)="https?://')
        self.assertEqual(self.facts["calc"]["default_sessions"], 40)
        self.assertEqual(self.facts["calc"]["default_cost"], 0.5)
        self.assertEqual(self.facts["calc"]["default_share_pct"], 20)

    def test_levels_add_up(self):
        c = self.facts["collision"]
        self.assertEqual(sum(l["with"] for l in c["levels"]), c["with_clean"])
        self.assertEqual(sum(l["without"] for l in c["levels"]), c["without_clean"])
        self.assertEqual(round(100 * c["with_clean"] / c["runs_per_side"]), c["with_pct"])
        self.assertEqual(round(100 * c["without_clean"] / c["runs_per_side"]), c["without_pct"])
        m = self.facts["memory"]
        self.assertEqual(round(100 * m["tool_pass"] / m["pooled_runs_each"]), m["tool_pct"])
        self.assertEqual(round(100 * m["none_pass"] / m["pooled_runs_each"]), m["none_pct"])


if __name__ == "__main__":
    unittest.main()
