/* Renders the page from CONFIG (config.js) and FACTS (facts.js). No dependencies, works from file://. */
(function () {
  "use strict";
  var C = window.CONFIG || {}, F = window.FACTS || {};
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var STATIC = /[?&]static\b/.test(location.search); /* ?static shows everything at once (printing, screenshots) */
  if (STATIC) { reduce = true; document.documentElement.classList.add("static"); }
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  function get(path) { return path.split(".").reduce(function (o, k) { return o == null ? o : o[k]; }, F); }
  function fmtNum(v, dec) {
    if (typeof v !== "number") return String(v);
    return v.toLocaleString("en-US", { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  }
  function fmt(v, o) {
    var dec = o.dec || 0;
    var s = o.fmt === "usd" ? "$" + v.toFixed(dec) : o.fmt === "plain" ? String(v) : fmtNum(v, dec);
    return (o.prefix || "") + s + (o.suffix || "");
  }
  function opts(el) { var d = el.dataset; return { fmt: d.fmt || "num", dec: d.dec ? +d.dec : 0, prefix: d.prefix || "", suffix: d.suffix || "" }; }
  function fillCmd(s) {
    return s.replace(/\{repo\}/g, C.repo || "<repo-url>").replace(/\{cli\}/g, C.cli || C.name).replace(/\{dir\}/g, C.dir || C.name);
  }

  /* marquee: duplicate the set once for a seamless loop */
  var ms = $(".marq-set");
  if (ms) { var cl = ms.cloneNode(true); cl.setAttribute("aria-hidden", "true"); ms.parentNode.appendChild(cl); if (reduce) cl.style.display = "none"; }

  /* ---------- config ---------- */
  var name = C.name || "this tool";
  document.title = name + ": " + (C.tagline || "");
  $$("[data-name]").forEach(function (e) { e.textContent = name; });
  $$("[data-tagline]").forEach(function (e) { e.textContent = C.tagline || ""; });
  $$("a[data-repo]").forEach(function (a) { a.href = C.repo || "#"; });
  $$("a[data-results]").forEach(function (a) { a.href = (C.repo || "") + "/blob/main/docs/RESULTS.md"; });
  $$("a[data-video]").forEach(function (a) { if (C.video) { a.href = C.video; a.hidden = false; } });
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

  /* ---------- copy ---------- */
  function copyText(text, setLabel, idle) {
    var done = function () { setLabel("Copied"); setTimeout(function () { setLabel(idle); }, 1600); };
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = text; ta.setAttribute("readonly", "");
      ta.style.position = "fixed"; ta.style.opacity = "0"; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { setLabel("Press Ctrl+C"); }
      document.body.removeChild(ta);
    }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  }
  var hc = $("#hero-cmd");
  if (hc) {
    var hcmd = fillCmd(C.heroCmd || "git clone {repo}"), lab = $(".cp-btn span", hc);
    $("code", hc).textContent = hcmd;
    $(".cp-btn", hc).addEventListener("click", function () { copyText(hcmd, function (t) { lab.textContent = t; }, "Copy"); });
  }
  var host = $("#steps");
  if (host && C.steps) {
    C.steps.forEach(function (it, i) {
      var cmd = fillCmd(it.cmd), w = document.createElement("div"); w.className = "st reveal" + (i ? " d" + i : "");
      var n = document.createElement("span"); n.className = "num"; n.textContent = String(i + 1);
      var h = document.createElement("h3"); h.textContent = it.label;
      var box = document.createElement("div"); box.className = "cmd-box";
      var pre = document.createElement("pre"); pre.textContent = cmd;
      var b = document.createElement("button"); b.type = "button"; b.className = "copy"; b.textContent = "Copy"; b.setAttribute("aria-label", "Copy command");
      b.addEventListener("click", function () { copyText(cmd, function (t) { b.textContent = t; }, "Copy"); });
      box.appendChild(pre); box.appendChild(b); w.appendChild(n); w.appendChild(h); w.appendChild(box); host.appendChild(w);
    });
  }
  var after = $("#after");
  if (after && C.after) {
    var txt = fillCmd(C.after), m = txt.match(/^(.*?run )(.+?)( to .*)$/);
    if (m) { after.appendChild(document.createTextNode(m[1])); var cd = document.createElement("code"); cd.textContent = m[2]; after.appendChild(cd); after.appendChild(document.createTextNode(m[3])); }
    else after.textContent = txt;
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
  function reveal(el) {
    el.classList.add("in");
    $$("[data-count]", el).forEach(countUp);
  }
  var targets = $$(".reveal");
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.12 });
    targets.forEach(function (t) { io.observe(t); });
  } else { targets.forEach(reveal); }

  /* ---------- calculator ---------- */
  var cf = F.calc, g = F.collision;
  var iS = $("#i-sess"), iC = $("#i-cost"), iP = $("#i-share");
  if (iS && cf && g) {
    iS.value = cf.default_sessions; iC.value = cf.default_cost; iP.value = cf.default_share_pct;
    var money = function (n) { return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); };
    var upd = function () {
      var s = +iS.value, c = +iC.value, sh = +iP.value / 100;
      [iS, iC, iP].forEach(function (i) { i.style.setProperty("--p", ((i.value - i.min) / (i.max - i.min) * 100) + "%"); });
      $("#o-sess").textContent = s; $("#o-cost").textContent = "$" + c.toFixed(2); $("#o-share").textContent = iP.value + "%";
      var month = s * cf.weeks_per_month;
      $("#r-points").textContent = "+" + (sh * g.gap_points).toFixed(1) + " points";
      $("#r-reruns").textContent = (month * sh * g.gap_points / 100).toFixed(1);
      $("#r-money").textContent = money(month * sh * c * g.cost_clean_drop_pct / 100);
    };
    [iS, iC, iP].forEach(function (i) { i.addEventListener("input", upd); });
    upd();
  }

  /* ---------- theme ---------- */
  var tb = $("#theme");
  if (tb) tb.addEventListener("click", function () {
    var r = document.documentElement, n = r.getAttribute("data-theme") === "dark" ? "light" : "dark";
    r.setAttribute("data-theme", n);
    try { localStorage.setItem("theme", n); } catch (e) {}
  });
})();
