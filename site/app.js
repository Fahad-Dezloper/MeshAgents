/* Renders the page from CONFIG (config.js) and FACTS (facts.js). No dependencies, works from file://. */
(function () {
  "use strict";
  var C = window.CONFIG || {}, F = window.FACTS || {};
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var STATIC = /[?&]static\b/.test(location.search); /* ?static shows everything at once (printing, screenshots) */
  if (STATIC) reduce = true;
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function get(path) {
    return path.split(".").reduce(function (o, k) { return o == null ? o : o[k]; }, F);
  }
  function fmtNum(v, dec) {
    if (typeof v !== "number") return String(v);
    return v.toLocaleString("en-US", { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  }
  /* format one value: data-fmt = num | usd | plain; data-dec, data-prefix, data-suffix */
  function fmt(v, o) {
    var dec = o.dec || 0;
    var s = o.fmt === "usd" ? "$" + v.toFixed(dec) : o.fmt === "plain" ? String(v) : fmtNum(v, dec);
    return (o.prefix || "") + s + (o.suffix || "");
  }
  function opts(el) {
    var d = el.dataset;
    return { fmt: d.fmt || "num", dec: d.dec ? +d.dec : 0, prefix: d.prefix || "", suffix: d.suffix || "" };
  }

  if (STATIC) document.documentElement.classList.add("static");
  if (STATIC) Array.prototype.forEach.call(document.querySelectorAll("details"), function (d) { d.open = true; });

  /* marquee: duplicate the set once for a seamless loop */
  var ms = $(".marq-set");
  if (ms) { var cl = ms.cloneNode(true); cl.setAttribute("aria-hidden", "true"); ms.parentNode.appendChild(cl); if (reduce) cl.style.display = "none"; }

  /* ---------- config ---------- */
  var name = C.name || "this tool";
  document.title = name + ": " + (C.tagline || "");
  $$("[data-name]").forEach(function (e) { e.textContent = name; });
  $$("[data-tagline]").forEach(function (e) { e.textContent = C.tagline || ""; });
  $$("a[data-repo]").forEach(function (a) { a.href = C.repo || "#"; });
  $$("[data-repo-note]").forEach(function (e) {
    e.textContent = C.repoIsPlaceholder ? "Repository link is a placeholder: " + C.repo : "";
  });
  $$("[data-link]").forEach(function (a) {
    var url = C[a.dataset.link], label = a.dataset.link === "video" ? "Video" : "Blog";
    if (url) { a.href = url; a.textContent = label; }
    else { var s = document.createElement("span"); s.className = "soon"; s.textContent = label + " (coming soon)"; a.replaceWith(s); }
  });

  /* ---------- facts ---------- */
  $$("[data-fact]").forEach(function (el) {
    var v = get(el.dataset.fact);
    if (v === undefined || v === null) { el.textContent = "?"; el.title = "missing fact"; return; }
    el.textContent = fmt(v, opts(el));
  });

  /* ---------- charts ---------- */
  var nm = function () { return name; };
  function row(lab, sub, bars, o) {
    o = o || {};
    var d = document.createElement("div");
    d.className = "row" + (o.hl ? " hl" : "") + (o.big ? " big-bars" : "");
    var l = document.createElement("div"); l.className = "lab"; l.textContent = lab;
    if (sub) { var s = document.createElement("small"); s.textContent = sub; l.appendChild(s); }
    var b = document.createElement("div"); b.className = "bars";
    bars.forEach(function (x) {
      var r = document.createElement("div"); r.className = "bar";
      var t = document.createElement("span"); t.className = "track";
      var f = document.createElement("span"); f.className = "fill" + (x.acc ? " acc" : "");
      f.style.setProperty("--w", Math.max(0, Math.min(100, x.v / x.max * 100)) + "%");
      t.appendChild(f);
      var n = document.createElement("b"); n.textContent = x.text;
      r.appendChild(t); r.appendChild(n); b.appendChild(r);
    });
    d.appendChild(l); d.appendChild(b);
    return d;
  }
  function fill(sel, rows) { var host = $('[data-chart="' + sel + '"]'); if (host) rows.forEach(function (r) { host.appendChild(r); }); }

  var col = F.collision, mem = F.memory, cost = F.cost, co = F.cochange;
  if (col) {
    fill("levels", col.levels.map(function (L) {
      return row(L.id, L.note || "", [
        { v: L.without, max: 10, text: L.without + "/10" },
        { v: L.with, max: 10, text: L.with + "/10", acc: true }
      ], { hl: L.id === "L3" });
    }));
  }
  if (mem) {
    fill("memory", [
      row("No memory", "", [{ v: mem.none_pct, max: 100, text: mem.none_pct + "%" }], { big: true }),
      row("Hand-kept notes file", "", [{ v: mem.notes_pct, max: 100, text: mem.notes_pct + "%" }], { big: true }),
      row(name, "", [{ v: mem.tool_pct, max: 100, text: mem.tool_pct + "%", acc: true }], { big: true, hl: true })
    ]);
    var mc = Math.max(mem.cost_success_none, mem.cost_success_notes, mem.cost_success_tool);
    var usd = function (v) { return "$" + v.toFixed(4); };
    fill("memory-cost", [
      row("No memory", "", [{ v: mem.cost_success_none, max: mc, text: usd(mem.cost_success_none) }]),
      row("Notes file", "", [{ v: mem.cost_success_notes, max: mc, text: usd(mem.cost_success_notes) }]),
      row(name, "", [{ v: mem.cost_success_tool, max: mc, text: usd(mem.cost_success_tool), acc: true }])
    ]);
  }
  if (cost && col) {
    var x = function (v) { return v.toFixed(2) + "x"; };
    fill("cost-ratio", [
      row("First version", "", [{ v: cost.first_ratio, max: 1.5, text: x(cost.first_ratio) }]),
      row("Shipped version", "", [{ v: cost.shipped_ratio, max: 1.5, text: x(cost.shipped_ratio), acc: true }]),
      row("No plugin", "", [{ v: cost.base_ratio, max: 1.5, text: x(cost.base_ratio) }])
    ]);
    var u = function (v) { return "$" + v.toFixed(4); }, mx = col.cost_clean_without;
    var mkClean = function () { return [
      row("Without", "", [{ v: col.cost_clean_without, max: mx, text: u(col.cost_clean_without) }]),
      row("With " + name, "", [{ v: col.cost_clean_with, max: mx, text: u(col.cost_clean_with), acc: true }])
    ]; };
    fill("cost-clean", mkClean()); fill("feat-cost", mkClean());
  }
  if (co) {
    var p = function (v) { return v.toFixed(1) + "%"; };
    fill("cochange", [
      row(name + " hint", "learned from git history", [{ v: co.hit_pct_same_cases, max: 100, text: p(co.hit_pct_same_cases), acc: true }], { big: true, hl: true }),
      row("Same-folder guess", "", [{ v: co.same_folder_pct, max: 100, text: p(co.same_folder_pct) }], { big: true }),
      row("Most-changed files", "", [{ v: co.most_changed_pct, max: 100, text: p(co.most_changed_pct) }], { big: true })
    ]);
  }

  /* ---------- reveal + count-up ---------- */
  function countUp(el) {
    var v = get(el.dataset.fact), o = opts(el);
    if (typeof v !== "number") return;
    if (reduce) { el.textContent = fmt(v, o); return; }
    var t0 = null, dur = 1400;
    function step(t) {
      if (t0 === null) t0 = t;
      var k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmt(k === 1 ? v : v * e, o);
      if (k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var counted = [];
  function reveal(el) {
    el.classList.add("in");
    $$("[data-count]", el).concat(el.hasAttribute && el.hasAttribute("data-count") ? [el] : []).forEach(function (c) {
      if (counted.indexOf(c) < 0) { counted.push(c); countUp(c); }
    });
  }
  var targets = $$(".reveal, .proof-card, [data-chart]").filter(function (e, i, a) { return a.indexOf(e) === i; });
  var lone = $$("[data-count]").filter(function (c) { return !c.closest(".reveal"); });
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    targets.forEach(function (t) { io.observe(t); });
    lone.forEach(function (c) { io.observe(c); });
  } else {
    targets.forEach(reveal); lone.forEach(function (c) { countUp(c); });
  }

  /* ---------- calculator ---------- */
  var cf = F.calc, g = F.collision;
  var iS = $("#i-sess"), iC = $("#i-cost"), iP = $("#i-share");
  if (iS && cf && g) {
    iS.value = cf.default_sessions; iC.value = cf.default_cost; iP.value = cf.default_share_pct;
    var money = function (n) { return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
    var upd = function () {
      var s = +iS.value, c = +iC.value, sh = +iP.value / 100;
      [iS, iC, iP].forEach(function (i) { i.style.setProperty("--p", ((i.value - i.min) / (i.max - i.min) * 100) + "%"); });
      $("#o-sess").textContent = s;
      $("#o-cost").textContent = "$" + c.toFixed(2);
      $("#o-share").textContent = iP.value + "%";
      var month = s * cf.weeks_per_month;
      var points = sh * g.gap_points;
      var reruns = month * sh * g.gap_points / 100;
      var saved = month * sh * c * g.cost_clean_drop_pct / 100;
      $("#r-points").textContent = "+" + points.toFixed(1) + " points";
      $("#r-reruns").textContent = reruns.toFixed(1);
      $("#r-money").textContent = money(saved);
    };
    [iS, iC, iP].forEach(function (i) { i.addEventListener("input", upd); });
    upd();
  }

  /* ---------- install commands ---------- */
  var host = $("#install");
  function fillCmd(s) {
    return s.replace(/\{repo\}/g, C.repo || "<repo-url>").replace(/\{cli\}/g, C.cli || name).replace(/\{dir\}/g, C.dir || name);
  }
  function copyText(text, btn) {
    var done = function () { btn.textContent = "Copied"; setTimeout(function () { btn.textContent = "Copy"; }, 1600); };
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { btn.textContent = "Press Ctrl+C"; }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  }
  if (host && C.install) {
    C.install.forEach(function (it) {
      var cmd = fillCmd(it.cmd);
      var w = document.createElement("div"); w.className = "cmd reveal";
      var h = document.createElement("h4"); h.textContent = it.label;
      var box = document.createElement("div"); box.className = "cmd-box";
      var pre = document.createElement("pre"); var code = document.createElement("code");
      code.style.background = "none"; code.style.padding = "0"; code.textContent = cmd; pre.appendChild(code);
      var b = document.createElement("button"); b.type = "button"; b.className = "copy"; b.textContent = "Copy";
      b.setAttribute("aria-label", "Copy command");
      b.addEventListener("click", function () { copyText(cmd.replace(/\s+#.*$/gm, ""), b); });
      box.appendChild(pre); box.appendChild(b); w.appendChild(h); w.appendChild(box); host.appendChild(w);
      if ("IntersectionObserver" in window && !reduce) io.observe(w); else w.classList.add("in");
    });
  }

  /* ---------- hero command pill ---------- */
  var hc = $("#hero-cmd");
  if (hc) {
    var hcmd = fillCmd(C.heroCmd || "git clone {repo} {dir}");
    $("code", hc).textContent = hcmd;
    var hb = $(".cp-btn", hc);
    hb.addEventListener("click", function () {
      var lab = $("span", hb);
      copyText(hcmd, { set textContent(v) { lab.textContent = v; }, get textContent() { return lab.textContent; } });
    });
  }

  /* ---------- results wall arrows ---------- */
  var wall = $("#wall");
  $$(".ar").forEach(function (b) {
    b.addEventListener("click", function () { wall.scrollBy({ left: +b.dataset.dir * 360, behavior: reduce ? "auto" : "smooth" }); });
  });

  /* ---------- theme ---------- */
  var tb = $("#theme");
  if (tb) tb.addEventListener("click", function () {
    var r = document.documentElement, n = r.getAttribute("data-theme") === "dark" ? "light" : "dark";
    r.setAttribute("data-theme", n);
    try { localStorage.setItem("theme", n); } catch (e) {}
  });
})();
