#!/usr/bin/env python3
"""Build study-guide.html from the SnowPro Gen AI markdown notes.

Reads the domain study-note markdown files, strips the QUIZ/ANSWER KEY sections
(those live in quiz.html), pre-renders each to HTML with python-markdown, and
bakes them into a single self-contained study-guide.html. No runtime library or
network is needed, so it opens directly in any browser (file://).

Requires: python-markdown  (pip install markdown)
Run: python3 build_study_guide.py
"""
import os
import re
import markdown

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "study-guide.html")

FILES = [
    ("00-START-HERE.md",                  "start",   "Start Here"),
    ("01-domain1-overview.md",            "domain1", "Domain 1 \u00b7 Overview (18%)"),
    ("SnowPro_GenAI_Domain1_DeepDive.md", "domain1-dd", "Domain 1 \u00b7 Deep-Dive"),
    ("02-domain2-functions.md",           "domain2", "Domain 2 \u00b7 Functions (38%)"),
    ("SnowPro_GenAI_Domain2_DeepDive.md", "domain2-dd", "Domain 2 \u00b7 Deep-Dive"),
    ("03-domain3-governance.md",          "domain3", "Domain 3 \u00b7 Governance (29%)"),
    ("SnowPro_GenAI_Domain3_DeepDive.md", "domain3-dd", "Domain 3 \u00b7 Deep-Dive"),
    ("04-domain4-documents.md",           "domain4", "Domain 4 \u00b7 Documents (15%)"),
    ("SnowPro_GenAI_Domain4_DeepDive.md", "domain4-dd", "Domain 4 \u00b7 Deep-Dive"),
    ("06-advanced-topics.md",             "advanced","Advanced \u00b7 Exam-Edge Gotchas"),
    ("05-link-index.md",                  "links",   "Link Index"),
]

_QUIZ_RE = re.compile(r"\n#+\s*QUIZ\b", re.IGNORECASE)

md_renderer = markdown.Markdown(
    extensions=["tables", "fenced_code", "sane_lists", "attr_list"]
)


def render(fp):
    with open(os.path.join(DIR, fp), encoding="utf-8") as f:
        text = f.read()
    m = _QUIZ_RE.search(text)
    if m:
        text = text[: m.start()].rstrip() + "\n"
    md_renderer.reset()
    return md_renderer.convert(text)


sections_html = []
for fp, sid, nav in FILES:
    body = render(fp)
    sections_html.append(
        '<section id="%s" data-nav="%s">\n%s\n</section>' % (sid, nav, body)
    )

CONTENT = "\n".join(sections_html)

# Open external doc links in a new tab so tapping one on mobile doesn't
# navigate away from the guide. Internal (#anchor) links are untouched.
CONTENT = re.sub(
    r'<a href="(https?://[^"]+)"',
    r'<a href="\1" target="_blank" rel="noopener noreferrer"',
    CONTENT,
)

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="snowflake-source" content="cortex-agent-authored" />
  <title>SnowPro Gen AI (GES-C02) — Study Guide</title>
  <script type="application/json" id="snowflake-report-metadata">
  {
    "generated": "2026-08-10",
    "intent": "Readable, self-contained HTML study guide for the SnowPro Specialty: Gen AI (GES-C02) certification, covering all four exam domains. Markdown is pre-rendered at build time so it opens directly in any browser.",
    "sections": [
      { "id": "study-guide", "title": "Study guide",
        "dataSources": [{ "type": "file", "path": "SnowPro-GenAI-Prep/00-START-HERE.md, 01-domain1-overview.md, 02-domain2-functions.md, 03-domain3-governance.md, 04-domain4-documents.md, 05-link-index.md" }],
        "producerNotes": "Pre-rendered from the markdown files via build_study_guide.py (python-markdown). QUIZ/ANSWER KEY sections are stripped (they live in quiz.html). To refresh: edit the .md files and re-run 'python3 build_study_guide.py'." }
    ]
  }
  </script>
  <style>
    :root { color-scheme: light dark; }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      font-family: -apple-system, system-ui, Segoe UI, Roboto, sans-serif;
      color: light-dark(#1f2937, #e5e7eb);
      background: light-dark(#ffffff, #0b1120);
      line-height: 1.6;
    }
    .layout { display: flex; align-items: flex-start; max-width: 1200px; margin: 0 auto; }

    /* Sidebar */
    .sidebar {
      position: sticky; top: 0; align-self: flex-start;
      width: 300px; flex: 0 0 300px; height: 100vh; overflow-y: auto;
      padding: 20px 16px; border-right: 1px solid light-dark(#e2e8f0, #1e293b);
    }
    .sidebar h2 { font-size: 0.95rem; margin: 0 0 4px; color: light-dark(#0f172a, #f1f5f9); }
    .sidebar .tagline { font-size: 0.78rem; color: light-dark(#64748b, #94a3b8); margin: 0 0 14px; }
    .quiz-btn {
      display: block; text-align: center; text-decoration: none;
      font-weight: 600; font-size: 0.9rem;
      padding: 10px 12px; margin: 0 0 16px; border-radius: 9px;
      background: light-dark(#2563eb, #3b82f6); color: #fff;
    }
    .quiz-btn:hover { background: light-dark(#1d4ed8, #2563eb); }
    nav.toc { font-size: 0.86rem; }
    nav.toc a {
      display: block; text-decoration: none; border-radius: 6px;
      padding: 4px 8px; margin: 1px 0;
      color: light-dark(#475569, #cbd5e1);
      border-left: 2px solid transparent;
    }
    nav.toc a:hover { background: light-dark(#f1f5f9, #111c30); }
    nav.toc a.lvl1 { font-weight: 700; margin-top: 10px; color: light-dark(#0f172a, #f8fafc); }
    nav.toc a.lvl2 { padding-left: 18px; }
    nav.toc a.active {
      color: light-dark(#1d4ed8, #93c5fd);
      border-left-color: light-dark(#2563eb, #60a5fa);
      background: light-dark(#eff6ff, #10203a);
    }

    /* Content */
    .content { flex: 1 1 auto; min-width: 0; padding: 24px 36px 120px; max-width: 860px; }
    .content section { scroll-margin-top: 16px; padding-bottom: 8px; }
    .content section + section { border-top: 1px solid light-dark(#e2e8f0, #1e293b); margin-top: 28px; padding-top: 8px; }

    h1 { font-size: 1.7rem; color: light-dark(#0f172a, #f1f5f9); margin: 18px 0 6px; }
    h2 { font-size: 1.3rem; color: light-dark(#0f172a, #f1f5f9); margin: 30px 0 8px; padding-bottom: 4px; border-bottom: 1px solid light-dark(#eef2f7, #1a2740); }
    h3 { font-size: 1.08rem; color: light-dark(#111827, #f1f5f9); margin: 22px 0 6px; }
    a { color: light-dark(#2563eb, #60a5fa); }
    p, li { font-size: 0.96rem; }

    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.86em;
      background: light-dark(#f1f5f9, #1e293b); padding: 1px 5px; border-radius: 4px;
    }
    pre {
      background: light-dark(#f8fafc, #0f172a);
      border: 1px solid light-dark(#e2e8f0, #253247);
      border-radius: 10px; padding: 14px 16px; overflow-x: auto;
    }
    pre code { background: none; padding: 0; font-size: 0.85rem; }

    table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 0.9rem; display: block; overflow-x: auto; }
    th, td { border: 1px solid light-dark(#d1d5db, #374151); padding: 7px 10px; text-align: left; vertical-align: top; }
    th { background: light-dark(#f3f4f6, #1f2937); font-weight: 600; color: light-dark(#0f172a, #f8fafc); }
    tr:nth-child(even) td { background: light-dark(#fafbfc, #0d1526); }

    blockquote {
      margin: 14px 0; padding: 10px 16px;
      border-left: 3px solid light-dark(#f59e0b, #fbbf24);
      background: light-dark(#fffbeb, #201a09); border-radius: 0 8px 8px 0;
    }
    blockquote p { margin: 6px 0; }
    hr { border: none; border-top: 1px solid light-dark(#e2e8f0, #1e293b); margin: 22px 0; }
    strong { color: light-dark(#0f172a, #f8fafc); }

    /* Mobile */
    @media (max-width: 820px) {
      .layout { flex-direction: column; }
      .sidebar { position: static; width: 100%; flex-basis: auto; height: auto; border-right: none; border-bottom: 1px solid light-dark(#e2e8f0, #1e293b); }
      .content { padding: 20px; }
    }
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h2>SnowPro Gen AI (GES-C02)</h2>
      <p class="tagline">Study guide · read all four domains, then test yourself.</p>
      <a class="quiz-btn" href="quiz.html">Take the practice quiz &rarr;</a>
      <nav class="toc" id="toc"></nav>
    </aside>
    <main class="content" id="content">
__CONTENT__
    </main>
  </div>

  <script>
    const contentEl = document.getElementById('content');
    const tocEl = document.getElementById('toc');

    function slug(s) {
      return s.toLowerCase().replace(/[^\w\s-]/g, '').trim().replace(/\s+/g, '-').slice(0, 60);
    }

    const tocLinks = [];
    const usedIds = {};

    contentEl.querySelectorAll('section').forEach(secEl => {
      const l1 = document.createElement('a');
      l1.className = 'lvl1';
      l1.href = '#' + secEl.id;
      l1.textContent = secEl.dataset.nav || secEl.id;
      tocEl.appendChild(l1);
      tocLinks.push({ a: l1, targetId: secEl.id });

      secEl.querySelectorAll('h2').forEach(h => {
        let id = slug(h.textContent) || secEl.id;
        if (usedIds[id]) { usedIds[id]++; id = id + '-' + usedIds[id]; } else { usedIds[id] = 1; }
        h.id = id;
        h.style.scrollMarginTop = '16px';
        const l2 = document.createElement('a');
        l2.className = 'lvl2';
        l2.href = '#' + id;
        l2.textContent = h.textContent;
        tocEl.appendChild(l2);
        tocLinks.push({ a: l2, targetId: id });
      });
    });

    const byId = {};
    tocLinks.forEach(t => byId[t.targetId] = t.a);
    const targets = tocLinks.map(t => document.getElementById(t.targetId)).filter(Boolean);
    let activeId = null;
    function setActive(id) {
      if (id === activeId) return;
      if (activeId && byId[activeId]) byId[activeId].classList.remove('active');
      activeId = id;
      if (byId[id]) {
        byId[id].classList.add('active');
        byId[id].scrollIntoView({ block: 'nearest' });
      }
    }
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter(e => e.isIntersecting)
        .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (visible.length) setActive(visible[0].target.id);
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0 });
    targets.forEach(t => observer.observe(t));
  </script>
</body>
</html>
"""

html = TEMPLATE.replace("__CONTENT__", CONTENT)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print("Wrote %s (%d bytes, %d sections)" % (OUT, len(html), len(sections_html)))
