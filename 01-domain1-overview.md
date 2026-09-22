# Domain 1.0 — Snowflake for Gen AI Overview (18%)

Goal of this domain: know **what each Cortex product is** and **when to choose it**. Most Domain 1 questions are "which capability fits this scenario" — memorize the decision table at the end.

---

## 1.1 Snowflake's Gen AI principles and features

### Snowflake Cortex — the umbrella
Cortex is Snowflake's fully-managed AI layer. No infra to manage; models run inside Snowflake's governance/security boundary. Your data does not leave the Snowflake boundary to be trained on.

**Cortex Models & Functions** — Serverless LLM access via SQL/Python/REST. Two families:
- **General:** `AI_COMPLETE` (free-form generation, the workhorse).
- **Task-specific:** `AI_CLASSIFY`, `AI_EXTRACT`, `AI_SENTIMENT`, `AI_TRANSLATE`, `AI_SUMMARIZE_AGG`, etc. — optimized single-purpose functions.

**Cortex Fine-tuning** (customizes a base model on your labeled data) — cheaper/faster inference than prompting a large model for a narrow task; improves accuracy on domain-specific tasks. Created with the `FINETUNE` function / requires `CREATE MODEL` privilege.

**Cortex Search** — Managed **hybrid search** (vector semantic + keyword/lexical) service. This is the retrieval engine for **RAG** and the answer for "search across unstructured docs (PDFs)". Handles chunking-adjacent concerns, embedding, indexing, and low-latency serving for you.
- RAG use case: retrieve relevant chunks → feed to an LLM (`AI_COMPLETE`) as grounding context.
- Unstructured data use case: semantic search over document text.

**Cortex Analyst** — **Text-to-SQL** over **structured** data. Users ask natural-language questions; Analyst generates SQL grounded in a **semantic view/model** (not the raw schema). Exposed as a **REST API**. Improve accuracy with **Verified Queries (VQR)** and **Custom Instructions**.

**Cortex Agents** — Orchestration layer. An agent reasons over a request and calls **tools**: Cortex Search (unstructured), Cortex Analyst (structured), and custom tools (functions/stored procs). Use when a single question spans both structured + unstructured sources or needs multi-step tool use. Uses **MCP** to expose/consume tools.

### Cortex Code (developer tooling)
AI coding assistant for Snowflake development.
- **Cortex Code in Snowsight UI** — in-browser assistant.
- **Cortex Code CLI** — command-line agent (this tool). Has session management and CLI commands. Metered/billable (replaced the older free Snowflake Copilot assistant).

### Snowflake Copilot Inline (Public Preview)
Inline SQL assistant embedded in worksheets — natural-language-to-SQL help, backed by Cortex models/functions, and can leverage Cortex Search for RAG. (Legacy Copilot assistant is being superseded by Cortex Code.)

### Snowflake Intelligence
A **no-code, business-user chat experience** built on top of Cortex Agents. Point it at your agents/semantic models/search services and let non-technical users ask questions in natural language. Think "packaged UI over Agents," not a separate model.

### Interfaces to Cortex (know all three)
- **AI Studio** (Snowsight UI, e.g., Cortex Playground) — click-to-try, compare models.
- **SQL** — call `AI_COMPLETE(...)` etc. directly in queries.
- **REST API** — call Cortex Analyst / Agents / inference from applications.

### Bringing your own models into Snowflake
Two paths (know the distinction — heavy in Domain 2.5):
- **Snowflake Model Registry** — log a custom/open-source model as a versioned object in a schema, then call it for inference. Governed like any Snowflake object.
- **Snowpark Container Services (SPCS)** — run containerized models/services (Docker images) on Snowflake-managed compute pools. Use when you need full control of the runtime, GPUs, or a serving framework.

---

## 1.2 Gen AI capabilities in Snowflake

**Prompting** — Instructions to the LLM. Good prompts are specific, give context/examples (few-shot), and constrain output format. Poor prompts increase hallucination and token cost.

**Cortex AI functions**
- **Vector embeddings** — Text → numeric vector (`AI_EMBED` / `EMBED_TEXT_768` / `EMBED_TEXT_1024`). Similar meanings → nearby vectors. Foundation of semantic search/RAG.
- **Context window** — Max tokens a model can consider (prompt + response). Long docs must be **chunked** to fit; exceeding it truncates or errors. Bigger context = higher latency/cost.

**Cortex Search**
- **Multi-index queries** — query across multiple search services/indexes.
- **Access control requirements** — caller needs `CORTEX_USER` (or targeted role) **plus** USAGE on the search service and on the underlying DB/schema/table.
- **Different ways to use it** — SQL, Python, REST API, or as a tool inside a Cortex Agent.

**Cortex Analyst**
- **Semantic Views** — the governed business model (tables, relationships, dimensions, metrics, synonyms) Analyst uses to ground SQL generation.
- **Semantic Views Autopilot** — assisted generation of a semantic view from your tables.
- **YAML specification** — semantic models can be authored/edited as YAML.
- **Verified Query (VQR)** — admin-approved NL→SQL pairs that Analyst reuses for accuracy/trust.
- **Custom Instructions** — persistent guidance (business rules, definitions) applied to every request.

**Cortex Agents / Snowflake Intelligence** — see 1.1.

**Cross-region inference**
- Controlled by the **account-level** parameter **`CORTEX_ENABLED_CROSS_REGION`**. Only **ACCOUNTADMIN** can set it (via `ALTER ACCOUNT`); cannot be set at user/session level; cannot be set by ORGADMIN.
- Values: `ANY_REGION` (broadest), cloud-scoped (`AWS_GLOBAL`, `AZURE_GLOBAL`, `GCP_GLOBAL`), geo-scoped (`AWS_US`, `AWS_EU`, `AZURE_US`, ...), or `DISABLED` (home region only).
- Why it matters: many frontier models aren't in every region. Cross-region routing gives access to them.
- **Data residency:** customer data stays stored in your home region; only the transient inference payload is sent to the processing region and is **not persisted** there. Encrypted in transit (mTLS across clouds).
- **Billing:** credits are consumed in the **requesting** region; **no egress charges**.
- **Considerations:** added latency; not all features (e.g., some Cortex Search) supported in all regions.

**REST APIs** — Cortex Analyst, Agents, and inference are callable over REST for app integration. Auth via PAT, key-pair JWT, or OAuth.

**Model Context Protocol (MCP)** — Open protocol for exposing tools/data to agents. Cortex Agents can act as MCP servers/clients so external and internal tools interoperate.

**Cortex Knowledge Extensions (CKE)** — Marketplace-distributed knowledge (backed by a Cortex Search Service) that a provider shares so consumers' agents/LLMs can ground answers on that curated content. Access relies on the underlying Cortex Search Service's access control.

---

## Decision table — pick the right capability (HIGH YIELD)

| Scenario | Answer |
|---|---|
| Chatbot/search over unstructured PDFs/docs | **Cortex Search** |
| RAG retrieval engine | **Cortex Search** |
| NL questions over structured tables (text-to-SQL) | **Cortex Analyst** (+ semantic view) |
| One assistant that combines structured + unstructured + custom tools | **Cortex Agents** |
| No-code chat UI for business users | **Snowflake Intelligence** |
| Generate/summarize/translate text in SQL | **Cortex AI functions** (AI_COMPLETE, etc.) |
| Improve a model's accuracy on a narrow, repeated task | **Cortex Fine-tuning** |
| Run your own open-source/custom model, need GPUs/runtime control | **SPCS** |
| Register + serve a custom model as a governed object | **Model Registry** |
| Access a frontier model not in your region | Enable **cross-region inference** |
| AI coding help in terminal / Snowsight | **Cortex Code** (CLI / Snowsight) |

---

## Common traps
- **Search vs. Analyst:** Search = *unstructured* text retrieval; Analyst = *structured* text-to-SQL. Don't mix them up — this is tested constantly.
- **Agents vs. Intelligence:** Agents = the orchestration engine/API; Intelligence = the packaged no-code UI on top.
- **Cross-region parameter** is `CORTEX_ENABLED_CROSS_REGION`, ACCOUNT level, ACCOUNTADMIN only.
- Fine-tuning ≠ RAG. Fine-tuning changes the model; RAG adds retrieved context at query time. RAG is the go-to for "answer from my documents/knowledge."

---

# QUIZ — Domain 1 (answers at bottom)

**Q1.** A team wants business users to ask plain-English questions like "What were Q3 sales by region?" against governed fact/dimension tables. Which Cortex capability, and what must exist first?
- A. Cortex Search; a chunked document index
- B. Cortex Analyst; a semantic view/model
- C. AI_COMPLETE; a fine-tuned model
- D. Snowflake Intelligence; a compute pool

**Q2.** Which statement about `CORTEX_ENABLED_CROSS_REGION` is correct?
- A. It can be set per session by any user with CORTEX_USER
- B. It causes your customer data to be permanently stored in the processing region
- C. It is an account-level parameter set only by ACCOUNTADMIN, and credits are billed in the requesting region
- D. It is set by ORGADMIN at the organization level

**Q3.** An organization needs one assistant that can answer questions requiring both a query against sales tables AND retrieval from support PDFs, deciding which to use per question. Best fit?
- A. Cortex Analyst alone
- B. Cortex Search alone
- C. Cortex Agents
- D. AI_EMBED

**Q4.** You want to run a proprietary open-source LLM with a custom serving stack and GPU control inside Snowflake. Which is most appropriate?
- A. Snowpark Container Services
- B. Cortex Fine-tuning
- C. Cortex Analyst
- D. Verified Query Repository

**Q5.** Which pair correctly matches feature → purpose?
- A. Verified Query → controls which regions models run in
- B. Semantic View → grounds Cortex Analyst's text-to-SQL generation
- C. Cortex Search → converts natural language to SQL over tables
- D. MCP → a vector distance metric

**Q6.** A developer needs a no-code, business-user-facing chat experience built on top of existing agents and semantic models. Which product?
- A. Cortex Code CLI
- B. AI Studio
- C. Snowflake Intelligence
- D. Model Registry

---

## ANSWER KEY — Domain 1

**Q1 → B.** Cortex Analyst does text-to-SQL over structured data and requires a **semantic view/model** to ground generation. Search (A) is for unstructured retrieval; a compute pool (D) is SPCS infra, unrelated.

**Q2 → C.** It's account-level, ACCOUNTADMIN-only, cannot be set at user/session level, and not by ORGADMIN (rules out A, D). Customer data is **not** persisted in the processing region (rules out B). Credits bill in the requesting region.

**Q3 → C.** Cortex **Agents** orchestrate multiple tools (Analyst for structured + Search for unstructured) and choose per question. A single tool alone (A/B) can't span both; AI_EMBED (D) just makes vectors.

**Q4 → A.** SPCS runs containerized models with runtime/GPU control. Fine-tuning (B) customizes a managed base model but doesn't give you a custom serving stack; C/D are unrelated.

**Q5 → B.** Semantic View grounds Analyst. Verified Query improves Analyst accuracy (not region control), Cortex Search is unstructured retrieval (not text-to-SQL), MCP is a tool protocol (not a distance metric).

**Q6 → C.** Snowflake Intelligence is the no-code chat UI over agents/semantic models. Cortex Code (A) is developer tooling; AI Studio (B) is for trying/comparing models; Model Registry (D) stores models.
