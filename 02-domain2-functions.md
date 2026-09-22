# Domain 2.0 — Snowflake Gen AI Functions (38%)

**The largest domain — spend the most time here.** Expect heavy questions on *which function to use*, structured outputs, vector functions, RAG pipeline mechanics, multi-turn chat, and running your own models (SPCS + Model Registry).

---

## 2.1 Cortex AI functions — the full catalog

All are callable in SQL (and most in Python). Access requires the `USE AI FUNCTIONS` account privilege **plus** a `CORTEX_USER` or `AI_FUNCTIONS_USER` database role (details in Domain 3).

### General
| Function | What it does |
|---|---|
| **AI_COMPLETE** | The workhorse. Free-form text generation from a prompt. Supports **structured outputs**, and multimodal input (text + image/file). Choose the model with the first arg. |
| **COMPLETE Structured Outputs** | Pass a `response_format` (JSON schema) so `AI_COMPLETE` returns valid, schema-conforming JSON instead of free text. Use when you need machine-parseable results. |

### Task-specific (prefer these over AI_COMPLETE when they fit — cheaper, more accurate, simpler)
| Function | Use it for |
|---|---|
| **AI_CLASSIFY** | Categorize text/images into your labels. Supports single or multi-label (`output_mode`). |
| **AI_EXTRACT** | Pull **structured fields** from text/documents/images via a response schema (question → value). Great for invoices, forms. |
| **AI_PARSE_DOCUMENT** | Convert a document on a stage to text (OCR) or Markdown+layout (LAYOUT). See Domain 4. |
| **AI_SENTIMENT** | Sentiment (and entity-level sentiment) of text. |
| **SUMMARIZE** / **AI_SUMMARIZE_AGG** | `SUMMARIZE` = summarize one value. `AI_SUMMARIZE_AGG` = **aggregate** summary across many rows (aggregate function; works without CORTEX_USER). |
| **AI_TRANSLATE** | Translate between languages. |
| **AI_EMBED** | Create a vector embedding from text (or image). Foundation of semantic search/RAG. |
| **AI_FILTER** | Returns TRUE/FALSE for a natural-language condition — use in `WHERE` to filter rows by meaning. |
| **AI_AGG** | Aggregate/reduce a column of text across rows with a natural-language instruction (aggregate function; no CORTEX_USER needed). |
| **AI_SIMILARITY** | Semantic similarity between two inputs (text or images). |
| **AI_TRANSCRIBE** | Speech/audio → text. |
| **AI_REDACT** | Redact PII/sensitive data from text (governance-relevant). |

> **Scalar vs. aggregate:** `AI_AGG` and `AI_SUMMARIZE_AGG` are the two **aggregate** functions and are usable with just `AI_FUNCTIONS_USER` (they work even without `CORTEX_USER`). Everything else is scalar (per-row).

### Vector functions (know what each computes)
Distance/similarity:
| Function | Meaning |
|---|---|
| **VECTOR_COSINE_SIMILARITY** | Cosine of angle; **higher = more similar**. Most common for semantic search. |
| **VECTOR_INNER_PRODUCT** | Dot product; higher = more similar (for normalized vectors ≈ cosine). |
| **VECTOR_L2_DISTANCE** | Euclidean distance; **lower = more similar**. |
| **VECTOR_L1_DISTANCE** | Manhattan (taxicab) distance; lower = more similar. |

Transforms/aggregates:
- **VECTOR_TRUNCATE** — shorten a vector to fewer dimensions.
- **VECTOR_NORMALIZE** — scale a vector to unit length.
- **VECTOR_SUM / VECTOR_MIN / VECTOR_MAX / VECTOR_AVG** — element-wise aggregations across vectors.

> Data type: **VECTOR(type, dimension)**, e.g. `VECTOR(FLOAT, 768)`. Embedding dimension must match the model.

### Helper functions
| Function | Use |
|---|---|
| **AI_COUNT_TOKENS** | Estimate tokens for a prompt/model → estimate cost before running. |
| **TRY_COMPLETE** | Like AI_COMPLETE/COMPLETE but returns NULL instead of erroring — safe for large batch jobs. |
| **SPLIT_TEXT_RECURSIVE_CHARACTER** | Chunk long text by characters with overlap — the standard chunker for RAG ingestion. |
| **SPLIT_TEXT_MARKDOWN_HEADER** | Chunk text along Markdown headers — preserves document structure (pairs well with AI_PARSE_DOCUMENT LAYOUT output). |
| **TO_FILE** | Build a FILE object from a stage path — required input for AI_PARSE_DOCUMENT and multimodal AI functions. |
| **PROMPT** | Helper to build a templated prompt object (e.g., for multimodal / structured calls). |

---

## 2.2 Perform data analysis given a use case

### Unstructured data
Function toolkit: **AI_PARSE_DOCUMENT** (get text), **AI_EXTRACT** (get fields), **AI_SIMILARITY** (compare), **AI_COMPLETE** (generate/answer).

**RAG pipeline pattern (memorize the flow):**
1. **Parse** docs → text/Markdown (`AI_PARSE_DOCUMENT`, LAYOUT for structure).
2. **Chunk** text (`SPLIT_TEXT_RECURSIVE_CHARACTER` or `SPLIT_TEXT_MARKDOWN_HEADER`). Chunk sizing matters: too big overflows context / dilutes relevance; too small loses meaning. Use overlap to preserve continuity.
3. **Embed** chunks (or let Cortex Search manage embeddings). Pick an **embedding model** whose dimension/quality fits your language + latency.
4. **Index/serve** with **Cortex Search** (hybrid vector + keyword). Cortex Search can add **semantic reranking** to reorder candidates for relevance.
5. **Retrieve** top-k chunks → build prompt → **AI_COMPLETE** to generate a grounded answer.

Key terms the guide calls out: *recursive split text/markdown*, *chunk sizing*, *embedding models*, *semantic reranking*.

**Multi-modal analytics:** AI functions handle **audio** (`AI_TRANSCRIBE`) and **images** (`AI_COMPLETE` multimodal, `AI_CLASSIFY`/`AI_SIMILARITY` on images, `AI_EXTRACT` on image files). `AI_COMPLETE` takes a FILE for image input; audio goes through AI_TRANSCRIBE first.

### Structured data
- **AI_COMPLETE** for generative tasks over row values.
- **Cortex Analyst** for text-to-SQL. Boost quality with:
  - **Verified Query Repository (VQR)** — curated NL→SQL pairs.
  - Integration with **Cortex Search** (semantic search over dimension values / help Analyst resolve entities).
  - **Suggested Questions** — surface example questions to users.
  - **CUSTOM_INSTRUCTIONS** — persistent business rules/definitions.

### Performance considerations (tested)
- **Choosing a model:** match capability to task. Small models = lower latency/cost; large/frontier models = higher quality on hard tasks. Don't use a 405B model for simple classification.
- **Latency** scales with model size and output length (tokens). Long context = slower.
- **Accuracy:** improve via **fine-tuning**, better prompts, and **RAG to reduce hallucinations** (ground answers in retrieved facts).
- **Model capability:** not every model supports every feature/region/modality.
- **Provisioned Throughput (PTU):** reserve dedicated inference capacity for predictable, high-volume workloads (vs. pay-per-token on-demand). Requires `CREATE PROVISIONED THROUGHPUT` privilege.

---

## 2.3 Build/interact with interfaces to chat with data

**Environment setup — required privileges:** caller needs `USE AI FUNCTIONS` + `CORTEX_USER` (or targeted role) to call functions; USAGE on any search service / semantic view / warehouse used; and for Analyst, the `ENABLE_CORTEX_ANALYST` account parameter must be TRUE.

**Invoke Cortex in app code (e.g., Streamlit in Snowflake):**
- Call `AI_COMPLETE`/Analyst REST API from the app.
- **Multi-turn chat architecture:** maintain a **messages array** (conversation history: system/user/assistant turns) and pass it on each request. The model has no memory between calls — **history in the messages array is what preserves context**. This is the single most-tested chat concept (matches official sample Q2).
- Update parameters between turns: append the latest user/assistant messages so context accumulates; trim old turns when you approach the context window.

**Snowflake Intelligence** — the no-code path to the same thing for business users.

---

## 2.4 Apply Cortex functions in data pipelines

Cortex functions are just SQL — drop them into ELT/pipelines:
- **Data extraction** — AI_EXTRACT / AI_PARSE_DOCUMENT to pull fields/text from raw docs.
- **Data enrichment** — add sentiment, classification, translations, embeddings as new columns.
- **Data augmentation** — generate summaries/synthetic fields with AI_COMPLETE.
- **Data transformations** — AI_FILTER in WHERE, AI_AGG/AI_SUMMARIZE_AGG in GROUP BY.
- Combine with **Streams + Tasks** (or Dynamic Tables) to run continuously as new rows/files land (see Domain 4). Use `TRY_COMPLETE` for resilient batch jobs.

---

## 2.5 Run third-party / your own models in Snowflake

### Option A — Snowpark Container Services (SPCS)
For full runtime control (custom frameworks, GPUs). Setup steps (know the order):
1. **Environment setup** — role/privileges, database/schema.
2. **Docker image** — containerize the model/serving code.
3. **Image repository** — `CREATE IMAGE REPOSITORY`; push the image to it.
4. **Compute pool** — `CREATE COMPUTE POOL` (choose instance family; GPU pools for LLMs).
5. **Specification file** — YAML service spec (containers, endpoints, resources).
6. **Create service** — `CREATE SERVICE` from the spec on the compute pool; call its endpoint.

Use SPCS for fine-tuning open-source LLMs (e.g., AutoTrain) and for serving models Cortex doesn't host.

### Option B — Snowflake Model Registry
For logging/serving models as governed Snowflake objects (schema-level).
1. **Log the model** — `registry.log_model(...)` (Python) creates a versioned MODEL object.
2. **Call the model** — invoke its methods for inference (`model_ref.run(...)` / SQL). Registry handles versioning and dependency packaging.

**When to pick which:** Registry = easiest path to deploy/version a model (esp. Python ML/LLMs that fit the managed runtime). SPCS = when you need containers, custom serving, or GPU-heavy workloads beyond the managed runtime.

---

## Function-selection cheat (HIGH YIELD)

| Need | Function |
|---|---|
| Free-form text / answer a prompt | AI_COMPLETE |
| Machine-parseable JSON out of an LLM | AI_COMPLETE + response_format (Structured Outputs) |
| Bucket into categories | AI_CLASSIFY |
| Pull named fields from text/doc | AI_EXTRACT |
| Doc → text/Markdown | AI_PARSE_DOCUMENT |
| Filter rows by meaning | AI_FILTER (in WHERE) |
| Summary across many rows | AI_SUMMARIZE_AGG / AI_AGG |
| Translate | AI_TRANSLATE |
| Sentiment | AI_SENTIMENT |
| Audio → text | AI_TRANSCRIBE |
| Redact PII | AI_REDACT |
| Make embeddings | AI_EMBED |
| Compare two texts semantically | AI_SIMILARITY |
| Estimate cost before running | AI_COUNT_TOKENS |
| Batch job that must not fail per-row | TRY_COMPLETE |
| Chunk long text for RAG | SPLIT_TEXT_RECURSIVE_CHARACTER / _MARKDOWN_HEADER |
| Most-similar vector search | VECTOR_COSINE_SIMILARITY (higher = closer) |

---

## Common traps
- **Task-specific over AI_COMPLETE:** if AI_CLASSIFY/AI_EXTRACT/AI_TRANSLATE fits, prefer it — cheaper and more accurate than a hand-prompted AI_COMPLETE.
- **Cosine/inner-product: higher = closer. L1/L2 distance: lower = closer.** Easy to flip under exam pressure.
- **Multi-turn memory = the messages array**, not a server-side session. The LLM is stateless.
- **AI_EXTRACT vs. AI_PARSE_DOCUMENT:** Extract = *specific fields* (schema); Parse = *the whole document's text/layout*. (Central to Domain 4 too.)
- **SPCS vs. Model Registry:** containers/GPUs/custom serving → SPCS; log-and-serve a model object → Registry.
- **Provisioned Throughput** = reserved capacity for cost/latency predictability at scale, not a model or a function.

---

# QUIZ — Domain 2 (answers at bottom)

**Q1.** You must return strictly valid JSON (fixed fields: `risk_level`, `reason`) from an LLM so a downstream job can parse it. Best approach?
- A. AI_COMPLETE with a structured output `response_format` schema
- B. AI_SENTIMENT
- C. SUMMARIZE
- D. AI_FILTER

**Q2.** In semantic search you compute `VECTOR_COSINE_SIMILARITY` between a query embedding and document embeddings. To get the best matches you order by:
- A. similarity ASC (smallest first)
- B. similarity DESC (largest first)
- C. L2 distance DESC
- D. it doesn't matter

**Q3.** A nightly job runs an LLM over millions of rows; a few malformed rows shouldn't abort the whole query. Which function?
- A. AI_COMPLETE
- B. TRY_COMPLETE
- C. AI_AGG
- D. PROMPT

**Q4.** Which correctly orders the RAG ingestion steps?
- A. Embed → Parse → Chunk → Retrieve → Generate
- B. Parse → Chunk → Embed → Index/Serve → Retrieve → Generate
- C. Chunk → Generate → Embed → Parse
- D. Retrieve → Parse → Generate → Embed

**Q5.** A data scientist has a trained Python model and wants to deploy it as a versioned, governed Snowflake object callable for inference, without managing containers. Best fit?
- A. Snowpark Container Services
- B. Snowflake Model Registry
- C. Cortex Analyst
- D. Provisioned Throughput

**Q6.** What is the primary role of the messages array in a multi-turn Cortex chat app?
- A. To store user credentials securely
- B. To speed up response generation
- C. To maintain conversation context across turns (the model is otherwise stateless)
- D. To cap tokens per request

**Q7.** You need to filter a table to only rows whose free-text `feedback` expresses a complaint about shipping. Most direct?
- A. AI_FILTER in the WHERE clause
- B. AI_EMBED then manual thresholding
- C. AI_TRANSLATE
- D. VECTOR_L1_DISTANCE

**Q8.** A team runs a GPU-heavy open-source LLM with a custom serving framework inside Snowflake. Which setup objects are involved?
- A. Semantic view + verified query
- B. Compute pool + image repository + service spec (SPCS)
- C. Cortex Search service + reranker
- D. ENABLE_CORTEX_ANALYST parameter

**Q9.** Which is an **aggregate** Cortex function usable even without the CORTEX_USER role?
- A. AI_COMPLETE
- B. AI_CLASSIFY
- C. AI_SUMMARIZE_AGG
- D. AI_TRANSLATE

**Q10.** For a high-volume, latency-sensitive production workload needing predictable inference cost/throughput, you should consider:
- A. A larger warehouse
- B. Provisioned Throughput
- C. VECTOR_NORMALIZE
- D. Disabling cross-region inference

---

## ANSWER KEY — Domain 2

**Q1 → A.** Structured Outputs: pass a JSON schema as `response_format` to AI_COMPLETE so it returns schema-valid JSON. Sentiment/summarize/filter don't produce arbitrary structured fields.

**Q2 → B.** Cosine similarity: **higher = more similar**, so order DESC. (For L1/L2 distance you'd order ASC.)

**Q3 → B.** TRY_COMPLETE returns NULL on failure instead of erroring — resilient batch processing. AI_COMPLETE would abort on a bad row.

**Q4 → B.** Parse → Chunk → Embed → Index/Serve (Cortex Search) → Retrieve top-k → Generate (AI_COMPLETE).

**Q5 → B.** Model Registry logs/serves a versioned model object with no container management. SPCS (A) is for containers/custom serving; Analyst/PTU are unrelated.

**Q6 → C.** The messages array carries conversation history so context persists; the LLM itself is stateless. (Matches official sample question 2.)

**Q7 → A.** AI_FILTER evaluates a natural-language condition to TRUE/FALSE and can be used directly in WHERE.

**Q8 → B.** SPCS uses a **compute pool**, **image repository** (Docker image), and a **service spec** to create the service. The others are unrelated products.

**Q9 → C.** AI_SUMMARIZE_AGG (and AI_AGG) are the aggregate functions and work with AI_FUNCTIONS_USER even without CORTEX_USER. The rest are scalar and need CORTEX_USER (or AI_FUNCTIONS_USER + are non-aggregate).

**Q10 → B.** Provisioned Throughput reserves dedicated capacity for predictable throughput/cost at scale. A bigger warehouse doesn't change LLM inference throughput.
