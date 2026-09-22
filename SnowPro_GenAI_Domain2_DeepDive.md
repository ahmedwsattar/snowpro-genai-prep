# Domain 2 Deep-Dive: Snowflake Gen AI Functions

> Content sourced from Snowflake documentation as of: 2026-08-24 (via `cortex search docs`)
> Exam: SnowPro Specialty: Gen AI (GES-C02)
> Domain weight: 38% (highest-weighted domain — master this first)

This domain tests whether you can pick the *right* Cortex AI function for a task, call it with correct syntax, force structured output, build a RAG retrieval pipeline (embed → store → search → generate), hold a multi-turn conversation, and bring your own model when a built-in one won't do.

---

## 2.1 AI_COMPLETE and the task-specific AI functions

**`AI_COMPLETE` is the general-purpose text/multimodal generation function** — the canonical replacement for the legacy `SNOWFLAKE.CORTEX.COMPLETE`. Everything else in the `AI_*` family is a *task-specialized* function that is easier to call and often cheaper/faster for its narrow job. On the exam, the trap is reaching for `AI_COMPLETE` with a hand-written prompt when a purpose-built function exists.

**Task-specific functions (know when each wins over AI_COMPLETE):**
- `AI_CLASSIFY` — assign text/images to one of a set of labels you provide.
- `AI_FILTER` — returns a boolean; use it in `WHERE`/`QUALIFY` to keep rows matching a natural-language condition.
- `AI_AGG` — aggregate a *column* of text and reason across all rows (not row-by-row).
- `AI_SUMMARIZE_AGG` — summarize across many rows.
- `AI_SIMILARITY` — semantic similarity between two inputs.
- `AI_SENTIMENT`, `SUMMARIZE`, `TRANSLATE`, `EXTRACT_ANSWER` — single-purpose task functions.

**Snowflake implementation:**
```sql
-- General generation: pick the model explicitly
SELECT AI_COMPLETE('claude-4-sonnet',
  'Write a one-sentence product tagline for a solar phone charger');

-- Task-specific is simpler than a COMPLETE prompt for classification
SELECT AI_CLASSIFY(review_text, ['positive','neutral','negative']) AS label
FROM reviews;

-- AI_FILTER used as a semantic WHERE clause
SELECT * FROM tickets
WHERE AI_FILTER(prompt('Is this ticket about a billing problem? {0}', body));
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Canonical function | `AI_COMPLETE` (legacy `SNOWFLAKE.CORTEX.COMPLETE` deprecated by end of 2026) |
| Model arg | Required first argument; supported models differ in cost/context window |
| `max_tokens` default | 4096, max 8192 (COMPLETE options) |
| `temperature` / `top_p` default | 0 (deterministic-leaning) |
| Privilege | `SNOWFLAKE.CORTEX_USER` database role |

---

## 2.2 Structured outputs (`response_format` / type literals)

**Structured output forces the model's response to conform to a JSON schema or SQL type**, so you skip brittle post-processing. AI_COMPLETE verifies each generated token against your structure. Two ways to specify it:

1. **`response_format`** — a JSON schema passed as a SQL sub-object (NOT a string) in the `options` argument.
2. **Type literals** — begin with the `TYPE` keyword using a SQL `OBJECT` as the top-level type. **Type literals are supported only for the single-string prompt form of AI_COMPLETE.**

**Snowflake implementation:**
```sql
-- response_format with a JSON schema (options object form)
SELECT AI_COMPLETE(
  'claude-4-sonnet',
  'Extract the customer name and order total from: John paid $42.50',
  {'response_format': {
      'type':'json',
      'schema': {'type':'object',
        'properties': {'name':{'type':'string'},'total':{'type':'number'}},
        'required':['name','total']}}}
);
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Every supported model | Supports structured output; stronger models = higher quality |
| `response_format` type | SQL sub-object, not a string |
| Type literals scope | Single-string prompt form only |
| Common exam trap | The **Prompt object** form (documents/images) **cannot** use `response_format` |

---

## 2.3 Vector data type, embeddings, and vector similarity functions

**Embeddings turn unstructured text/images into a `VECTOR` of floats** that preserves semantic similarity. Snowflake stores them in the native `VECTOR(type, dimension)` column type and compares them with vector similarity functions.

**Embedding functions (note the dimension in the name):**
- `EMBED_TEXT_768(model, text)` → `VECTOR(FLOAT, 768)`
- `EMBED_TEXT_1024(model, text)` → `VECTOR(FLOAT, 1024)`
- (`AI_EMBED` is the newer unified surface for text and images.)

**Similarity functions:**
- `VECTOR_COSINE_SIMILARITY` — cosine (most common for semantic search; higher = more similar).
- `VECTOR_INNER_PRODUCT`, `VECTOR_L2_DISTANCE` (lower distance = more similar).

**Snowflake implementation:**
```sql
-- 1. Store embeddings in a native VECTOR column
CREATE TABLE docs (id INT, chunk STRING, v VECTOR(FLOAT, 768));

INSERT INTO docs
SELECT id, chunk,
       SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', chunk)
FROM raw_chunks;

-- 2. Retrieve top-k most similar chunks to a query
SELECT chunk,
       VECTOR_COSINE_SIMILARITY(
         v, SNOWFLAKE.CORTEX.EMBED_TEXT_768('snowflake-arctic-embed-m', 'reset my password')
       ) AS score
FROM docs
ORDER BY score DESC
LIMIT 5;
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Column type | `VECTOR(<type>, <dimension>)` — dimension must match the embedding model |
| Dimension mismatch | Comparing vectors of different dimensions is an error |
| Cosine similarity | Higher value = more similar; L2 distance = lower is more similar |
| Trap | The embedding model used for the query MUST match the model used for stored chunks |

---

## 2.4 RAG pipeline mechanics: Cortex Search vs. hand-rolled vector search

**Retrieval-Augmented Generation = retrieve relevant context, then feed it to an LLM to ground the answer.** You can build the retrieval layer two ways, and the exam wants you to know the tradeoff:

- **Cortex Search Service (recommended):** a managed **hybrid (vector + keyword)** search engine. It handles embedding, indexing, index refresh, and quality tuning for you. Purpose-built as the RAG engine for chatbots and enterprise search over text.
- **Manual vector search:** you call `EMBED_TEXT_*` yourself, store vectors, and rank with `VECTOR_COSINE_SIMILARITY`. More control, but you own chunking, embedding, and refresh.

**RAG data-flow (managed path):**
```
Docs → [chunk] → CREATE CORTEX SEARCH SERVICE (auto-embeds + indexes)
     → query → SEARCH_PREVIEW / service returns top-k chunks
     → AI_COMPLETE(prompt + retrieved chunks) → grounded answer
```

**Snowflake implementation:**
```sql
-- Managed hybrid search service over a chunk table (auto refresh via TARGET_LAG)
CREATE OR REPLACE CORTEX SEARCH SERVICE support_search
  ON chunk                    -- the search (text) column
  ATTRIBUTES product, region  -- filterable columns
  WAREHOUSE = search_wh
  TARGET_LAG = '1 hour'
  AS (SELECT chunk, product, region FROM docs);
```

**Decision framework:**
| Scenario | Recommended Approach | Why |
|----------|---------------------|-----|
| Chatbot/RAG over PDFs or KB text | Cortex Search Service | Managed hybrid search, auto index refresh, no infra to tune |
| Fine-grained control of chunking/embedding/scoring | Manual `EMBED_TEXT_*` + `VECTOR_COSINE_SIMILARITY` | Full control of the retrieval math |
| Natural-language questions over **structured tables** | Cortex Analyst (not RAG) | Text-to-SQL over a semantic view, not document retrieval |

---

## 2.5 Multi-turn (conversational) completions

**`AI_COMPLETE`/`COMPLETE` retain NO state between calls.** To make a stateful chat, you pass the entire conversation history as an array of `{role, content}` objects in chronological order.

- Roles: `system` (optional, must be first and only one), `user`, `assistant`.
- Each round you resend prior turns → token count and cost grow every turn.

**Snowflake implementation:**
```sql
SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-4-sonnet',
  [ {'role':'system','content':'You are a terse SQL tutor.'},
    {'role':'user','content':'What is a semantic view?'},
    {'role':'assistant','content':'A modeled layer Cortex Analyst queries.'},
    {'role':'user','content':'Give one example.'} ],
  {'temperature':0.2});
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Statefulness | None — you must resend history each call |
| System prompt | At most one; must be first element |
| Cost implication | Grows per turn as history lengthens |

---

## 2.6 Bring-your-own model: Model Registry + SPCS

When a built-in Cortex model isn't enough, you host your own. The exam expects you to know the two building blocks:

- **Snowflake Model Registry** — logs/versions models (via `snowflake.ml`) as first-class schema objects; you then call them for inference.
- **Snowpark Container Services (SPCS)** — runs custom/large models (incl. GPU) in managed containers when a model can't run as a warehouse UDF.

**Decision framework:**
| Scenario | Approach | Why |
|----------|----------|-----|
| Common LLM task (generate, classify, embed) | Built-in `AI_*` / Cortex functions | No hosting; serverless |
| Custom or open-source model, moderate size | Model Registry + warehouse inference | Versioned, governed, SQL-callable |
| Large / GPU model or custom container | Model Registry + **SPCS** | Dedicated compute (incl. GPU) the warehouse can't provide |

---

## 2.X Decision Frameworks: which function?

| You need to… | Use |
|--------------|-----|
| Generate free-form or multimodal text | `AI_COMPLETE` |
| Force a JSON/typed response | `AI_COMPLETE` + `response_format` / type literal |
| Label rows into known categories | `AI_CLASSIFY` |
| Keep rows matching a fuzzy condition | `AI_FILTER` in `WHERE` |
| Reason across all rows of a column | `AI_AGG` / `AI_SUMMARIZE_AGG` |
| Embed text for semantic search | `EMBED_TEXT_768` / `EMBED_TEXT_1024` / `AI_EMBED` |
| Rank stored vectors by similarity | `VECTOR_COSINE_SIMILARITY` |
| Managed RAG retrieval over documents | Cortex Search Service |

---

## 2.Y Key Exam Traps for This Domain

1. **Prompt object cannot use `response_format`.** Structured output (`response_format`, and type literals) applies to the text/single-string prompt form. The document/image **Prompt object** form does not accept `response_format` — a very common distractor.
2. **Task function vs. AI_COMPLETE.** If a question describes classification, filtering, sentiment, or translation, the *best* answer is the task-specific function (`AI_CLASSIFY`, `AI_FILTER`, etc.), not a hand-written `AI_COMPLETE` prompt — even though COMPLETE *could* do it.
3. **Cortex Search is hybrid, and it's for unstructured text.** Don't confuse it with Cortex Analyst. Search = fuzzy/semantic retrieval over documents (RAG). Analyst = text-to-SQL over structured tables via a semantic view.
4. **Embedding model must match.** Query embeddings and stored chunk embeddings must come from the *same* model and dimension, or similarity is meaningless / errors on dimension mismatch.
5. **COMPLETE is stateless.** Multi-turn chat requires resending the full history array; there is no server-side session. Cost rises each turn.
6. **`SNOWFLAKE.CORTEX_USER` is the gating role.** Without it, every AI function call fails regardless of table privileges. Users also need READ on stages/files for document inputs.

---

## Quick Reference Links

- [AI_COMPLETE (Single string)](https://docs.snowflake.com/en/sql-reference/functions/ai_complete-single-string)
- [AI_COMPLETE structured outputs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/complete-structured-outputs)
- [AI_COMPLETE with documents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-complete-document-intelligence)
- [Vector Embeddings](https://docs.snowflake.com/en/user-guide/snowflake-cortex/vector-embeddings)
- [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview)
- [COMPLETE (SNOWFLAKE.CORTEX) — chat/history](https://docs.snowflake.com/en/sql-reference/functions/complete-snowflake-cortex)
- [Official Exam Guide](https://learn.snowflake.com/en/certifications/) (search "SnowPro Specialty: Gen AI")
- [Schedule your exam](https://learn.snowflake.com/en/certifications/)
