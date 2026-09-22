#!/usr/bin/env python3
"""Build exam-hardest.html by reusing the exam-targeted.html drill engine but
swapping in only the HARDEST questions (the exam-edge set plus brand-new ones).

Keeps the same self-contained engine: filters, scroll-preserving render,
single- and multi-answer support. Run: python3 build_hardest.py
"""
import os
import re

DIR = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(DIR, "exam-targeted.html")
OUT = os.path.join(DIR, "exam-hardest.html")

with open(SRC, encoding="utf-8") as f:
    html = f.read()

# The hardest-question array. Reuses the same { topic, q, opts, answer/answers, why } schema.
HARDEST = r"""    const QUESTIONS = [
      // ===== Hardest set: exam-edge (doc-verified) =====
      { topic: "1.1", q: "You fine-tune a model with Cortex Fine-tuning (FINETUNE 'CREATE'). Which set of facts is correct?",
        opts: ["Any model can be fine-tuned; needs ACCOUNTADMIN; data columns can be named anything","Base model is <code>llama3.1-8b</code>; the query result MUST have columns named <code>prompt</code> and <code>completion</code>; creator needs <code>CREATE MODEL</code> on the schema","Training data columns must be <code>input</code>/<code>output</code>; needs CREATE WAREHOUSE","Fine-tuned models work in any region via cross-region inference"], answer: 1,
        why: "Cortex Fine-tuning (text) uses base model llama3.1-8b; the training/validation query MUST produce columns literally named prompt and completion (alias with AS); the creating role needs CREATE MODEL (or OWNERSHIP) on the target schema, plus SNOWFLAKE.CORTEX_USER. Cross-region inference does NOT support fine-tuned models \u2014 inference must run in the model's region (replicate the model to move it)." },
      { topic: "3.4", q: "A teammate says \"turn on Cortex Guard to stop prompt-injection attacks on our agent.\" What's the precise correction?",
        opts: ["Correct \u2014 Cortex Guard blocks prompt injection","Cortex Guard (guardrails=TRUE, Llama Guard 3) filters HARMFUL model output; PROMPT-INJECTION/jailbreak defense is Cortex AI Guardrails (set via ALTER ACCOUNT ... AI_SETTINGS advanced_prompt_injection) for Agents/CoWork/CoCo","Both are the same feature with two names","Guardrails prevent hallucination"], answer: 1,
        why: "Two different controls: Cortex Guard = a COMPLETE/AI_COMPLETE safety filter (guardrails=TRUE) that removes harmful content (violence, hate, self-harm...) using Llama Guard 3. Cortex AI Guardrails = Horizon feature configured with ALTER ACCOUNT SET AI_SETTINGS (advanced_prompt_injection) that defends Cortex Agents/CoWork/CoCo against prompt injection + jailbreak. Neither addresses factual accuracy \u2014 that's grounding (RAG/VQR) measured by groundedness." },
      { topic: "2.1", q: "You need deterministic, machine-parseable JSON from <code>AI_COMPLETE</code>. Which is TRUE about structured outputs?",
        opts: ["Default temperature is 1; you must raise it for JSON","<code>response_format</code> (JSON schema or TYPE literal) works only with the SINGLE-STRING AI_COMPLETE, NOT the prompt-object (image/doc) form; default temperature is already 0","Type literals support VARIANT and DATE top-level types","Schema property names may contain spaces"], answer: 1,
        why: "response_format (JSON schema, or a TYPE OBJECT literal) is supported only for AI_COMPLETE single-string \u2014 you CANNOT get structured output from the prompt-object (image/document) form. AI_COMPLETE temperature defaults to 0 (deterministic already). Type literals can't use VARIANT/MAP/date-time as mapped types; schema keys can't contain spaces. For OpenAI models the schema also needs additionalProperties=false and every property in 'required'." },
      { topic: "2.2", q: "In a Cortex Analyst semantic model, a verified query in the VQR must reference tables/columns how?",
        opts: ["By the physical base-table and column names","By the LOGICAL names defined in the semantic model \u2014 the logical table name prefixed with two underscores (e.g. <code>__sales_data</code>)","By fully-qualified DB.SCHEMA.TABLE only","By column ordinal position"], answer: 1,
        why: "Verified queries must use the semantic model's LOGICAL table/column names, not the underlying physical names. The logical table is referenced with a double-underscore prefix (e.g. FROM __sales_data), and logical column names (not the physical d_state/dt/amt) are used. Invalid/physical-name queries hurt Analyst accuracy." },
      { topic: "2.1", q: "Which pairing of embedding model to VECTOR dimension is correct for building a similarity search column?",
        opts: ["<code>snowflake-arctic-embed-m-v1.5</code> \u2192 VECTOR(FLOAT, 1024)","<code>snowflake-arctic-embed-l-v2.0</code> \u2192 VECTOR(FLOAT, 1024); <code>snowflake-arctic-embed-m-v1.5</code> \u2192 VECTOR(FLOAT, 768)","All Arctic embed models output 512 dimensions","Dimensions are chosen freely by the user"], answer: 1,
        why: "Output dimension is fixed by the model: arctic-embed-m / m-v1.5 / e5-base-v2 = 768; arctic-embed-l-v2.0 / voyage-multilingual-2 / nv-embed-qa-4 = 1024. The VECTOR column must match (e.g. VECTOR(FLOAT, 768)). 512 is the context window (tokens), not the dimension. AI_EMBED bills input tokens only; the vector similarity functions incur NO token cost." },
      { topic: "2.1", q: "Best practice for calling <code>VECTOR_COSINE_SIMILARITY</code> in a top-k semantic search query?",
        opts: ["Call it in the WHERE clause so it runs on every row","Put it in the SELECT with a column alias, then ORDER BY that alias and LIMIT k (optionally filter the alias in WHERE)","Only usable inside a JOIN ON clause","It must be wrapped in AI_COMPLETE"], answer: 1,
        why: "Docs recommend calling the similarity function in the SELECT (aliased) and using ORDER BY alias + LIMIT k, so it's computed for the rows the WHERE clause selects rather than blindly over all rows. To threshold on similarity, alias it in SELECT and reference the alias in WHERE. Vector similarity functions don't consume tokens." },
      { topic: "2.2", q: "A Cortex Search Service is created on a table protected by a row access policy. A role with only USAGE on the service (no access to the base rows) queries it. What happens?",
        opts: ["It sees only rows its own role can read","It errors out due to the policy","It can see results from ALL indexed rows the service OWNER can read \u2014 Cortex Search runs with OWNER'S RIGHTS","Row policies are re-applied at query time per querying role"], answer: 2,
        why: "Cortex Search queries run with OWNER'S RIGHTS: any role with USAGE on the service can retrieve any data the service indexed, regardless of that role's privileges on the underlying tables/views. So a querying role can see rows it could NOT read directly \u2014 a key governance caution when granting USAGE on a search service." },
      { topic: "4.2", q: "Which statement about <code>CREATE CORTEX SEARCH SERVICE</code> is correct?",
        opts: ["<code>EMBEDDING_MODEL</code> and <code>REFRESH_MODE</code> can be changed later with ALTER","Default embedding model is <code>snowflake-arctic-embed-m-v1.5</code>; the source query must qualify for dynamic-table INCREMENTAL refresh and needs change tracking; EMBEDDING_MODEL/REFRESH_MODE are fixed at create (use CREATE OR REPLACE to change)","Any SELECT works, including non-incremental constructs","REFRESH_MODE defaults to FULL"], answer: 1,
        why: "Default embedding model = snowflake-arctic-embed-m-v1.5. REFRESH_MODE defaults to INCREMENTAL and the source query must satisfy dynamic-table incremental-refresh constraints; change tracking must be enabled on base objects (Snowflake tries to enable it). EMBEDDING_MODEL and REFRESH_MODE CANNOT be altered \u2014 recreate with CREATE OR REPLACE. Recommended chunk size \u2264512 tokens; base result must be <400M rows." },
      { topic: "3.1", q: "Since the USE AI FUNCTIONS privilege was introduced, what does a custom role need to call <code>AI_COMPLETE</code>?",
        opts: ["Only <code>SNOWFLAKE.CORTEX_USER</code>","BOTH the account-level <code>USE AI FUNCTIONS</code> privilege (or per-function <code>USE AI FUNCTION AI_COMPLETE</code>) AND a <code>CORTEX_USER</code>/<code>AI_FUNCTIONS_USER</code> database role","Only ACCOUNTADMIN","Only <code>CORTEX_MODELS_ALLOWLIST</code> set to 'All'"], answer: 1,
        why: "Access is now gated by TWO things: the account-level USE AI FUNCTIONS privilege (granted to PUBLIC by default, or a per-function USE AI FUNCTION <name>) AND one of the CORTEX_USER / AI_FUNCTIONS_USER database roles. Missing either blocks the call. Model access (allowlist/RBAC) is a separate, third control layer." },
      { topic: "4.4", q: "Which is a real documented LIMIT you must design around for Cortex Search / doc functions?",
        opts: ["Cortex Search base result must be < 400M rows; AI_PARSE_DOCUMENT max ~2,000 pages/doc; AI_EXTRACT max 125 pages/doc","Cortex Search has no row limit","AI_PARSE_DOCUMENT max 100 pages","AI_EXTRACT has no page limit"], answer: 0,
        why: "Documented hard limits: Cortex Search materialized source query must be <400M rows (else creation fails); AI_PARSE_DOCUMENT max 2,000 pages and 100 MB per doc; AI_EXTRACT max 125 pages/doc (each page ~970 tokens). Knowing which limit maps to which function is a common D4 trap." },
      { topic: "3.3", q: "Which single ACCOUNT_USAGE view gives per-QUERY token + credit attribution for AISQL functions (the current canonical one)?",
        opts: ["<code>METERING_DAILY_HISTORY</code>","<code>CORTEX_AISQL_USAGE_HISTORY</code> (per-query model, tokens, token_credits) \u2014 don't also sum the legacy CORTEX_FUNCTIONS_USAGE_HISTORY / CORTEX_AI_FUNCTIONS_USAGE_HISTORY","<code>QUERY_HISTORY</code>","<code>WAREHOUSE_METERING_HISTORY</code>"], answer: 1,
        why: "CORTEX_AISQL_USAGE_HISTORY is the current canonical per-query view (model, tokens, token_credits, query_tag, user, warehouse). CORTEX_FUNCTIONS_USAGE_HISTORY (legacy) and CORTEX_AI_FUNCTIONS_USAGE_HISTORY (intermediate) OVERLAP with it \u2014 don't sum all three. For credits-by-AI-service per day use METERING_DAILY_HISTORY (SERVICE_TYPE) instead." },
      { topic: "2.2", q: "You must stop an LLM from inventing fields AND make output repeatable. Best combination?",
        opts: ["Structured Outputs (response_format with 'required') + temperature=0","guardrails=TRUE + temperature=1","show_details=TRUE only","AI_CLASSIFY then AI_TRANSLATE"], answer: 0,
        why: "A response_format JSON schema with a 'required' list constrains output to your structure (COMPLETE errors if a required field can't be produced), and temperature=0 makes generation deterministic. Guardrails is a safety filter (not a format control); show_details only adds metadata. Docs explicitly recommend temperature=0 for consistent structured output." },

      // ===== Hardest set: brand-new (doc-verified) =====
      { topic: "2.5", q: "You fine-tune <code>arctic-extract</code> for document extraction. Which is correct about the training data?",
        opts: ["It uses prompt/completion columns like text fine-tuning","It uses a Snowflake DATASET whose rows have <code>File</code>, <code>Prompt</code>, and <code>Response</code> columns; inference is via <code>AI_EXTRACT(model => ...)</code>","It trains directly on a stage of PDFs with no labels","It requires ACCOUNTADMIN and outputs to AI_COMPLETE"], answer: 1,
        why: "arctic-extract fine-tuning (for AI_EXTRACT) uses a Snowflake Dataset object with columns File (path), Prompt (question schema), and Response (answers) \u2014 NOT prompt/completion (that's the llama3.1-8b text path). You then run inference with AI_EXTRACT(model => 'db.schema.my_tuned_model', file => TO_FILE(...)). Needs CREATE MODEL + CORTEX_USER; client-side-encrypted stages unsupported." },
      { topic: "3.4", q: "Which sequence correctly evaluates a RAG app end-to-end with Snowflake AI Observability?",
        opts: ["Enable Cortex Guard \u2192 create run \u2192 execute \u2192 monitor","Instrument/evaluate with the TruLens SDK \u2192 register the app in Snowflake \u2192 create a run over an input dataset \u2192 execute to produce traces + RAG-Triad metrics \u2192 monitor in Snowsight","Create run \u2192 execute \u2192 cancel run \u2192 read metrics","AI_COMPLETE with show_details \u2192 read usage tokens"], answer: 1,
        why: "AI Observability uses the TruLens SDK to instrument and evaluate; you register the app, create a run over an input dataset, execute it to generate traces and RAG-Triad metrics (context relevance, groundedness, answer relevance), and monitor in Snowsight. Traces are written to an event table. Cancelling a run yields no metrics; Cortex Guard is unrelated to evaluation." },
      { topic: "3.2", q: "You want a role that can call the Cortex Agents API but NOT other Cortex features. Best grant?",
        opts: ["Grant <code>SNOWFLAKE.CORTEX_USER</code> to the role","Grant <code>SNOWFLAKE.CORTEX_AGENT_USER</code> to a custom role (and do NOT grant CORTEX_USER); assign that role to users","Set ENABLE_CORTEX_ANALYST = TRUE","Grant OWNERSHIP on the agent to the user directly"], answer: 1,
        why: "SNOWFLAKE.CORTEX_AGENT_USER scopes access to Cortex Agents only. CORTEX_USER would re-open ALL covered AI features. Database roles can't be granted to users directly \u2014 grant to a custom role, then role\u2192user. Also remember: an agent evaluates the querying user's DEFAULT role and needs a DEFAULT warehouse, with privileges on every tool object." },
      { topic: "2.5", q: "You register a custom Python model and must serve it for real-time, low-latency external calls. Which path?",
        opts: ["Schedule a Task to run batch inference nightly","Deploy the model to Snowpark Container Services as a service (<code>model_version.create_service(...)</code>) exposing an HTTP endpoint; external callers POST to it","Only AI_COMPLETE can serve models","Copy the model file to a stage and read it with SQL"], answer: 1,
        why: "For real-time external serving, deploy the registered model as an SPCS service via ModelVersion.create_service(...), which stands up an HTTP endpoint an external gateway can POST to. Tasks are batch/scheduled (not real-time); AI_COMPLETE serves Cortex base models, not your custom pickled model." },
      { topic: "4.2", q: "You must OCR a scanned PDF into plain text and also extract 4 named fields into a schema. Which two functions, in order?",
        opts: ["AI_CLASSIFY then AI_TRANSLATE","AI_PARSE_DOCUMENT (OCR mode) for full text, then AI_EXTRACT with a response schema over a FILE object built with TO_FILE","AI_EMBED then VECTOR_COSINE_SIMILARITY","AI_COMPLETE then SPLIT_TEXT_RECURSIVE_CHARACTER"], answer: 1,
        why: "AI_PARSE_DOCUMENT (OCR mode) turns the scanned PDF into text; AI_EXTRACT with a responseFormat schema pulls specific named fields. AI_EXTRACT consumes a FILE object via TO_FILE(@stage,'path') \u2014 not a bare string path. (Use LAYOUT mode instead of OCR when you need tables/structure.)" },
      { topic: "3.3", q: "Cross-region inference is needed because your region lacks a model. Who enables it and how?",
        opts: ["Any user; SET CORTEX_MODELS_ALLOWLIST","ACCOUNTADMIN runs <code>ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION'</code> (or AWS_US / AWS_GLOBAL)","It's on by default in every account","SECURITYADMIN sets it per warehouse"], answer: 1,
        why: "Cross-region inference is an ACCOUNT parameter set by ACCOUNTADMIN: CORTEX_ENABLED_CROSS_REGION = ANY_REGION (or a scoped value like AWS_US / AWS_GLOBAL). Default is DISABLED. It lets a request process in another region when your home region lacks the model \u2014 but it does NOT support fine-tuned models." },
      { topic: "1.2", q: "A 40-page contract exceeds the model's context window. Which capability addresses this and why?",
        opts: ["Fine-tuning, because it enlarges the context window","Chunking \u2014 long inputs must be split to fit the max tokens (prompt + response) the model can consider","Cross-region inference, because other regions have bigger windows","Guardrails, because they compress text"], answer: 1,
        why: "The context window is the maximum tokens (prompt + generated response) a model can consider at once. Long documents must be chunked (e.g. SPLIT_TEXT_RECURSIVE_CHARACTER) to fit; exceeding it truncates or errors and raises latency/cost. Fine-tuning changes behavior, not window size; cross-region/guardrails are unrelated." },
      { topic: "3.1", q: "Which is TRUE about the <code>CORTEX_MODELS_ALLOWLIST</code> account parameter?",
        opts: ["It can be set at session or warehouse level","It's an ACCOUNT-level parameter set only by ACCOUNTADMIN via ALTER ACCOUNT; value is 'All', 'None', or a lowercase comma-separated model list; model RBAC can still grant access when it's 'None'","It accepts an array literal like ['a','b']","Model names are case-insensitive"], answer: 1,
        why: "CORTEX_MODELS_ALLOWLIST is account-level, ACCOUNTADMIN-only (ALTER ACCOUNT). It takes 'All', 'None', or one quoted comma-separated STRING of lowercase, case-sensitive model names ('mistral-large2,llama3.1-70b') \u2014 NOT an array. Access is granted if EITHER the allowlist OR model RBAC (application roles) permits, so RBAC still works when the allowlist is 'None'. (The allowlist is being deprecated in favor of RBAC.)" },
      { topic: "2.3", q: "In a Streamlit chat app, which command renders a role-based chat turn that can hold text, tables, and charts and shows an avatar?",
        opts: ["<code>st.write</code>","<code>st.chat_message(name, avatar=...)</code> used as a context manager","<code>st.chat_input</code>","<code>st.text</code>"], answer: 1,
        why: "st.chat_message(name, avatar=...) creates the role-based message container; used as a context manager (with st.chat_message('assistant'):) it can host any element \u2014 st.write, charts, dataframes, markdown. st.chat_input renders the input box; st.write/st.text render content but have no role/avatar semantics." },
      { topic: "4.4", q: "AI_PARSE_DOCUMENT is slow, so you scale the warehouse to X-LARGE \u2014 no improvement. Why, and what's recommended?",
        opts: ["A bug \u2014 file a ticket","It bills/performs per PAGE and doesn't benefit from a big warehouse; use a warehouse no larger than MEDIUM and split large docs with page_split/page_filter","Enable guardrails to speed it up","Raise max_tokens"], answer: 1,
        why: "AI_PARSE_DOCUMENT cost and performance scale with document PAGES, not warehouse size \u2014 a larger warehouse just wastes credits. Use a warehouse no larger than MEDIUM, and split documents exceeding the ~2,000-page limit with page_split / page_filter. Same 'no larger than MEDIUM' guidance applies to AI_EXTRACT and Cortex Search refreshes." },
      { topic: "3.4", q: "A colleague enables Cortex Guard and reports the answers are 'more accurate now.' What's the accurate framing?",
        opts: ["Correct \u2014 Guard improves factual accuracy","Guard filters HARMFUL content (Llama Guard 3); it does not improve factual accuracy. Reduce hallucination with RAG grounding / Verified Queries, and measure it with the groundedness metric","Guard removes PII, which improves accuracy","Guard only works with Cortex Analyst"], answer: 1,
        why: "Cortex Guard is a safety filter for harmful output \u2014 it has no effect on factual correctness. Factuality comes from GROUNDING (RAG retrieval, Verified Query Repository), and you measure whether answers are supported by retrieved context using the groundedness metric in AI Observability (RAG Triad)." },
      { topic: "2.1", q: "Which statement about token billing across AI functions is correct?",
        opts: ["All functions bill input+output equally","<code>AI_EMBED</code> / embedding functions bill INPUT tokens only; generative functions (AI_COMPLETE, AI_TRANSLATE, AI_CLASSIFY, etc.) bill INPUT + OUTPUT; vector similarity functions incur NO token cost","AI_COUNT_TOKENS is billed per token counted","Vector similarity functions bill per comparison token"], answer: 1,
        why: "Embedding functions (AI_EMBED, EMBED_TEXT_768/1024) bill on input tokens only at a low rate. Generative functions bill both input and output tokens at a higher rate. Vector similarity functions (COSINE/L2/L1/INNER_PRODUCT) incur NO token cost. AI_COUNT_TOKENS only incurs compute to run, no token charge \u2014 use it to estimate before a big batch." }
    ];"""

# Replace the QUESTIONS array (everything from `const QUESTIONS = [` up to the
# closing `];` that precedes `const LETTERS`).
pattern = re.compile(r"    const QUESTIONS = \[.*?\n    \];", re.DOTALL)
html, n = pattern.subn(lambda m: HARDEST, html, count=1)
assert n == 1, "Failed to locate QUESTIONS array"

# Customize titles / header text for the hardest page.
html = html.replace(
    "<title>SnowPro Gen AI (GES-C02) \u2014 Targeted Drill</title>",
    "<title>SnowPro Gen AI (GES-C02) \u2014 Hardest Questions</title>",
)
html = html.replace(
    "<h1>SnowPro Gen AI (GES-C02) \u2014 Targeted Drill</h1>",
    "<h1>SnowPro Gen AI (GES-C02) \u2014 Hardest Questions</h1>",
)
html = re.sub(
    r'<p class="sub">Built around the exact subtopics.*?</p>',
    '<p class="sub">The toughest exam-edge questions \u2014 the ones that trip people up. '
    'Doc-verified, with detailed explanations and trap breakdowns. Filter by subtopic, '
    'or grind straight through. Single-answer locks on click; multi-answer ("Select TWO") '
    'uses checkboxes + Check answer.</p>',
    html,
    count=1,
    flags=re.DOTALL,
)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

count = html.count("topic:")
print("Wrote %s (%d bytes, %d questions)" % (OUT, len(html), count))
