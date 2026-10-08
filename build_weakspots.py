#!/usr/bin/env python3
"""Build exam-weakspots.html: a hard, scenario-based "Weak-Spot Drill" focused on
the concepts Ahmed has gotten wrong (see genai-answer-log.md): cost/credits,
grants & who-can-grant, document extraction (FILE objects), chunking params,
compute-pool defaults, doc-pipeline PARSE_JSON/TARGET_LAG traps, and Streamlit
chat. Reuses the exam-targeted.html drill engine, adds a seeded option-shuffler
(so correct positions are distributed) and localStorage auto save/resume.

Run: python3 build_weakspots.py
"""
import os
import re
import random

DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(DIR, "exam-targeted.html")
OUT = os.path.join(DIR, "exam-weakspots.html")

with open(SRC, encoding="utf-8") as f:
    html = f.read()

WEAK = r"""    const QUESTIONS = [
      // ===== Cost & credits (D3.3) =====
      { topic: "3.3", q: "Query A calls AI_EMBED and processes 50,000 input tokens; Query B calls AI_COMPLETE on llama3.1-70b with only 3,000 tokens. Query B bills MORE token-credits. Which explanation is correct?",
        opts: ["Embedding bills INPUT tokens only (low rate); generative completion bills INPUT + OUTPUT tokens, and each model has its own per-token credit rate \u2014 so fewer tokens on a pricier generative model can cost more", "AI_COMPLETE silently calls Cortex Analyst, which adds the extra credits", "AI_EMBED is always free, so any completion will cost more", "Query B ran on a larger virtual warehouse, doubling the credits"], answer: 0,
        why: "Credits = tokens \u00d7 per-model rate. AI_EMBED is priced on INPUT tokens only at a low rate; generative AI_COMPLETE is priced on INPUT + OUTPUT tokens at a higher, model-specific rate. No hidden Analyst call, no 'embedding is free', and warehouse size isn't the token-credit driver." },
      { topic: "3.3", q: "You need per-call token AND credit detail for Cortex AI Function usage today. Which is the CURRENT view, and why are the others wrong?",
        opts: ["CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY \u2014 the current per-query view", "CORTEX_AI_FUNCTIONS_USAGE_HISTORY \u2014 current per-call view (tokens + CREDITS); CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY is no longer updated, METERING_DAILY_HISTORY is daily-by-service only, QUERY_HISTORY has no per-AI credit column", "METERING_DAILY_HISTORY, filtered to the AI_SERVICES service type", "QUERY_HISTORY using its CREDITS_USED_CORTEX column"], answer: 1,
        why: "CORTEX_AI_FUNCTIONS_USAGE_HISTORY is the current Account Usage view (per call: tokens, CREDITS, model, warehouse, role). CORTEX_FUNCTIONS_QUERY_USAGE_HISTORY is deprecated/not updated; METERING_DAILY_HISTORY is coarse daily-by-service; QUERY_HISTORY has no per-AI credit column." },
      { topic: "3.3", q: "CORTEX_SEARCH_DAILY_USAGE_HISTORY breaks Cortex Search spend into which categories? (Select THREE.)",
        opts: ["Serving", "Embedding text (EMBED_TEXT_TOKENS)", "Batch / indexing", "Fail-safe storage", "Virtual-warehouse auto-suspend", "Network-policy evaluation"], answers: [0, 1, 2],
        why: "Search cost is NOT just a warehouse charge \u2014 the daily view splits it into serving, embedding-text, and batch/indexing. Fail-safe storage, warehouse suspend, and network-policy checks are not Search cost categories." },
      { topic: "3.3", q: "A FinOps lead wants ONE object for daily credits consumed by ALL AI services (not per-function detail). Which is the documented go-to?",
        opts: ["METERING_DAILY_HISTORY filtered to SERVICE_TYPE = 'AI_SERVICES'", "CORTEX_AI_FUNCTIONS_USAGE_HISTORY summed by day", "CORTEX_ANALYST_USAGE_HISTORY", "WAREHOUSE_METERING_HISTORY"], answer: 0,
        why: "For daily credits by AI service, use METERING_DAILY_HISTORY with SERVICE_TYPE='AI_SERVICES'. The AI-functions view is per-call detail (overkill/overlap here); Analyst view is Analyst-only; warehouse metering excludes serverless AI service credits." },

      // ===== Grants, RBAC & who-can-grant (D3.1 / D3.2) =====
      { topic: "3.2", q: "Which statements let user SOME_USER call Cortex LLM functions via SNOWFLAKE.CORTEX_USER? (Select TWO.)",
        opts: ["USE ROLE SECURITYADMIN; CREATE ROLE cu_role; GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE cu_role; GRANT ROLE cu_role TO USER some_user;", "USE ROLE ACCOUNTADMIN; CREATE ROLE cu_role; GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE cu_role; GRANT ROLE cu_role TO USER some_user;", "USE ROLE SYSADMIN; CREATE ROLE cu_role; GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE cu_role; GRANT ROLE cu_role TO USER some_user;", "GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO USER some_user;", "USE ROLE USERADMIN; GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE PUBLIC;"], answers: [0, 1],
        why: "A SNOWFLAKE database role must be granted to an ACCOUNT role (then that role to the user) \u2014 so direct-to-user (D) is invalid. Making the grant needs MANAGE GRANTS: SECURITYADMIN (A) or ACCOUNTADMIN (B) qualify. SYSADMIN (C) lacks MANAGE GRANTS; USERADMIN (E) can create users/roles but not MANAGE GRANTS, and granting to PUBLIC would over-expose anyway." },
      { topic: "3.1", q: "A role can SELECT from tables but gets an authorization error on AI_COMPLETE. Which pair of conditions must BOTH be true to fix it? (Select TWO.)",
        opts: ["The role holds the account-level USE AI FUNCTIONS privilege (or per-function USE AI FUNCTION AI_COMPLETE)", "The role has a CORTEX_USER or AI_FUNCTIONS_USER database role", "The role is granted ACCOUNTADMIN", "The role owns the SNOWFLAKE database", "The warehouse is resized to at least Medium"], answers: [0, 1],
        why: "Current access needs BOTH the account privilege USE AI FUNCTIONS AND a CORTEX_USER/AI_FUNCTIONS_USER database role \u2014 missing either blocks the call. ACCOUNTADMIN 'works' only because it bypasses these; ownership of SNOWFLAKE and warehouse size are irrelevant to the auth error." },
      { topic: "3.2", q: "In the system role hierarchy, which role can make the grant of a SNOWFLAKE database role to an account role WITHOUT being ACCOUNTADMIN, and why can't SYSADMIN?",
        opts: ["SECURITYADMIN \u2014 it holds MANAGE GRANTS (and inherits USERADMIN); SYSADMIN builds objects but has no MANAGE GRANTS", "USERADMIN \u2014 it owns all grants; SYSADMIN lacks CREATE ROLE", "PUBLIC \u2014 everyone can grant database roles", "Only ACCOUNTADMIN can ever grant a database role"], answer: 0,
        why: "SECURITYADMIN has MANAGE GRANTS (and inherits USERADMIN) so it can make the grant; SYSADMIN is the object builder (warehouses/DBs/schemas) and has no MANAGE GRANTS. USERADMIN manages users/roles but not arbitrary grants; PUBLIC can't grant; ACCOUNTADMIN isn't the ONLY option." },
      { topic: "3.1", q: "A user has USAGE on a Cortex Agent whose custom tool reads a table their role can't SELECT. What happens?",
        opts: ["The tool call is denied \u2014 Agent USAGE does NOT bypass underlying object permissions; the querying role still needs its own access (and Agents evaluate the user's DEFAULT role + default warehouse)", "The Agent runs the tool as ACCOUNTADMIN and returns the rows", "USAGE on the Agent implicitly grants SELECT on referenced tables", "Snowflake clones the restricted table into a scratch schema the user owns"], answer: 0,
        why: "Agent permission \u2260 data permission: the calling role must independently hold privileges on each underlying source/tool. Agents evaluate the user's DEFAULT role (not session role) and need a default warehouse. No ACCOUNTADMIN escalation, implicit SELECT, or auto-clone occurs." },
      { topic: "3.1", q: "As of the 2026 rollout, how should you restrict which Cortex models a role may use, and what's the exact transitional state of the old control?",
        opts: ["Keep using CORTEX_MODELS_ALLOWLIST \u2014 it's the long-term control", "Use model RBAC (CORTEX-MODEL-ROLE-* application roles on SNOWFLAKE.MODELS); CORTEX_MODELS_ALLOWLIST is deprecated \u2014 it can now only be set to 'None' \u2014 and RBAC is enforced even for embedding models (AI_EMBED, AI_SIMILARITY, Cortex Search)", "Model access can no longer be restricted at all", "Set CORTEX_MODELS_ALLOWLIST = 'ANY_REGION' to pin models"], answer: 1,
        why: "Model RBAC (application roles in SNOWFLAKE.MODELS) is the go-forward, fine-grained mechanism. The allowlist is deprecating \u2014 only 'None' is a permitted change during transition \u2014 and RBAC now covers embedding models too. 'ANY_REGION' is a cross-region value, unrelated to the allowlist." },

      // ===== Document extraction & FILE objects (D4.2) =====
      { topic: "4.2", q: "Invoice PDFs sit on a stage. You must pull invoice_number/date/total into structured output. Which is a CORRECT approach, and what's the specific error in the tempting wrong one?",
        opts: ["Pass the bare stage path STRING directly to AI_EXTRACT with an object schema", "Either parse first with AI_PARSE_DOCUMENT then AI_EXTRACT on the text, OR call AI_EXTRACT on a FILE object (TO_FILE) with a responseFormat schema \u2014 the trap is passing a bare path string: AI_EXTRACT needs a FILE object, not a raw string path", "Call AI_COMPLETE on the raw PDF bytes and regex the fields", "Run AI_SENTIMENT on the file to score the invoice"], answer: 1,
        why: "Two valid paths: AI_PARSE_DOCUMENT\u2192AI_EXTRACT(text), or AI_EXTRACT directly on a FILE reference built with TO_FILE + a responseFormat schema. The classic wrong answer passes a bare stage-path STRING to AI_EXTRACT \u2014 it requires a FILE object. AI_COMPLETE-on-bytes and AI_SENTIMENT don't do structured field extraction." },
      { topic: "4.2", q: "A pipeline parses a PDF with AI_PARSE_DOCUMENT and then wants the text in a column for chunking. What must you remember about the function's OUTPUT?",
        opts: ["It returns a VARIANT you can use as-is without parsing", "It returns a JSON STRING; convert it with PARSE_JSON and read the :content field before using the text", "It returns plain TEXT already stripped of JSON", "It returns a VECTOR you pass straight to Cortex Search"], answer: 1,
        why: "AI_PARSE_DOCUMENT returns a JSON STRING; you typically PARSE_JSON it and read the :content field to get the extracted text. It is not a ready VARIANT, not plain text, and not a vector." },
      { topic: "4.2", q: "A PDF has multi-column text, nested tables, and headings that MUST survive for RAG; separately you also need the embedded images. Which configuration is right?",
        opts: ["mode='OCR' (fastest) with extract_images=true", "mode='LAYOUT' (preserves tables/headings/reading order) with extract_images=true \u2014 image extraction REQUIRES LAYOUT", "mode='TEXT' with images=true", "mode='LAYOUT' only works if you also set mode='OCR'"], answer: 1,
        why: "LAYOUT preserves structure for RAG; extracting embedded images requires LAYOUT with extract_images=true. OCR is fast text-only and does not support extract_images; there is no 'TEXT' mode / 'images' flag, and LAYOUT doesn't require OCR." },
      { topic: "4.4", q: "Match the hard limits: which pairing is correct for the document functions?",
        opts: ["AI_PARSE_DOCUMENT: 100 MB & 2,000 pages per file; AI_EXTRACT: ~125 pages per doc", "AI_PARSE_DOCUMENT: 50 MB & 250 pages; AI_EXTRACT: unlimited", "AI_PARSE_DOCUMENT: 1 GB & 10,000 pages; AI_EXTRACT: 2,000 pages", "Both functions share a single 100-page limit"], answer: 0,
        why: "AI_PARSE_DOCUMENT allows up to 100 MB and 2,000 pages per file; AI_EXTRACT handles roughly 125 pages per document. The other pairings invent limits." },

      // ===== Chunking parameters (D2.2 / D4) =====
      { topic: "2.2", q: "SPLIT_TEXT_RECURSIVE_CHARACTER('markdown', chunk_size, overlap) produced chunks like ['A few showers,','showers early','early becoming','becoming a','a steady rain']. Which (chunk_size, overlap) is most consistent, and why not the others?",
        opts: ["(100, 25) \u2014 big window", "(15, 10) \u2014 chunk_size must be \u2265 the longest chunk (~14 chars) but still small, and the heavy whole-phrase overlap implies ~10; (10,2) is too small for a 14-char chunk, (25,15) and (100,25) are too large to yield ~14-char chunks", "(10, 2) \u2014 tiny window", "(25, 15) \u2014 medium window"], answer: 1,
        why: "chunk_size has to be at least the longest emitted chunk (~14 chars) yet small enough to force these short pieces \u2192 ~15; the large repeated overlap between adjacent chunks implies ~10. (10,2) can't hold a 14-char chunk; (25,15)/(100,25) would produce much longer chunks." },
      { topic: "2.2", q: "Which statements about SPLIT_TEXT_RECURSIVE_CHARACTER are TRUE? (Select TWO.)",
        opts: ["Its default separators (e.g. [\"\\n\\n\",\"\\n\",\" \",\"\"]) split on paragraph breaks first, preserving natural-language boundaries", "overlap repeats context from the end of one chunk at the start of the next so facts near a boundary aren't severed", "It requires a unique hash key per chunk to deduplicate", "It only works on Markdown input", "It returns a single concatenated string, not an array"], answers: [0, 1],
        why: "Recursive splitting tries natural separators (paragraph, then line, then space) first, preserving boundaries; overlap carries boundary context forward. There is no hash-key dedup requirement, it supports formats beyond Markdown (there's a separate markdown-header splitter), and it returns an array of chunks." },

      // ===== Compute pools / SPCS (D2.5) =====
      { topic: "2.5", q: "Which consideration about a USER-created compute pool (to serve third-party models) is correct?",
        opts: ["It can only be created through the Snowflake CLI", "By default INITIALLY_SUSPENDED is FALSE for a user-created pool and AUTO_RESUME is TRUE, so a workload can start it automatically; node caps vary by instance family (account cap 750), not a flat 50", "A hard maximum of 50 nodes applies regardless of INSTANCE_FAMILY", "You must run ALTER COMPUTE POOL ... RESUME before first use because pools start suspended"], answer: 1,
        why: "User-created pools default INITIALLY_SUSPENDED=FALSE and AUTO_RESUME=TRUE (so no manual RESUME is needed). You can create via SQL/Snowsight/Python (not CLI-only). The 50 figure is a GPU SYSTEM-pool MAX_NODES, not a universal cap \u2014 per-family limits vary under an account limit of 750. (System GPU/CPU pools default INITIALLY_SUSPENDED=TRUE \u2014 a common confuser.)" },
      { topic: "2.5", q: "A data scientist wants to MANAGE and version a bring-your-own model and call it for inference, with no container work; a second team must RUN a custom GPU container. Which pairing is correct?",
        opts: ["Model Registry (snowflake.ml.registry) manages/serves the logged model; Snowpark Container Services on a compute pool runs the custom GPU container", "Snowpark Container Services for both", "Model Registry for both", "Cortex Fine-tuning registers the first model; a virtual warehouse (GPU mode) runs the container"], answer: 0,
        why: "'Manage/version/call a model' \u2192 Model Registry (snowflake.ml.registry); 'run a custom container/GPU' \u2192 SPCS on a compute pool. Registry can even serve via an SPCS service, but the division of labor is Registry=manage, SPCS=run. Warehouses have no GPU/custom-container support." },

      // ===== Doc ingestion pipeline traps (D4) =====
      { topic: "4.4", q: "A document-ingestion pipeline uses AI_PARSE_DOCUMENT + SPLIT_TEXT_RECURSIVE_CHARACTER + a Cortex Search service. Which statements are TRUE? (Select TWO.)",
        opts: ["The recursive splitter's default separators split on paragraph breaks first, preserving natural-language boundaries", "AI_PARSE_DOCUMENT returns a JSON string; convert with PARSE_JSON to read the :content field before splitting", "A Dynamic Table defined on the stage auto-triggers re-parse the instant a file lands", "A Cortex Search service refreshes on row INSERT immediately, independent of TARGET_LAG", "Each chunk needs a unique hash key for the Search service to dedupe"], answers: [0, 1],
        why: "True: recursive splitter preserves NL boundaries; AI_PARSE_DOCUMENT output is a JSON string needing PARSE_JSON (:content). False traps: dynamic tables refresh on TARGET_LAG (not an instant stage-file trigger), Cortex Search refreshes per its TARGET_LAG (not instantly on insert), and there's no hash-key dedup requirement." },
      { topic: "4.4", q: "A Cortex Search service is built on a table behind a row-access policy. A role with only USAGE on the service (no access to base rows) queries it. What's returned?",
        opts: ["Only the rows that role could read directly", "Results from ALL rows the service OWNER indexed \u2014 Cortex Search runs with OWNER'S RIGHTS, so USAGE on the service can expose rows the caller couldn't read directly", "An error, because the row-access policy blocks the service", "The policy is re-evaluated per querying role at query time"], answer: 1,
        why: "Cortex Search queries run with OWNER'S RIGHTS: any role with USAGE on the service can retrieve anything the service indexed, regardless of its own base-table privileges. That's a key governance caution \u2014 the policy is NOT re-applied per caller." },

      // ===== Streamlit chat UI (D2.3) =====
      { topic: "2.3", q: "A Streamlit-in-Snowflake LLM chat app must show role-based message bubbles with custom avatars and embed charts/tables/text inside each turn. Which API, and why not the near-miss?",
        opts: ["st.markdown \u2014 it renders the whole conversation", "st.chat_message(role, avatar=...) \u2014 a role-based container (supports an avatar and can host other st elements like st.dataframe/st.line_chart); st.markdown only renders text, no bubble/avatar/embeds", "st.write for everything", "st.text_area as the chat container"], answer: 1,
        why: "st.chat_message creates a role-tagged bubble, takes an avatar param, and can host other Streamlit elements (charts, tables, text). st.markdown/st.write/st.text_area render content but don't give you the role bubble + avatar + embedded-element container. (Pair it with st.chat_input for the prompt box.)" },

      // ===== A couple of trap-sibling rounders (D1/D2) =====
      { topic: "2.1", q: "You must compare the MEANING of two already-generated strings and get a single similarity score, without hand-managing vectors. Which function \u2014 and what 2026 governance nuance applies?",
        opts: ["VECTOR_COSINE_SIMILARITY on the two strings", "AI_SIMILARITY \u2014 compares two inputs' meaning directly; being embedding-based, it is subject to model RBAC after the allowlist deprecation", "AI_CLASSIFY with categories ['similar','different']", "AI_EMBED, which returns the similarity score"], answer: 1,
        why: "AI_SIMILARITY compares meaning of two inputs directly (it embeds internally). VECTOR_COSINE_SIMILARITY needs vectors, not raw strings; AI_EMBED returns a vector (not a score); AI_CLASSIFY labels. Nuance: embedding functions (AI_SIMILARITY/AI_EMBED/EMBED_TEXT) fall under model RBAC enforcement in the allowlist deprecation." },
      { topic: "2.1", q: "A 500K-row free-text table needs a CUSTOM analytical answer (\"top recurring complaint themes\") synthesized across rows beyond one context window. Which function, and how does it differ from the plain-summary sibling?",
        opts: ["SUMMARIZE per row, then concatenate", "AI_AGG \u2014 instruction-driven aggregation across many rows (not bound to one context window); AI_SUMMARIZE_AGG only makes a generic summary with no custom instruction", "AI_SUMMARIZE_AGG, which answers arbitrary analytical questions", "AI_COMPLETE with all 500K rows in one prompt"], answer: 1,
        why: "AI_AGG takes a natural-language INSTRUCTION and reduces many rows to an answer to it, beyond a single context window. AI_SUMMARIZE_AGG is a plain many-row summary (no custom instruction). SUMMARIZE is scalar; stuffing 500K rows into one prompt overflows the window. (Both AI_AGG/AI_SUMMARIZE_AGG work with only USE AI FUNCTIONS, no CORTEX_USER.)" }
    ];"""

# --- seeded option shuffler (distribute correct positions) ---
def shuffle_options(js_array_text):
    rng = random.Random(43218)
    objs = []
    depth = 0
    start = None
    for i, ch in enumerate(js_array_text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                objs.append((start, i + 1))
    out = js_array_text
    for start, end in reversed(objs):
        block = js_array_text[start:end]
        om = re.search(r"opts:\s*(\[.*?\])\s*,\s*(?:answer|answers):", block, re.DOTALL)
        if not om:
            continue
        opts_text = om.group(1)
        opt_items = re.findall(r'"((?:[^"\\]|\\.)*)"', opts_text)
        n = len(opt_items)
        perm = list(range(n))
        rng.shuffle(perm)
        new_opts = [opt_items[perm[k]] for k in range(n)]
        old_to_new = {perm[k]: k for k in range(n)}
        new_opts_text = "[" + ", ".join('"%s"' % o for o in new_opts) + "]"
        new_block = block[:om.start(1)] + new_opts_text + block[om.end(1):]
        am = re.search(r"answer:\s*(\d+)", new_block)
        if am:
            old = int(am.group(1))
            new_block = new_block[:am.start(1)] + str(old_to_new[old]) + new_block[am.end(1):]
        asm = re.search(r"answers:\s*\[([\d,\s]*)\]", new_block)
        if asm:
            olds = [int(x) for x in re.findall(r"\d+", asm.group(1))]
            news = sorted(old_to_new[o] for o in olds)
            new_block = new_block[:asm.start(1)] + ", ".join(str(x) for x in news) + new_block[asm.end(1):]
        out = out[:start] + new_block + out[end:]
    return out

WEAK = "    const QUESTIONS = " + shuffle_options(WEAK[WEAK.index("["):WEAK.rindex("]") + 1]) + ";"

pattern = re.compile(r"    const QUESTIONS = \[.*?\n    \];", re.DOTALL)
html, n = pattern.subn(lambda m: WEAK, html, count=1)
assert n == 1, "Failed to locate QUESTIONS array"

# titles / intro
html = html.replace(
    "<title>SnowPro Gen AI (GES-C02) \u2014 Targeted Drill</title>",
    "<title>SnowPro Gen AI (GES-C02) \u2014 Weak-Spot Drill</title>",
)
html = html.replace(
    "<h1>SnowPro Gen AI (GES-C02) \u2014 Targeted Drill</h1>",
    "<h1>SnowPro Gen AI (GES-C02) \u2014 Weak-Spot Drill</h1>",
)
html = re.sub(
    r'<p class="sub">Built around the exact subtopics.*?</p>',
    '<p class="sub">A hard, scenario-based set concentrated on the topics you\u2019ve missed before \u2014 cost &amp; '
    'credits, who-can-grant RBAC, document FILE-object extraction, chunking params, compute-pool defaults, '
    'doc-pipeline PARSE_JSON/TARGET_LAG traps, and Streamlit chat. Shuffled answers, auto save/resume. '
    'Single-answer locks on click; multi-answer uses checkboxes + Check answer.</p>',
    html,
    count=1,
    flags=re.DOTALL,
)

# --- auto save/resume (localStorage), unique key for this page ---
state_old = "    const state = {};\n    const pending = {};"
state_new = state_old + "\n" + r"""    const LS_KEY = "snowpro-genai-weakspots-v1";
    function saveProgress() {
      try {
        if (!Object.keys(state).length) { localStorage.removeItem(LS_KEY); return; }
        localStorage.setItem(LS_KEY, JSON.stringify({ state: state, pending: pending, ts: Date.now() }));
      } catch (e) {}
    }
    function restoreProgress() {
      try {
        const s = localStorage.getItem(LS_KEY);
        if (!s) return 0;
        const d = JSON.parse(s);
        if (d && d.state) Object.assign(state, d.state);
        if (d && d.pending) Object.assign(pending, d.pending);
        return Object.keys(state).length;
      } catch (e) { return 0; }
    }"""
assert state_old in html
html = html.replace(state_old, state_new, 1)

score_old = ('      document.getElementById("s-pct").textContent = pct === null ? "\\u2014" : pct + "%";\n'
             "    }")
score_new = ('      document.getElementById("s-pct").textContent = pct === null ? "\\u2014" : pct + "%";\n'
             "      saveProgress();\n"
             "    }")
assert score_old in html
html = html.replace(score_old, score_new, 1)

init_old = "    render(); updateScore();\n  </script>"
init_new = (r"""    const _resumed = restoreProgress();
    render(); updateScore();
    if (_resumed) {
      const _n = document.createElement("div");
      _n.textContent = "\u21ba Resumed your saved progress \u2014 " + _resumed + " answered. Click Reset to start over.";
      _n.style.cssText = "margin:14px 0;padding:10px 14px;border:1px solid #3b82f6;border-radius:8px;background:rgba(59,130,246,0.12);font-size:0.9rem;";
      quizEl.parentNode.insertBefore(_n, quizEl);
    }
  </script>""")
assert init_old in html
html = html.replace(init_old, init_new, 1)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

count = html.count("topic:")
print("Wrote %s (%d bytes, %d questions)" % (OUT, len(html), count))
