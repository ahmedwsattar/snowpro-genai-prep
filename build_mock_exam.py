#!/usr/bin/env python3
"""Build mock-exam.html — a full, timed, exam-style mock for SnowPro Gen AI (GES-C02).

Pools all questions from quiz.html / exam-hard.html / exam-targeted.html into one
bank (tagged by domain), embeds it, and the page samples a domain-weighted set of
65 questions per attempt, shuffles questions AND options, runs an 85-minute
countdown, and produces a scored report with a per-domain breakdown and full review.

Interactive (JavaScript) — intended for a browser (local or the hosted Netlify link).
Requires nothing beyond Python 3.  Run: python3 build_mock_exam.py
"""
import os
import re
import json

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "mock-exam.html")


def parse_bank(filename):
    s = open(os.path.join(DIR, filename), encoding="utf-8").read()
    arr = re.search(r"const QUESTIONS = (\[.*?\n    \]);", s, re.S).group(1)
    t = re.sub(r"//[^\n]*", "", arr)
    t = re.sub(r'(\{|,)\s*(topic|domain|q|opts|answers|answer|why)\s*:',
               lambda m: '%s "%s":' % (m.group(1), m.group(2)), t)
    t = re.sub(r",(\s*[\]}])", r"\1", t)
    return json.loads(t)


pool = []
for fn in ["quiz.html", "exam-hard.html", "exam-targeted.html"]:
    for it in parse_bank(fn):
        dom = it["domain"] if "domain" in it else int(str(it["topic"]).split(".")[0])
        entry = {"d": dom, "q": it["q"], "opts": it["opts"], "why": it["why"]}
        if "answers" in it:
            entry["ma"] = it["answers"]          # multi-answer: list of correct indices
        else:
            entry["a"] = it["answer"]            # single-answer: one correct index
        pool.append(entry)

POOL_JSON = json.dumps(pool, ensure_ascii=False).replace("</", "<\\/")

from collections import Counter
dist = Counter(p["d"] for p in pool)
print("Pool: %d questions, per-domain %s" % (len(pool), dict(sorted(dist.items()))))

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <meta name="snowflake-source" content="cortex-agent-authored" />
  <title>SnowPro Gen AI (GES-C02) — Timed Mock Exam</title>
  <script type="application/json" id="snowflake-report-metadata">
  {
    "generated": "2026-08-13",
    "intent": "Full, timed, exam-style mock for SnowPro Gen AI (GES-C02): 65 domain-weighted questions, 85-minute countdown, shuffled questions/options, scored report with per-domain breakdown and review.",
    "sections": [ { "id": "mock", "title": "Timed mock exam",
      "producerNotes": "Built by build_mock_exam.py from the pooled QUESTIONS arrays in quiz.html/exam-hard.html/exam-targeted.html (112 total, tagged by domain). Rebuild: python3 build_mock_exam.py." } ]
  }
  </script>
  <style>
    :root { color-scheme: light dark; --accent: light-dark(#7c3aed,#8b5cf6); }
    * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
    body { margin: 0; font-size: 16px; line-height: 1.5;
      font-family: -apple-system, system-ui, Segoe UI, Roboto, sans-serif;
      color: light-dark(#1f2937,#e5e7eb); background: light-dark(#ffffff,#0b1120); }
    a { color: light-dark(#2563eb,#60a5fa); }
    main { max-width: 860px; margin: 0 auto; padding: 20px 16px 100px; }
    h1 { font-size: 1.5rem; color: light-dark(#0f172a,#f1f5f9); margin: 6px 0; }
    h2 { font-size: 1.2rem; color: light-dark(#0f172a,#f1f5f9); }
    .sub { color: light-dark(#64748b,#94a3b8); }
    code { font-family: ui-monospace,SFMono-Regular,Menlo,monospace; font-size: 0.85em;
      background: light-dark(#f1f5f9,#1e293b); padding: 1px 5px; border-radius: 4px; overflow-wrap: anywhere; }
    .btn { font: inherit; font-weight: 700; cursor: pointer; border: none; border-radius: 10px;
      padding: 12px 20px; min-height: 46px; background: var(--accent); color: #fff; }
    .btn.secondary { background: light-dark(#e2e8f0,#1e293b); color: light-dark(#0f172a,#e5e7eb); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .card { border: 1px solid light-dark(#e2e8f0,#1e293b); border-radius: 14px; padding: 20px;
      background: light-dark(#ffffff,#0f172a); margin: 16px 0; }
    ul.facts { margin: 8px 0 0; padding-left: 1.2em; } ul.facts li { margin: 4px 0; }

    /* Exam bar */
    .bar { position: sticky; top: 0; z-index: 20; display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
      padding: 12px 16px; margin: 0 -16px 14px; background: light-dark(#ffffffee,#0b1120ee); backdrop-filter: blur(8px);
      border-bottom: 1px solid light-dark(#e2e8f0,#1e293b); }
    .timer { font-variant-numeric: tabular-nums; font-weight: 800; font-size: 1.25rem; color: light-dark(#0f172a,#f1f5f9); }
    .timer.warn { color: light-dark(#b91c1c,#f87171); }
    .prog { font-size: 0.9rem; color: light-dark(#475569,#cbd5e1); }
    .bar .spacer { flex: 1 1 auto; }

    .q { border: 1px solid light-dark(#e2e8f0,#1e293b); border-radius: 12px; padding: 16px; margin: 0 0 14px;
      background: light-dark(#ffffff,#0f172a); scroll-margin-top: 76px; }
    .q-num { font-size: 0.75rem; font-weight: 700; color: light-dark(#7c3aed,#c4b5fd); text-transform: uppercase; }
    .q-text { font-weight: 600; color: light-dark(#0f172a,#f1f5f9); margin: 4px 0 10px; }
    .opts { list-style: none; padding: 0; margin: 0; }
    .opt { display: flex; gap: 10px; align-items: flex-start; padding: 12px; margin: 8px 0; min-height: 46px;
      border: 1px solid light-dark(#e2e8f0,#253247); border-radius: 10px; cursor: pointer; }
    .opt:hover { border-color: var(--accent); }
    .opt input { margin-top: 3px; accent-color: var(--accent); }
    .opt .letter { font-weight: 700; color: light-dark(#64748b,#94a3b8); }
    /* review state */
    .opt.correct { background: light-dark(#dcfce7,#052e1a); border-color: light-dark(#22c55e,#16a34a); }
    .opt.wrong { background: light-dark(#fee2e2,#3b0d0d); border-color: light-dark(#ef4444,#dc2626); }
    .explain { margin-top: 8px; padding: 12px; font-size: 0.92rem; border-radius: 0 8px 8px 0;
      border-left: 3px solid var(--accent); background: light-dark(#f8fafc,#111c30); }
    .verdict.right { color: light-dark(#15803d,#4ade80); font-weight: 700; }
    .verdict.no { color: light-dark(#b91c1c,#f87171); font-weight: 700; }
    .flag { margin-left: auto; font-size: 0.8rem; }

    /* Report */
    .scorehero { text-align: center; padding: 22px; }
    .scorehero .pct { font-size: 3rem; font-weight: 800; line-height: 1; }
    .pill { display: inline-block; padding: 4px 14px; border-radius: 999px; font-weight: 700; margin-top: 8px; }
    .pill.pass { background: light-dark(#dcfce7,#052e1a); color: light-dark(#15803d,#4ade80); }
    .pill.fail { background: light-dark(#fee2e2,#3b0d0d); color: light-dark(#b91c1c,#f87171); }
    table { border-collapse: collapse; width: 100%; margin: 14px 0; font-size: 0.92rem; }
    th, td { border: 1px solid light-dark(#d1d5db,#374151); padding: 8px 10px; text-align: left; }
    th { background: light-dark(#f3f4f6,#1f2937); font-weight: 600; }
    .hide { display: none; }
    footer { max-width: 860px; margin: 0 auto; padding: 8px 16px 40px; color: light-dark(#64748b,#94a3b8); font-size: 0.82rem; }
  </style>
</head>
<body>
  <main>
    <!-- START -->
    <div id="start">
      <h1>SnowPro Gen AI (GES-C02) — Timed Mock Exam</h1>
      <p class="sub">A full, exam-style run to simulate the real thing.</p>
      <div class="card">
        <h2 style="margin-top:0">Format</h2>
        <ul class="facts">
          <li><strong>65 questions</strong>, domain-weighted (D1 18% / D2 38% / D3 29% / D4 15%).</li>
          <li><strong>85-minute</strong> countdown; the exam auto-submits at 0:00.</li>
          <li>Questions and answer options are <strong>shuffled</strong>; each attempt is a fresh draw.</li>
          <li><strong>No feedback until you submit</strong> — then you get a score, per-domain breakdown, and full review with explanations.</li>
          <li>Estimated pass line: <strong>75%</strong> (approximation of Snowflake's scaled 750/1000).</li>
        </ul>
        <p style="margin-bottom:0"><button class="btn" id="startBtn">Start exam</button></p>
        <p id="resumeWrap" class="hide" style="margin:10px 0 0"><button class="btn secondary" id="resumeBtn"></button></p>
      </div>
      <p class="sub">Tip: sit it in one uninterrupted block, no notes, like the real exam.</p>
      <footer>Pooled from the practice quiz + hard mock + targeted drill. Back to <a href="index.html">prep hub</a>.</footer>
    </div>

    <!-- EXAM -->
    <div id="exam" class="hide">
      <div class="bar">
        <span class="timer" id="timer">85:00</span>
        <span class="prog" id="prog">0 / 65 answered</span>
        <span class="spacer"></span>
        <button class="btn secondary" id="pauseBtn">Pause &amp; save</button>
        <button class="btn" id="submitBtn">Submit</button>
      </div>
      <div id="questions"></div>
      <p><button class="btn" id="submitBtn2">Submit exam</button></p>
    </div>

    <!-- REPORT -->
    <div id="report" class="hide">
      <div class="card scorehero">
        <div class="pct" id="r-pct">--</div>
        <div id="r-pill"></div>
        <p class="sub" id="r-line"></p>
      </div>
      <div class="card">
        <h2 style="margin-top:0">By domain</h2>
        <table><thead><tr><th>Domain</th><th>Correct</th><th>%</th></tr></thead><tbody id="r-domain"></tbody></table>
        <p><button class="btn" id="retakeBtn">Retake (new draw)</button>
           <button class="btn secondary" id="reviewToggle">Show review</button></p>
      </div>
      <div id="review" class="hide"></div>
      <footer>Back to <a href="index.html">prep hub</a> &middot; <a href="study-guide.html">study guide</a>.</footer>
    </div>
  </main>

  <script id="mock-pool" type="application/json">__POOL__</script>
  <script>
    const POOL = JSON.parse(document.getElementById('mock-pool').textContent);
    const LETTERS = ["A","B","C","D","E"];
    const DOMAIN_NAMES = { 1:"D1 Overview", 2:"D2 Functions", 3:"D3 Governance", 4:"D4 Documents" };
    const NUM_Q = 65;
    const WEIGHTS = { 1:12, 2:25, 3:19, 4:9 }; // sums to 65
    const MINUTES = 85;
    const PASS = 75;

    let exam = [];      // selected questions (with shuffled opts + remapped answer)
    let answers = {};   // idx -> chosen display-option index
    let timerId = null;
    let secondsLeft = MINUTES*60;
    const LS_KEY = 'ges_c02_mock_v1';

    function save() {
      try { localStorage.setItem(LS_KEY, JSON.stringify({ exam, answers, secondsLeft, ts: Date.now() })); } catch(e) {}
    }
    function loadSaved() {
      try { const s = localStorage.getItem(LS_KEY); return s ? JSON.parse(s) : null; } catch(e) { return null; }
    }
    function clearSave() { try { localStorage.removeItem(LS_KEY); } catch(e) {} }

    function shuffle(a) { for (let i=a.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; }

    function buildExam() {
      const byDom = {1:[],2:[],3:[],4:[]};
      POOL.forEach(q => byDom[q.d].push(q));
      let picked = [];
      for (const d of [1,2,3,4]) {
        const arr = shuffle(byDom[d].slice());
        picked = picked.concat(arr.slice(0, Math.min(WEIGHTS[d], arr.length)));
      }
      shuffle(picked);
      exam = picked.map(q => {
        const order = shuffle(q.opts.map((_,i)=>i));
        const opts = order.map(i => q.opts[i]);
        if (Array.isArray(q.ma)) {
          const ma = q.ma.map(x => order.indexOf(x)).sort((a,b)=>a-b);
          return { d:q.d, q:q.q, opts, ma, why:q.why };
        }
        const a = order.indexOf(q.a);
        return { d:q.d, q:q.q, opts, a, why:q.why };
      });
      answers = {};
    }

    function renderExam() {
      const box = document.getElementById('questions');
      box.innerHTML = "";
      exam.forEach((item, idx) => {
        const isMulti = Array.isArray(item.ma);
        const card = document.createElement('div'); card.className = 'q'; card.id = 'q'+idx;
        card.innerHTML = '<div class="q-num">Question ' + (idx+1) + ' &middot; ' + DOMAIN_NAMES[item.d] +
                         (isMulti ? ' &middot; select ' + item.ma.length : '') + '</div>' +
                         '<div class="q-text">' + item.q + '</div>';
        const ul = document.createElement('ul'); ul.className = 'opts';
        item.opts.forEach((opt, oi) => {
          const li = document.createElement('li'); li.className = 'opt';
          const input = document.createElement('input');
          input.value = oi;
          if (isMulti) {
            input.type = 'checkbox'; input.name = 'm'+idx+'_'+oi;
            if (Array.isArray(answers[idx]) && answers[idx].includes(oi)) input.checked = true;
          } else {
            input.type = 'radio'; input.name = 'm'+idx;
            if (answers[idx] === oi) input.checked = true;
          }
          const toggle = () => {
            if (isMulti) {
              let arr = Array.isArray(answers[idx]) ? answers[idx].slice() : [];
              const at = arr.indexOf(oi);
              if (at === -1) arr.push(oi); else arr.splice(at, 1);
              arr.sort((a,b)=>a-b);
              if (arr.length) answers[idx] = arr; else delete answers[idx];
              input.checked = arr.includes(oi);
            } else {
              answers[idx] = oi; input.checked = true;
            }
            updateProg(); save();
          };
          input.addEventListener('change', toggle);
          const lt = document.createElement('span'); lt.className='letter'; lt.textContent = LETTERS[oi]+'.';
          const tx = document.createElement('span'); tx.innerHTML = opt;
          li.appendChild(input); li.appendChild(lt); li.appendChild(tx);
          li.addEventListener('click', (e) => { if (e.target !== input) { input.checked = !input.checked; toggle(); } });
          ul.appendChild(li);
        });
        card.appendChild(ul);
        box.appendChild(card);
      });
      updateProg();
    }

    function updateProg() {
      document.getElementById('prog').textContent = Object.keys(answers).length + ' / ' + exam.length + ' answered';
    }

    function fmt(s) { const m = Math.floor(s/60), r = s%60; return m + ':' + (r<10?'0':'') + r; }
    function isCorrect(item, ans) {
      if (Array.isArray(item.ma)) {
        if (!Array.isArray(ans) || ans.length !== item.ma.length) return false;
        const a = ans.slice().sort((x,y)=>x-y);
        return item.ma.every((v,i) => v === a[i]);
      }
      return ans === item.a;
    }
    function correctLetters(item) {
      const cs = Array.isArray(item.ma) ? item.ma : [item.a];
      return cs.map(i => LETTERS[i]).join(', ');
    }
    function tick() {
      secondsLeft = Math.max(0, secondsLeft - 1);
      const t = document.getElementById('timer');
      t.textContent = fmt(secondsLeft);
      t.classList.toggle('warn', secondsLeft <= 300);
      if (secondsLeft % 5 === 0) save();
      if (secondsLeft <= 0) { clearInterval(timerId); submit(true); }
    }
    function runTimer() { clearInterval(timerId); timerId = setInterval(tick, 1000); }

    function beginExamScreen() {
      document.getElementById('start').classList.add('hide');
      document.getElementById('report').classList.add('hide');
      document.getElementById('exam').classList.remove('hide');
      document.getElementById('timer').textContent = fmt(secondsLeft);
      runTimer(); window.scrollTo({top:0});
    }

    function startExam() {
      clearSave(); buildExam(); secondsLeft = MINUTES*60; renderExam(); save(); beginExamScreen();
    }
    function resumeExam(saved) {
      exam = saved.exam; answers = saved.answers || {}; secondsLeft = saved.secondsLeft || MINUTES*60;
      renderExam(); beginExamScreen();
    }
    function pauseExam() {
      clearInterval(timerId); save();
      document.getElementById('exam').classList.add('hide');
      document.getElementById('start').classList.remove('hide');
      maybeShowResume(); window.scrollTo({top:0});
    }
    function maybeShowResume() {
      const saved = loadSaved();
      const wrap = document.getElementById('resumeWrap');
      const btn = document.getElementById('resumeBtn');
      if (saved && saved.exam && saved.exam.length) {
        const ans = Object.keys(saved.answers || {}).length;
        btn.textContent = 'Resume in-progress exam \u2014 ' + ans + '/' + saved.exam.length + ' answered, ' + fmt(saved.secondsLeft || 0) + ' left';
        wrap.classList.remove('hide');
      } else { wrap.classList.add('hide'); }
    }

    function submit(auto) {
      if (!auto) {
        const unanswered = exam.length - Object.keys(answers).length;
        if (unanswered > 0 && !confirm(unanswered + ' question(s) unanswered. Submit anyway?')) return;
      }
      clearInterval(timerId); clearSave();
      let correct = 0;
      const dom = {1:[0,0],2:[0,0],3:[0,0],4:[0,0]};
      exam.forEach((item, idx) => {
        dom[item.d][1]++;
        if (isCorrect(item, answers[idx])) { correct++; dom[item.d][0]++; }
      });
      const pct = Math.round(correct / exam.length * 100);
      document.getElementById('exam').classList.add('hide');
      document.getElementById('report').classList.remove('hide');
      document.getElementById('r-pct').textContent = pct + '%';
      const pass = pct >= PASS;
      const pill = document.getElementById('r-pill');
      pill.className = 'pill ' + (pass ? 'pass':'fail');
      pill.textContent = pass ? 'PASS (\u2265'+PASS+'%)' : 'BELOW '+PASS+'%';
      document.getElementById('r-line').textContent =
        correct + ' / ' + exam.length + ' correct' + (auto ? ' \u00b7 time expired' : '') +
        ' \u00b7 approx scaled ' + Math.round(pct*10) + '/1000';
      const tb = document.getElementById('r-domain'); tb.innerHTML = '';
      [1,2,3,4].forEach(d => {
        const [c,n] = dom[d]; const p = n ? Math.round(c/n*100) : 0;
        tb.innerHTML += '<tr><td>'+DOMAIN_NAMES[d]+'</td><td>'+c+' / '+n+'</td><td>'+p+'%</td></tr>';
      });
      buildReview();
      window.scrollTo({top:0});
    }

    function buildReview() {
      const box = document.getElementById('review'); box.innerHTML = '';
      exam.forEach((item, idx) => {
        const chosen = answers[idx];
        const isMulti = Array.isArray(item.ma);
        const chosenArr = isMulti ? (Array.isArray(chosen) ? chosen : []) : [];
        const ok = isCorrect(item, chosen);
        const card = document.createElement('div'); card.className='q';
        card.innerHTML = '<div class="q-num">Q'+(idx+1)+' &middot; '+DOMAIN_NAMES[item.d]+
          ' &middot; '+(ok?'<span class="verdict right">correct</span>':'<span class="verdict no">incorrect</span>')+'</div>'+
          '<div class="q-text">'+item.q+'</div>';
        const ul = document.createElement('ul'); ul.className='opts';
        item.opts.forEach((opt, oi) => {
          const li = document.createElement('li'); li.className = 'opt';
          const isSel = isMulti ? chosenArr.includes(oi) : chosen === oi;
          const isRight = isMulti ? item.ma.includes(oi) : oi === item.a;
          if (isRight) li.classList.add('correct');
          else if (isSel) li.classList.add('wrong');
          li.innerHTML = '<span class="letter">'+LETTERS[oi]+'.</span> <span>'+opt+
            (isSel ? ' <em>(your answer)</em>':'')+'</span>';
          ul.appendChild(li);
        });
        card.appendChild(ul);
        const ex = document.createElement('div'); ex.className='explain';
        ex.innerHTML = '<strong>Answer'+(isMulti?'s':'')+': '+correctLetters(item)+'.</strong> '+item.why;
        card.appendChild(ex);
        box.appendChild(card);
      });
    }

    document.getElementById('startBtn').addEventListener('click', startExam);
    document.getElementById('resumeBtn').addEventListener('click', () => { const s = loadSaved(); if (s) resumeExam(s); });
    document.getElementById('pauseBtn').addEventListener('click', pauseExam);
    document.getElementById('submitBtn').addEventListener('click', () => submit(false));
    document.getElementById('submitBtn2').addEventListener('click', () => submit(false));
    document.getElementById('retakeBtn').addEventListener('click', startExam);
    document.getElementById('reviewToggle').addEventListener('click', (e) => {
      const r = document.getElementById('review'); const show = r.classList.toggle('hide') === false;
      e.target.textContent = show ? 'Hide review' : 'Show review';
    });
    maybeShowResume();
  </script>
</body>
</html>
"""

html = TEMPLATE.replace("__POOL__", POOL_JSON)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)
print("Wrote %s (%d bytes)" % (OUT, len(html)))
