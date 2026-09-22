# Advanced Topics — Exam-Edge Gotchas (read last)

This is the **deep-dive companion** to the four domain guides. Everything here is a nuance the real exam likes to test and that the foundational notes intentionally kept simple. Grounded against Snowflake docs (2026). Skim this the day before your exam.

> How to use it: for each item, cover the answer and ask yourself *"what's the exact default / limit / exception?"* The exam rewards precision here, not the general idea.

---

## 1. AI_COMPLETE — the fine print

### Parameter defaults (memorize the numbers)
| Param | Default | Gotcha |
|---|---|---|
| `temperature` | **0** | Higher = more random. Set **0** for deterministic/structured output. |
| `top_p` | **0** | Alternative to temperature (restricts token set). Don't tune both. |
| `max_tokens` | **4096** | Caps **output** length. Too-small values → **truncated** responses (classic "why is my answer cut off"). |
| `guardrails` | **FALSE** | TRUE enables **Cortex Guard**. |

### Single-string vs. Prompt-object — the big trap
- **Single-string** `AI_COMPLETE(model, prompt, [model_parameters, response_format, show_details])` → **supports `response_format`** (structured outputs) and `show_details`.
- **Prompt-object** `AI_COMPLETE(model, PROMPT(...), [model_parameters])` (for images/documents/multimodal) → **CANNOT take a `response_format` JSON schema.** Only the single-string form does. To get structured JSON from a multimodal call, you prompt "Respond in JSON" and parse yourself.

### `show_details => TRUE`
Returns a JSON object with `choices`, `created`, `model`, and a **`usage`** block (`prompt_tokens`, `completion_tokens`, `total_tokens`). Use it for **cost/token tracking**.

### Cortex Guard (`guardrails => TRUE`)
- Built on **Meta Llama Guard 3**.
- Filters **the model's OUTPUT** (violence, hate, sexual content, self-harm, etc.) *before it's returned*.
- It is **NOT** prompt-injection defense (that's **Cortex AI Guardrails** via `AI_SETTINGS`) and **NOT** PII redaction (that's **AI_REDACT**). Three different things — the exam mixes them.
- Incurs extra compute on input tokens processed.

### `TRY_COMPLETE`
Returns **NULL** on error instead of raising — including when a model's output fails structured-output validation. Use it for resilient batch jobs.

---

## 2. Structured Outputs (AI_COMPLETE `response_format`)

Two ways to specify the format:
1. **SQL type literal** — begins with `TYPE`, top level must be an **`OBJECT`**. e.g. `response_format => TYPE OBJECT(items_count NUMBER, price ARRAY(STRING))`.
2. **JSON schema** — `{ 'type':'json', 'schema': {...} }`. Use `required` to force fields (COMPLETE errors if a required field can't be extracted).

### Limitations that cause errors (high-yield)
- **No spaces in keys.** Property names: letters, digits, hyphen, underscore only; max 64 chars.
- **Unsupported constraint keywords → error:** `minLength`, `maxLength`, `format`, `minimum`, `maximum`, `exclusiveMinimum/Maximum`, `multipleOf`, `minItems`, `maxItems`, `uniqueItems`, `pattern`, `minProperties`, `maxProperties`, etc.
- Type literals: **`OBJECT()` empty is not allowed**; unsupported SQL types include **VARIANT, MAP, and date/time** types.
- `$ref` allowed only **within your schema** under `$defs` (no external/HTTP refs).
- **OpenAI (GPT) models only:** `additionalProperties: false` on every node and `required` must list every property.
- **Set `temperature = 0`** for the most consistent JSON. For medium/complex tasks, also add "Respond in JSON" to the prompt.

---

## 3. AI_CLASSIFY — beyond the basics
- **`output_mode`**: `'single'` (default) or `'multi'` (multi-label).
- **Up to 500 labels** (the newer AI_CLASSIFY; the legacy `CLASSIFY_TEXT` was single-label / 100 categories). Accuracy tends to drop past ~20 categories in practice.
- **Categories are case-sensitive.** Input text is case-sensitive too.
- **`task_description`** ≤ **50 words**; per-label **`description`** ≤ **25 words**; both count as input tokens (cost).
- **Few-shot `examples`** (input + labels + explanation) improve accuracy.
- **Documents:** `output_mode` **must be `'single'`** and **`examples` is not supported**. Doc limits: 100 pages, 200k tokens, 22 MB.
- Requires **CORTEX_USER**.

---

## 4. Cortex Search — CREATE + query internals

### CREATE CORTEX SEARCH SERVICE params
| Param | Default / note |
|---|---|
| `EMBEDDING_MODEL` | default **`snowflake-arctic-embed-m-v1.5`**; **can't be altered** after create (must CREATE OR REPLACE). |
| `REFRESH_MODE` | default **INCREMENTAL** (needs **change tracking** on base objects); can't be altered after create. |
| `INITIALIZE` | `ON_CREATE` (default, synchronous first build) or `ON_SCHEDULE` (populated at next refresh). |
| `TARGET_LAG` | must be **shorter than the source's data-retention period**, else the service can't detect changes. |
| `AUTO_SUSPEND` | minimum **1800 seconds (30 min)**; default NULL (disabled). |
| `ATTRIBUTES` | columns you can **filter** on at query time (must be in the source query). |
| `PRIMARY KEY` | enables an **optimized (cheaper/faster) refresh path**; TEXT columns only; tune with `FULL_INDEX_BUILD_INTERVAL_DAYS` (default 1). |
| Warehouse | use **no larger than MEDIUM**; a dedicated warehouse is recommended. |

### Multi-index services
- Syntax: `TEXT INDEXES col, ...` + `VECTOR INDEXES col(model='...'), ...`.
- **At least one VECTOR index is required** (text-only errors). Querying only text indexes in a multi-index query is an error.
- Behavior: **AND across fields**, **OR across terms** within a text field. Text queries are stemmed/lemmatized.

### Scoring / reranking
- **Reranking is ON by default.** Disable per query with `scoring_config: { "reranker": "none" }`.
- Disabling reranking cuts latency **~100–300 ms** but can reduce relevance — evaluate before disabling.
- Tune with `weights` (texts/vectors/reranker — relative), `numeric_boosts`, `time_decays` (with `limit_hours`), `text_boosts`/`vector_boosts`, `diversity`, and **named scoring profiles** (`ALTER … ADD SCORING PROFILE`).

### Filter operators
`@eq`, `@contains` (array), `@gte`, `@lte`, `@primarykey`; compose with `@and` / `@or` / `@not`.

### Security model — **owner's rights** (very high-yield)
Cortex Search runs with **owner's rights**. **Any role with USAGE on the service can retrieve every row the service indexed**, regardless of that role's privileges on the underlying tables/views — even rows behind row-access/masking policies the querying role couldn't otherwise read. **Grant USAGE on a search service carefully.**

### Access to build/query
- **Build:** `CREATE CORTEX SEARCH SERVICE` + SELECT on source + USAGE on warehouse, and **CORTEX_USER or CORTEX_EMBED_USER** (embedding privilege).
- **Query:** USAGE on the service + its DB + schema.
- Response size limits: REST/Python **10 MB**; SQL `SEARCH_PREVIEW` **300 KB** (preview/testing only, string literals, higher latency).

---

## 5. Cortex Analyst / Semantic Views — advanced

- **Semantic views** (schema-level objects) are **recommended** over legacy stage-based YAML models. Benefits: native RBAC, sharing, catalog, **derived metrics**, **access modifiers**.
- **Verified queries (VQR)** must reference the **logical** table/column names, with the logical table prefixed by **two underscores** (e.g. `FROM __sales_data`) — not the physical column names. `use_as_onboarding_question: true` surfaces it as a suggestion.
- **Custom instructions:** the single `custom_instructions` string is **legacy** — migrate to **`module_custom_instructions`** with two components:
  - `sql_generation` — how SQL is written (formatting, default filters).
  - `question_categorization` — classify/block questions or ask for missing details (e.g., mark UNCLEAR). Via an **Agent**, write these in plain language (no `UNCLEAR` keyword needed).
- **Dimension → Cortex Search** (`cortex_search_service` with `literal_column`) helps Analyst **resolve dimension literal values** (entity resolution). Replaces the deprecated `cortex_search_service_name`.
- **Access modifiers:** facts/metrics can be `public_access` (default) or **`private_access`** (hidden from queries; intermediate calcs only).
- **Semantic views don't need `join_type`/`relationship_type`** — relationship type is inferred. Support ASOF/range relationships, role-playing tables, bridge (many-to-many), variables, `max_staleness` for materializations (min 120s).
- Enable with `ENABLE_CORTEX_ANALYST = TRUE` + CORTEX_USER; USAGE on the view + warehouse.

---

## 6. Governance / Access — precise mechanics

### Two things needed to call AI functions
1. Account privilege **`USE AI FUNCTIONS`** (on PUBLIC by default), **AND**
2. a database role: **`SNOWFLAKE.CORTEX_USER`** *or* **`SNOWFLAKE.AI_FUNCTIONS_USER`**.

### Cortex database roles
| Role | Grants | Default on PUBLIC? |
|---|---|---|
| `CORTEX_USER` | All covered Cortex AI features | **Yes** |
| `AI_FUNCTIONS_USER` | Scalar AI functions only (no Cortex services) | No |
| `CORTEX_AGENT_USER` | Agents only | No |
| `CORTEX_EMBED_USER` | Embeddings + build Search w/ managed embeddings | No |

- **Database roles can't be granted directly to users** — grant to a custom account role, then to the user.

### Model access control (two mechanisms, OR relationship)
- **RBAC (recommended):** base models are objects in **`SNOWFLAKE.MODELS`** (refresh daily; `CALL SNOWFLAKE.MODELS.CORTEX_BASE_MODELS_REFRESH()`). Snowflake creates **application roles** per model, e.g. `SNOWFLAKE."CORTEX-MODEL-ROLE-LLAMA3.1-70B"` and `CORTEX-MODEL-ROLE-ALL`. Grant with `GRANT APPLICATION ROLE`.
- **Allowlist (legacy):** `ALTER ACCOUNT SET CORTEX_MODELS_ALLOWLIST = 'All'|'None'|'model-a,model-b'`. Account-level, ACCOUNTADMIN-only, **names case-sensitive lowercase**.
- **Interaction: OR** — access if RBAC USAGE **or** allowlist permits. To use RBAC exclusively, set allowlist to **'None'**. **ACCOUNTADMIN bypasses both** — test with a non-admin role + `USE SECONDARY ROLES NONE`.

### Cortex Agents — the default-role trap
Agents evaluate the querying user's **default role** (not the current session role) and require a **default warehouse**. Grants must be on the **default** role, over the agent, its DB/schema, the warehouse, and **every tool object** (search service, semantic view tables, custom functions).

### Cost / metering views (all in `SNOWFLAKE.ACCOUNT_USAGE`)
| View | Tracks |
|---|---|
| `METERING_HISTORY` | Hourly credits by service type |
| **`METERING_DAILY_HISTORY`** | **Daily** credits by service (`SERVICE_TYPE='AI_SERVICES'`) — the "daily AI cost" answer |
| `CORTEX_ANALYST_USAGE_HISTORY` | Analyst messages/credits by user |
| `CORTEX_AISQL_USAGE_HISTORY` | **Per-query** LLM function token usage |
| `CORTEX_SEARCH_DAILY_USAGE_HISTORY` | Search serving/token usage (daily) |
| `CORTEX_PROVISIONED_THROUGHPUT_USAGE_HISTORY` | PTU hours |

### Data safety, guardrails, redaction
- **AI_REDACT** = strip/mask **PII** before inference or storage.
- **Cortex AI Guardrails** (Horizon; `AI_SETTINGS`) = **prompt-injection / jailbreak** defense for agents/CoCo/CoWork. Monitor with `CORTEX_AI_GUARDRAILS_USAGE_HISTORY`.
- **Cortex Guard** (AI_COMPLETE `guardrails=TRUE`) = filter harmful **model output** (Llama Guard 3).
- **Cross-region:** payload transient (not persisted in processing region), encrypted in transit; **credits billed in the requesting region, no egress**; `CORTEX_ENABLED_CROSS_REGION` is ACCOUNT-level, ACCOUNTADMIN-only.
- **AI Observability:** **TruLens SDK** instruments the app; evaluates the **RAG Triad** (context relevance, groundedness, answer relevance) via LLM-as-judge; traces + metrics land in an **event table**.

---

## 7. Document processing — advanced

- **AI_PARSE_DOCUMENT modes:** **OCR** = plain text (fast, cheaper); **LAYOUT** = Markdown with **tables/headers preserved** and **required for image extraction** (`extract_images`).
- **AI_EXTRACT** = pull **specific fields** via a response schema (question→value). Choose Extract for fields, Parse LAYOUT for the whole document.
- **Limits:** ~**2,000 pages/doc**, ~100 MB; use **`page_split` / `page_filter`** to stay in bounds. `page_filter {start:0, end:2}` → indexes 0 and 1 = **first two pages** (end exclusive).
- **Warehouse no larger than MEDIUM** — bigger doesn't speed it up (billing is per page).
- **Pipelines:** **Stream** (CDC on the stage's directory table) captures new files; **Task** runs the parse/extract. Use `TRY_COMPLETE`-style resilience for batch.
- **Staged files:** `TO_FILE(...)` builds the FILE object; **`GET_PRESIGNED_URL`** creates a temporary access URL.
- **Fine-tuning:** improve domain-specific extraction by fine-tuning **`arctic-extract`** on labeled examples.
- **Encryption gotcha:** AI functions on FILE objects **don't work** on client-side-encrypted stages (`AWS_CSE`/`AZURE_CSE`), `SNOWFLAKE_FULL` internal encryption, user/table stages, or double-quoted stage names.

---

## 8. Vector functions — quick recap
- **Similarity (higher = closer):** `VECTOR_COSINE_SIMILARITY`, `VECTOR_INNER_PRODUCT`.
- **Distance (lower = closer):** `VECTOR_L2_DISTANCE`, `VECTOR_L1_DISTANCE`.
- Type is **`VECTOR(type, dim)`** — dimensions **must match** to compare (e.g. can't compare 768-dim to 1024-dim). Use `VECTOR_TRUNCATE` to shorten deliberately, `VECTOR_NORMALIZE` for unit length.
- Cosine assumes normalized vectors; scores in `[-1, 1]`.

---

## 9. Subtopic quick-reference (1.1–4.4) — foundational facts the drill also tests

The sections above go deep on edge cases; this table backfills the **foundational** facts (mostly Domains 1–2) so this page alone answers every targeted-drill question.

### Domain 1
- **1.1 Cortex Fine-tuning** — customizes a base model on labeled data for a narrow task (cheaper/faster inference, better accuracy). Created with the **`FINETUNE`** function; requires the **`CREATE MODEL`** privilege. Distinct from RAG (which adds retrieved context at query time and does **not** change the model).
- **1.1 Principle** — data stays inside Snowflake's governance boundary and is **not used to train** the foundation models.
- **1.2 Context window** — max tokens (prompt + response) a model can consider; long docs must be **chunked** to fit. Exceeding it truncates/errors and raises latency/cost.
- **1.2 MCP (Model Context Protocol)** — open protocol to expose/consume tools and data; Cortex Agents can act as MCP **server/client** so internal + external tools interoperate.
- **1.2 REST auth** — Cortex REST APIs (Analyst, Agents, inference) authenticate via **PAT**, **key-pair JWT**, or **OAuth**.

### Domain 2
- **2.1 AI_FILTER** — returns TRUE/FALSE for a natural-language condition; use directly in a **`WHERE`** clause to filter rows by meaning.
- **2.1 Aggregates** — **`AI_AGG`** and **`AI_SUMMARIZE_AGG`** reduce many rows into one result (use with `GROUP BY`); usable with `AI_FUNCTIONS_USER` even without `CORTEX_USER`. **`SUMMARIZE`** is scalar (one value at a time).
- **2.1 Other task functions** — `AI_SIMILARITY` (compare two inputs), `AI_TRANSCRIBE` (audio→text), `AI_TRANSLATE`, `AI_SENTIMENT`. Prefer task-specific over hand-prompted `AI_COMPLETE` when they fit (cheaper, more accurate).
- **2.2 Chunking helpers** — **`SPLIT_TEXT_RECURSIVE_CHARACTER`** (generic, by characters with overlap) and **`SPLIT_TEXT_MARKDOWN_HEADER`** (splits along Markdown headers to preserve structure; pairs with AI_PARSE LAYOUT).
- **2.2 RAG order** — Parse → Chunk → Embed → Index/Serve (Cortex Search) → Retrieve top-k → Generate (AI_COMPLETE). Reranking (default on) reorders candidates for relevance.
- **2.3 Multi-turn chat** — the **messages array** carries conversation history; the LLM is **stateless**, so the app must resend prior turns each request.
- **2.3 Snowflake Intelligence** — the **no-code** business-user chat UI built on top of Cortex Agents + semantic models.
- **2.5 SPCS object order** — Docker **image** → **image repository** → **compute pool** (GPU for LLMs) → **service spec** (YAML) → **`CREATE SERVICE`** → call endpoint. Use for custom serving/GPUs.
- **2.5 Model Registry** — `registry.log_model(...)` creates a **versioned MODEL object**; call it for inference. Easiest governed deploy for standard models (no containers). Pick **SPCS** only when you need containers/GPUs/custom runtime.

### Domain 3
- **3.3 AI_COUNT_TOKENS** — estimate tokens for a prompt/model to forecast cost **before** running.
- **3.3 Provisioned Throughput (PTU)** — reserve dedicated inference capacity for **predictable cost/throughput** at high volume (vs pay-per-token). Track with `CORTEX_PROVISIONED_THROUGHPUT_USAGE_HISTORY`.
- **3.3 Cost attribution / control** — use **object tagging** + **usage quotas/budgets** to attribute and cap AI spend by team; minimize tokens (shorter prompts/outputs, smaller models); suspend idle **SPCS compute pools**.

### Domain 4
- **4.2 FILE objects** — **`TO_FILE(stage, path)`** builds the FILE input; the stage needs a **directory table** (enumerate via `DIRECTORY(@stage)`). **`GET_PRESIGNED_URL`** makes a temporary access URL.
- **4.2 Extraction workflow** — `AI_EXTRACT` (schema → specific fields) vs `AI_PARSE_DOCUMENT` LAYOUT (whole doc as Markdown w/ tables). Automate with **Stream (CDC on directory table) + Task**.
- **4.4 Optimize/troubleshoot** — ~2,000-page limit → **page_split/page_filter**; warehouse **≤ MEDIUM** (per-page billing); encrypted-stage blockers (CSE / SNOWFLAKE_FULL / user & table stages / quoted names); fine-tune **arctic-extract** for niche fields.

---

## 10. Reducing hallucinations — the Snowflake toolkit

"Which feature reduces hallucination?" is a recurring exam scenario. The answer is almost always **grounding**, not safety filtering.

### Grounding (primary defense — give the model facts)
- **RAG with Cortex Search** — retrieve relevant chunks and pass them to `AI_COMPLETE` so the answer is grounded in your data, not the model's memory. **This is the default "reduce hallucination" answer.**
- **Cortex Analyst on a semantic view** — grounds text-to-SQL in a governed business model (not the raw schema), so results reflect real definitions.
- **Verified Query Repository (VQR)** — admin-approved NL→SQL pairs Analyst reuses for trusted, consistent answers.
- **Custom / `module_custom_instructions`** — encode business definitions and rules so generation follows them.
- **Cortex Knowledge Extensions (CKE)** — ground agents on curated, provider-maintained knowledge.
- **Agent citations** — Cortex Agents return citations to source, making grounding auditable.

### Constrain the output
- **Structured Outputs** (`response_format` + `required` fields) — force schema-valid JSON, reducing free-form drift and fabricated fields.
- **`temperature = 0`** — deterministic, less "creative"/invented output.
- **Capable model choice** — stronger models hallucinate less on hard tasks.

### Improve retrieval quality
- **Semantic reranking** (Cortex Search, on by default) surfaces the most relevant chunks first, so the grounding context is better.

### Measure it
- **AI Observability + TruLens** — the **RAG Triad**; its **groundedness** metric specifically scores whether the answer is supported by retrieved context (LLM-as-judge), alongside context relevance and answer relevance. Use tracing to see which chunks were used.

### Trap (know the distinction)
- **Cortex Guard** (`guardrails=TRUE`, Llama Guard 3) filters **harmful output**; **Cortex AI Guardrails** (`AI_SETTINGS`) defend against **prompt injection/jailbreaks**. Both are **safety**, **not** factuality — do **not** pick them as the "reduce hallucination" answer. The correct lever is **RAG grounding** (and **VQR** for Analyst).

---

## Rapid-fire "exact answer" drill
- AI_COMPLETE max_tokens default? → **4096** (truncation cause).
- Can a prompt-object AI_COMPLETE take a JSON schema? → **No** (single-string only).
- Cortex Guard filters input or output? → **Output** (Llama Guard 3).
- Default Cortex Search embedding model? → **snowflake-arctic-embed-m-v1.5**.
- Default REFRESH_MODE? → **INCREMENTAL** (needs change tracking).
- AUTO_SUSPEND minimum for Search? → **1800 s**.
- Who can query all indexed Search rows? → any role with **USAGE** (owner's rights).
- RBAC vs allowlist? → **OR**; allowlist names **lowercase, case-sensitive**; ACCOUNTADMIN bypasses.
- Agent uses which role? → the user's **default** role (+ default warehouse).
- Daily AI credits view? → **METERING_DAILY_HISTORY** in ACCOUNT_USAGE.
- Per-query token usage view? → **CORTEX_AISQL_USAGE_HISTORY**.
- AI_CLASSIFY on a document: output_mode? → **single**, no examples.
- AI_PARSE mode for tables + images? → **LAYOUT**.
- Fine-tune model for extraction? → **arctic-extract**.
- VQR references which names? → **logical** (`__table`), not physical.
- Reduce hallucination — best lever? → **RAG grounding** (Cortex Search); **VQR** for Analyst. **Not** Cortex Guard/Guardrails (those are safety).
- Which metric scores hallucination? → **groundedness** (RAG Triad, TruLens/AI Observability).
