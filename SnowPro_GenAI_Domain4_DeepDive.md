# Domain 4 Deep-Dive: Snowflake Document Processing

> Content sourced from Snowflake documentation as of: 2026-08-24 (via `cortex search docs` + docs.snowflake.com)
> Exam: SnowPro Specialty: Gen AI (GES-C02)
> Domain weight: 15% (smallest domain, but overlaps heavily with Domain 2 functions)

This domain is about turning documents in a stage into usable data: parse/OCR a whole document, extract specific fields, understand charts/layouts, and keep it fresh with an incremental pipeline (Streams + Tasks). The exam's favorite question here is **AI_PARSE_DOCUMENT vs. AI_EXTRACT vs. AI_COMPLETE**.

---

## 4.1 The `FILE` data type and stage inputs

Document functions read files from a stage via a **`FILE` object**, built with `TO_FILE('@stage','path')`. The caller needs **READ** on the stage plus the relevant Cortex privilege (`CORTEX_USER` / `USE AI FUNCTIONS`). Stages must use **server-side encryption**.

```sql
-- Reference a staged document as a FILE object
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@docs','contract.pdf'),
  {'mode':'OCR'}
);
```

---

## 4.2 `AI_PARSE_DOCUMENT` — full document → text/Markdown (OCR vs. LAYOUT)

**`AI_PARSE_DOCUMENT` converts an entire document into text/Markdown.** It returns a JSON object with metadata and page text. It has **two modes** — knowing the difference is the highest-yield fact in this domain:

- **`OCR` mode** — fast, high-quality **text** extraction from scanned or text-heavy docs (contracts, insurance claims, manuals). **Does NOT preserve layout.**
- **`LAYOUT` mode** — preferred for **most/complex** documents. Optimized for **structured content** — tables, headers, layout relationships — and returns Markdown. **Image extraction (`extract_images`) requires LAYOUT mode.**

**Snowflake implementation:**
```sql
-- OCR: plain text from a scanned doc
SELECT AI_PARSE_DOCUMENT(TO_FILE('@docs','scan.pdf'), {'mode':'OCR'});

-- LAYOUT: structure-aware Markdown, split per page, only pages 0-1
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@docs','research.pdf'),
  {'mode':'LAYOUT', 'page_split': TRUE, 'page_filter':[{'start':0,'end':1}]}
);

-- LAYOUT + extract embedded images (LAYOUT only)
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@docs','report.pdf'),
  {'mode':'LAYOUT', 'extract_images': TRUE}
);
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Output | JSON with metadata + page text (Markdown in LAYOUT) |
| `OCR` mode | Fast text extraction; layout NOT preserved |
| `LAYOUT` mode | Structure-aware (tables/headers), Markdown; preferred default |
| `extract_images` | LAYOUT mode only; up to 50 images/doc |
| `page_split` / `page_filter` | Split multi-page docs; process only chosen page ranges |
| Auto-detected | Tables and forms; handwriting; most serif/sans-serif fonts |

---

## 4.3 `AI_EXTRACT` — pull specific structured fields

**`AI_EXTRACT` returns specific fields you ask for** from a document (or text), as structured output — e.g., invoice number, total, vendor. Use it when you know *what* you want, versus `AI_PARSE_DOCUMENT` which gives you the *whole* document text.

```sql
SELECT AI_EXTRACT(
  file => TO_FILE('@docs','invoice.pdf'),
  responseFormat => {
    'invoice_number':'What is the invoice number?',
    'total':'What is the grand total?',
    'vendor':'Who is the vendor?'}
);
```

---

## 4.4 `AI_COMPLETE` with documents — reason over a doc

**`AI_COMPLETE` (Prompt object form)** takes a prompt plus a `FILE` and *reasons* over the document — chart Q&A, cross-page relationships, contextual summarization — and lets you **choose the model** (e.g., Claude, Gemini). Use it for interpretation/analysis, not raw extraction.

```sql
SELECT AI_COMPLETE(
  MODEL => 'claude-4-sonnet',
  PROMPT => PROMPT('Summarize the risk factors in {0}', TO_FILE('@docs','10k.pdf'))
);
```
> Trap: the Prompt object form does **not** support `response_format` (see Domain 2).

---

## 4.5 Incremental document pipelines (Streams + Tasks)

To keep parsed/extracted output fresh as new files land, build an **incremental pipeline**: a directory table (or stream) detects new files, and a **Task** (or dynamic table) processes only the new ones.

**Data-flow:**
```
Files land in @stage → [Directory table / Stream detects new files]
   → [Task runs AI_PARSE_DOCUMENT / AI_EXTRACT on new rows]
   → Parsed table → (optional) embed + CREATE CORTEX SEARCH SERVICE
```

```sql
-- Task processes only newly arrived documents on a schedule
CREATE OR REPLACE TASK parse_new_docs
  WAREHOUSE = etl_wh
  SCHEDULE = '60 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('docs_stream')
AS
  INSERT INTO parsed_docs
  SELECT relative_path,
         AI_PARSE_DOCUMENT(TO_FILE('@docs', relative_path), {'mode':'LAYOUT'})
  FROM docs_stream;
```

---

## 4.X Decision Framework: which document function?

| You need to… | Use | Why |
|--------------|-----|-----|
| Turn a whole document into text/Markdown | `AI_PARSE_DOCUMENT` | Full-document OCR/LAYOUT extraction |
| Preserve tables/headers/layout or extract images | `AI_PARSE_DOCUMENT` **LAYOUT** | Structure-aware; images require LAYOUT |
| Fast plain text from a scan | `AI_PARSE_DOCUMENT` **OCR** | Fast, no layout |
| Pull specific named fields | `AI_EXTRACT` | Targeted structured extraction |
| Interpret/summarize/answer questions about a doc (choose model) | `AI_COMPLETE` w/ FILE | Reasoning + model choice |
| Keep outputs fresh as files arrive | Streams + Tasks (or dynamic tables) | Incremental processing |

---

## 4.Y Key Exam Traps for This Domain

1. **OCR vs. LAYOUT.** OCR = fast text, **no layout**. LAYOUT = structure-aware (tables/headers), Markdown, and the **only** mode that supports `extract_images`. LAYOUT is the recommended default for complex docs.
2. **PARSE vs. EXTRACT vs. COMPLETE.** Parse = *whole* document to text. Extract = *specific fields*. Complete = *reason/interpret* (and pick the model). Matching the verb in the scenario to the function is the whole game.
3. **`extract_images` needs LAYOUT.** Requesting image extraction in OCR mode is invalid.
4. **`AI_COMPLETE` w/ documents can't use `response_format`.** For guaranteed structured fields from a doc, reach for `AI_EXTRACT` (or parse then structure), not the Prompt-object COMPLETE.
5. **Stage READ + encryption required.** Document functions need READ on the stage and server-side-encrypted stages; missing privileges/encryption is a common failure, not a syntax error.
6. **Freshness comes from Streams/Tasks, not the function.** The AI functions are one-shot; ongoing freshness is a pipeline concern (Streams + Tasks / dynamic tables).

---

## Quick Reference Links

- [Parsing documents with AI_PARSE_DOCUMENT](https://docs.snowflake.com/en/user-guide/snowflake-cortex/parse-document)
- [AI_PARSE_DOCUMENT (SQL reference)](https://docs.snowflake.com/en/sql-reference/functions/ai_parse_document)
- [AI_EXTRACT](https://docs.snowflake.com/en/sql-reference/functions/ai_extract)
- [AI_COMPLETE with documents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-complete-document-intelligence)
- [Official Exam Guide](https://learn.snowflake.com/en/certifications/) (search "SnowPro Specialty: Gen AI")
- [Schedule your exam](https://learn.snowflake.com/en/certifications/)
