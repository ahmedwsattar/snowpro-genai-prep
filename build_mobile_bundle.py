#!/usr/bin/env python3
"""Build a single, self-contained, mobile-first, JAVASCRIPT-FREE HTML bundle of the
whole SnowPro Gen AI prep site. Designed to work in the iOS Files preview (Quick
Look), which does not run JavaScript: navigation uses plain anchor links and every
question reveals its answer with a native <details> element (no JS, no libraries,
no network, no cross-file links).

Sources (single source of truth):
  - Study notes markdown (00-06), rendered with python-markdown (QUIZ sections stripped).
  - The three QUESTIONS arrays parsed from quiz.html / exam-hard.html / exam-targeted.html.

Requires: python-markdown.  Run: python3 build_mobile_bundle.py
"""
import os
import re
import json
import html as _html
import markdown

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "snowpro-genai-prep-mobile.html")

GUIDE_FILES = [
    ("00-START-HERE.md",        "g-start",   "Start Here"),
    ("01-domain1-overview.md",  "g-domain1", "Domain 1 \u00b7 Overview (18%)"),
    ("02-domain2-functions.md", "g-domain2", "Domain 2 \u00b7 Functions (38%)"),
    ("03-domain3-governance.md","g-domain3", "Domain 3 \u00b7 Governance (29%)"),
    ("04-domain4-documents.md", "g-domain4", "Domain 4 \u00b7 Documents (15%)"),
    ("06-advanced-topics.md",   "g-advanced","Advanced \u00b7 Exam-Edge Gotchas"),
    ("05-link-index.md",        "g-links",   "Link Index"),
]
_QUIZ_RE = re.compile(r"\n#+\s*QUIZ\b", re.IGNORECASE)
_md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "attr_list"])

DOMAIN_NAMES = {1: "Domain 1 \u00b7 Overview", 2: "Domain 2 \u00b7 Functions",
                3: "Domain 3 \u00b7 Governance", 4: "Domain 4 \u00b7 Documents"}
TOPIC_NAMES = {
    "1.1": "1.1 Principles & features", "1.2": "1.2 Gen AI capabilities",
    "2.1": "2.1 Apply AI functions", "2.2": "2.2 Data analysis use case",
    "2.3": "2.3 Chat interfaces", "2.5": "2.5 Run third-party models",
    "3.1": "3.1 Model access controls", "3.2": "3.2 RBAC grant/revoke",
    "3.3": "3.3 Cost mgmt & optimize", "3.4": "3.4 Observability & hallucination",
    "4.2": "4.2 Doc prep & extraction", "4.4": "4.4 Doc troubleshoot/optimize",
}
LETTERS = ["A", "B", "C", "D", "E"]


def render_guide():
    parts, toc = [], []
    for fp, sid, nav in GUIDE_FILES:
        with open(os.path.join(DIR, fp), encoding="utf-8") as f:
            text = f.read()
        m = _QUIZ_RE.search(text)
        if m:
            text = text[: m.start()].rstrip() + "\n"
        _md.reset()
        parts.append('<section id="%s" class="gsec">\n%s\n</section>' % (sid, _md.convert(text)))
        toc.append('<a href="#%s">%s</a>' % (sid, nav))
    return "\n".join(parts), "\n".join(toc)


def parse_bank(filename):
    s = open(os.path.join(DIR, filename), encoding="utf-8").read()
    arr = re.search(r"const QUESTIONS = (\[.*?\n    \]);", s, re.S).group(1)
    t = re.sub(r"//[^\n]*", "", arr)
    t = re.sub(r'(\{|,)\s*(topic|domain|q|opts|answer|why)\s*:',
               lambda m: '%s "%s":' % (m.group(1), m.group(2)), t)
    t = re.sub(r",(\s*[\]}])", r"\1", t)
    return json.loads(t)


def render_quiz(bank, key, names, anchor):
    """Static, JS-free rendering: grouped by key, each question with a <details> answer."""
    # group in names order
    groups = {}
    for item in bank:
        groups.setdefault(str(item[key]), []).append(item)
    order = [k for k in names if k in groups] + [k for k in groups if k not in names]

    out = []
    n = 0
    # in-section jump menu
    jump = " &middot; ".join(
        '<a href="#%s-%s">%s</a>' % (anchor, k.replace(".", "_"),
                                     (k if key == "topic" else names[int(k)] if False else names.get(k, k)))
        for k in order)
    # names keyed differently for domain (int) vs topic (str)
    def gname(k):
        return names[int(k)] if key == "domain" else names.get(k, k)
    jump = " &middot; ".join('<a href="#%s-%s">%s</a>' % (anchor, k.replace(".", "_"), gname(k)) for k in order)
    out.append('<p class="jump">Jump: ' + jump + '</p>')

    for k in order:
        gid = "%s-%s" % (anchor, k.replace(".", "_"))
        out.append('<h3 id="%s" class="grp">%s <span class="cnt">(%d)</span></h3>' % (gid, gname(k), len(groups[k])))
        for item in groups[k]:
            n += 1
            correct = LETTERS[item["answer"]]
            opts_html = "".join("<li>%s</li>" % o for o in item["opts"])
            out.append(
                '<div class="q">'
                '<p class="q-text">%d. %s</p>'
                '<ol class="opts" type="A">%s</ol>'
                '<details><summary>Show answer</summary>'
                '<p class="ans"><strong>Answer: %s.</strong> %s</p>'
                '</details></div>' % (n, item["q"], opts_html, correct, item["why"])
            )
        out.append('<p class="totop"><a href="#%s">&uarr; Back to top of %s</a></p>' %
                   (anchor, "this section"))
    return "\n".join(out)


GUIDE_HTML, GUIDE_TOC = render_guide()
Q_QUIZ = render_quiz(parse_bank("quiz.html"), "domain", DOMAIN_NAMES, "quiz")
Q_HARD = render_quiz(parse_bank("exam-hard.html"), "domain", DOMAIN_NAMES, "hard")
Q_DRILL = render_quiz(parse_bank("exam-targeted.html"), "topic", TOPIC_NAMES, "drill")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="snowflake-source" content="cortex-agent-authored" />
  <meta name="theme-color" content="#0b1120" />
  <title>SnowPro Gen AI (GES-C02) — Prep (mobile, offline)</title>
  <script type="application/json" id="snowflake-report-metadata">
  {
    "generated": "2026-08-13",
    "intent": "Single-file, mobile-first, JavaScript-free study bundle for SnowPro Gen AI (GES-C02): study guide + all questions with reveal-answer details. Works in the iOS Files preview (no JS).",
    "sections": [ { "id": "bundle", "title": "Offline mobile bundle",
      "producerNotes": "Built by build_mobile_bundle.py from the study markdown (00-06) and the QUESTIONS arrays in quiz.html/exam-hard.html/exam-targeted.html. No JavaScript. Rebuild: python3 build_mobile_bundle.py." } ]
  }
  </script>
  <style>
    :root { color-scheme: light dark; --accent: light-dark(#2563eb,#60a5fa); }
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
    html { scroll-behavior: smooth; }
    body { margin: 0; font-size: 16px; line-height: 1.55;
      font-family: -apple-system, system-ui, Segoe UI, Roboto, sans-serif;
      color: light-dark(#1f2937,#e5e7eb); background: light-dark(#ffffff,#0b1120);
      -webkit-text-size-adjust: 100%; }
    a { color: var(--accent); }

    nav.top { position: sticky; top: 0; z-index: 20;
      display: flex; gap: 6px; overflow-x: auto; -webkit-overflow-scrolling: touch;
      padding: 10px 10px; background: light-dark(#ffffffee,#0b1120ee); backdrop-filter: blur(8px);
      border-bottom: 1px solid light-dark(#e2e8f0,#1e293b); }
    nav.top a { flex: 0 0 auto; text-decoration: none; font-size: 0.9rem; font-weight: 600;
      padding: 9px 14px; min-height: 40px; border-radius: 999px; white-space: nowrap;
      border: 1px solid light-dark(#cbd5e1,#334155);
      background: light-dark(#f8fafc,#1e293b); color: light-dark(#334155,#cbd5e1); }

    main { max-width: 820px; margin: 0 auto; padding: 8px 14px 96px; }
    section.tabsec { scroll-margin-top: 62px; padding-top: 10px; }
    section.tabsec + section.tabsec { margin-top: 30px; border-top: 2px solid light-dark(#e2e8f0,#1e293b); }

    h1 { font-size: 1.4rem; color: light-dark(#0f172a,#f1f5f9); margin: 14px 0 4px; }
    h2 { font-size: 1.2rem; color: light-dark(#0f172a,#f1f5f9); margin: 24px 0 8px; padding-bottom: 4px;
      border-bottom: 1px solid light-dark(#eef2f7,#1a2740); }
    h3 { font-size: 1.05rem; margin: 20px 0 8px; }
    h3.grp { color: light-dark(#0f172a,#f1f5f9); scroll-margin-top: 62px; }
    h3.grp .cnt { color: light-dark(#94a3b8,#64748b); font-weight: 400; font-size: 0.85rem; }
    .sub { color: light-dark(#64748b,#94a3b8); margin: 0 0 12px; font-size: 0.95rem; }
    .note { padding: 10px 14px; border-radius: 10px; font-size: 0.9rem; margin: 10px 0 4px;
      background: light-dark(#eff6ff,#10203a); border: 1px solid light-dark(#bfdbfe,#1e3a5f); }

    code { font-family: ui-monospace,SFMono-Regular,Menlo,monospace; font-size: 0.85em;
      background: light-dark(#f1f5f9,#1e293b); padding: 1px 5px; border-radius: 4px; overflow-wrap: anywhere; }
    pre { background: light-dark(#f8fafc,#0f172a); border: 1px solid light-dark(#e2e8f0,#253247);
      border-radius: 10px; padding: 12px 14px; overflow-x: auto; }
    pre code { background: none; padding: 0; }
    table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 0.88rem; display: block; overflow-x: auto; }
    th, td { border: 1px solid light-dark(#d1d5db,#374151); padding: 7px 9px; text-align: left; vertical-align: top; }
    th { background: light-dark(#f3f4f6,#1f2937); font-weight: 600; }
    blockquote { margin: 12px 0; padding: 8px 14px; border-left: 3px solid light-dark(#f59e0b,#fbbf24);
      background: light-dark(#fffbeb,#201a09); border-radius: 0 8px 8px 0; }
    hr { border: none; border-top: 1px solid light-dark(#e2e8f0,#1e293b); margin: 20px 0; }

    .cards { display: grid; grid-template-columns: 1fr; gap: 12px; margin-top: 14px; }
    .card { display: block; text-decoration: none; color: inherit;
      border: 1px solid light-dark(#e2e8f0,#1e293b); border-radius: 14px; padding: 16px;
      background: light-dark(#ffffff,#0f172a); }
    .card .ic { font-size: 1.5rem; }
    .card h3 { margin: 6px 0 4px; color: light-dark(#0f172a,#f1f5f9); }
    .card p { margin: 0; font-size: 0.9rem; color: light-dark(#475569,#cbd5e1); }

    details.toc { margin: 8px 0 16px; border: 1px solid light-dark(#e2e8f0,#1e293b); border-radius: 10px;
      padding: 4px 12px; background: light-dark(#f8fafc,#0f172a); }
    details.toc > summary { cursor: pointer; font-weight: 600; padding: 10px 0; min-height: 40px; }
    details.toc a { display: block; padding: 10px 4px; text-decoration: none; border-top: 1px solid light-dark(#eef2f7,#1a2740); }
    .gsec { scroll-margin-top: 62px; }
    .gsec + .gsec { border-top: 1px solid light-dark(#e2e8f0,#1e293b); margin-top: 22px; padding-top: 6px; }

    .jump { font-size: 0.85rem; color: light-dark(#475569,#cbd5e1); margin: 4px 0 14px; }
    .jump a { margin-right: 2px; }
    .q { border: 1px solid light-dark(#e2e8f0,#1e293b); border-radius: 12px; padding: 14px 14px 6px; margin: 0 0 14px;
      background: light-dark(#ffffff,#0f172a); }
    .q-text { font-weight: 600; color: light-dark(#0f172a,#f1f5f9); margin: 0 0 8px; }
    ol.opts { margin: 0 0 8px; padding-left: 1.5em; }
    ol.opts li { padding: 4px 0; }
    details.q > summary, .q details > summary { cursor: pointer; font-weight: 600; color: var(--accent);
      padding: 10px 0; min-height: 40px; list-style: none; }
    .q details > summary::-webkit-details-marker { display: none; }
    .q details > summary::before { content: "\25B8  "; }
    .q details[open] > summary::before { content: "\25BE  "; }
    .ans { margin: 4px 0 10px; padding: 12px; font-size: 0.92rem; border-radius: 0 8px 8px 0;
      border-left: 3px solid light-dark(#22c55e,#16a34a); background: light-dark(#f0fdf4,#052e1a); }
    .totop { text-align: right; font-size: 0.82rem; margin: 2px 0 22px; }
    .grp + .totop { display: none; }

    footer { max-width: 820px; margin: 0 auto; padding: 8px 14px 40px; color: light-dark(#64748b,#94a3b8); font-size: 0.82rem; }
  </style>
</head>
<body>
  <nav class="top">
    <a href="#home">Home</a>
    <a href="#study">Study Guide</a>
    <a href="#quiz">Quiz</a>
    <a href="#hard">Hard Mock</a>
    <a href="#drill">Drill</a>
  </nav>

  <main>
    <section class="tabsec" id="home">
      <h1>SnowPro Gen AI (GES-C02)</h1>
      <p class="sub">Offline study bundle. Tap a section above, or a card below. Under each question, tap <strong>Show answer</strong>.</p>
      <div class="note">This version needs no internet and no app &mdash; it works right in the Files preview. Tap <strong>Show answer</strong> to reveal the correct choice and explanation for any question.</div>
      <div class="cards">
        <a class="card" href="#study"><div class="ic">&#128218;</div><h3>Study Guide</h3><p>All domains + advanced gotchas, with a jump menu.</p></a>
        <a class="card" href="#quiz"><div class="ic">&#9989;</div><h3>Practice Quiz</h3><p>Scenario questions grouped by domain; reveal answers.</p></a>
        <a class="card" href="#hard"><div class="ic">&#128293;</div><h3>Hard Mock</h3><p>Tougher, nuance-driven questions.</p></a>
        <a class="card" href="#drill"><div class="ic">&#127919;</div><h3>Targeted Drill</h3><p>Grouped by exam subtopic (1.1&ndash;4.4).</p></a>
      </div>
      <table>
        <thead><tr><th>Domain</th><th>Weight</th></tr></thead>
        <tbody>
          <tr><td>1.0 Overview</td><td>18%</td></tr>
          <tr><td>2.0 Functions</td><td>38%</td></tr>
          <tr><td>3.0 Governance</td><td>29%</td></tr>
          <tr><td>4.0 Document Processing</td><td>15%</td></tr>
        </tbody>
      </table>
    </section>

    <section class="tabsec" id="study">
      <h1>Study Guide</h1>
      <details class="toc"><summary>Jump to section</summary>__GUIDE_TOC__</details>
      __GUIDE_HTML__
      <p class="totop"><a href="#home">&uarr; Back to top</a></p>
    </section>

    <section class="tabsec" id="quiz">
      <h1>Practice Quiz</h1>
      <p class="sub">34 questions grouped by domain. Tap <strong>Show answer</strong> under each.</p>
      __Q_QUIZ__
      <p class="totop"><a href="#home">&uarr; Back to top</a></p>
    </section>

    <section class="tabsec" id="hard">
      <h1>Hard Mock Exam</h1>
      <p class="sub">34 tougher, nuance-driven questions.</p>
      __Q_HARD__
      <p class="totop"><a href="#home">&uarr; Back to top</a></p>
    </section>

    <section class="tabsec" id="drill">
      <h1>Targeted Drill</h1>
      <p class="sub">44 questions grouped by exam subtopic.</p>
      __Q_DRILL__
      <p class="totop"><a href="#home">&uarr; Back to top</a></p>
    </section>
  </main>

  <footer>Self-contained offline study bundle &middot; no JavaScript &middot; SnowPro Specialty: Gen AI (GES-C02).</footer>
</body>
</html>
"""

html = (TEMPLATE
        .replace("__GUIDE_TOC__", GUIDE_TOC)
        .replace("__GUIDE_HTML__", GUIDE_HTML)
        .replace("__Q_QUIZ__", Q_QUIZ)
        .replace("__Q_HARD__", Q_HARD)
        .replace("__Q_DRILL__", Q_DRILL))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print("Wrote %s (%d bytes)" % (OUT, len(html)))
