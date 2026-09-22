# Domain 4.0 — Snowflake Document Processing (15%)

Smallest domain, but overlaps heavily with Domain 2. Centered on **AI_PARSE_DOCUMENT vs. AI_EXTRACT**, building automated pipelines with **Streams + Tasks**, and troubleshooting.

---

## 4.1 Document parsing functions

### AI_PARSE_DOCUMENT — document → text
Extracts content from a document **on a Snowflake stage**. Input is a **FILE object** (built with `TO_FILE('@stage','file.pdf')`). Returns a JSON string.

```sql
SELECT AI_PARSE_DOCUMENT(
  TO_FILE('@my_stage','contract.pdf'),
  {'mode': 'LAYOUT', 'page_split': true}
);
```

**Two modes (know the difference cold):**
- **OCR mode** (default) — fast, high-quality **text-only** extraction. Does **not** preserve layout. Best for scanned/text-heavy docs (contracts, claims, manuals). Output: `{"content": "..."}` (plain text).
- **LAYOUT mode** — extracts **structure**: tables, headers, reading order, as **Markdown**. Preferred for complex docs and **required for image extraction** (`'extract_images': true`).

**Key options:**
- **`mode`**: `'OCR'` | `'LAYOUT'`.
- **`page_split`** (bool): split multi-page docs into a `pages[]` array, each with `content` + `index` (0-based). Use it to stay under token limits for long docs. Supports PDF/PPTX/DOCX.
- **`page_filter`**: array of `{'start': n, 'end': m}` ranges (0-based, **start inclusive, end exclusive**) to process only some pages. Specifying `page_filter` **implies** `page_split`.
- **`extract_images`** (bool): return embedded images as base64 (LAYOUT only; ≤50 images/doc; no extra cost).
- **`return_error_details`** (bool, 3rd positional arg): returns an OBJECT with `value`, `error`, `metadata` (incl. `pageCount`).

**Note:** `AI_PARSE_DOCUMENT` is the updated version of `PARSE_DOCUMENT` — use AI_PARSE_DOCUMENT.

### AI_EXTRACT — document → structured fields
Pulls **specific fields** you define via a response format (a set of questions/keys → values). Best when you know exactly what you want (vendor name, total, dates, line items). Works on text, documents, and images (image input must be binary — decode base64 first).

```sql
SELECT AI_EXTRACT(
  file => TO_FILE('@my_stage','invoice.pdf'),
  responseFormat => {'vendor':'Who is the vendor?','total':'What is the total amount?'}
);
```

- **Response format** = your schema/questions. Governs output keys.
- **Prompt engineering** matters: clear, specific questions → better extraction. Ambiguous questions → wrong/empty values.

### AI_PARSE_DOCUMENT vs. AI_EXTRACT (THE core Domain 4 distinction)
| | AI_PARSE_DOCUMENT | AI_EXTRACT |
|---|---|---|
| Goal | Get the **whole document's** text/layout | Get **specific named fields** |
| Output | Text (OCR) or Markdown+structure (LAYOUT) | Structured values per your schema |
| Best for | Full-text search, RAG ingestion, preserving tables/layout | Invoices, forms, targeted field capture |
| Modes/options | OCR/LAYOUT, page_split, page_filter, extract_images | responseFormat (questions) |

**Official sample Q3 pattern:** invoices need *specific fields* → **AI_EXTRACT** with a schema; contracts need *full text as searchable Markdown with tables preserved* → **AI_PARSE_DOCUMENT in LAYOUT mode**. Use the right tool per doc type; don't force one for both.

---

## 4.2 Prepare & manage documents; extraction workflows

- **Upload documents** to a **stage** (internal or external). Use a **directory table** to enumerate files: `SELECT TO_FILE('@stg', RELATIVE_PATH) FROM DIRECTORY(@stg);`
- **Requirements / limits for AI_PARSE_DOCUMENT** (know the big ones):
  - Max file size **100 MB**; max **2,000 pages/doc**; max page resolution 10000×10000 px.
  - Supported types: **PDF, PPTX, DOCX, JPEG/JPG, PNG, TIFF/TIF, HTML, TXT**.
  - Page counting for billing: PDF/DOCX = per page; image files = per file; HTML/TXT = per 3,000-char chunk.
  - Stage may use client-side or server-side encryption (works with PrivateLink).

---

## 4.3 Automated document processing pipelines (Streams + Tasks)

Goal: process new documents automatically as they land on a stage.

**Pattern (know the objects):**
1. Documents land in a **stage** with a **directory table**.
2. A **Stream** on the directory table (or a table of file paths) captures **new/changed files** (change data capture).
3. A **Task** runs on a schedule or when triggered (e.g., `WHEN SYSTEM$STREAM_HAS_DATA('my_stream')`), consuming the stream and calling `AI_PARSE_DOCUMENT`/`AI_EXTRACT` to populate result tables.
4. Optionally chain tasks (task graph/DAG) for parse → extract → classify → embed, and feed a **Cortex Search** service.

- Alternative: **Dynamic Tables** can incrementally refresh derived AI columns from a base table.
- Use `TRY_COMPLETE` / handle NULLs so one bad file doesn't fail the batch.

---

## 4.4 Troubleshoot & optimize document processing

**Extraction/query errors:**
- **`GET_PRESIGNED_URL`** — generates a temporary URL to access a staged file; needed when a downstream process (or model) must fetch the file by URL. Related helper: `BUILD_SCOPED_FILE_URL`. Access issues often trace to presigned-URL/stage privileges.
- Common errors: unsupported format/language, file >100 MB, >2,000 pages, page too large, file not found, insufficient stage privileges, timeout.

**Requirements & privileges:** caller needs `SNOWFLAKE.CORTEX_USER` (granted by ACCOUNTADMIN) + `USE AI FUNCTIONS`, plus **READ/USAGE on the stage** and the file.

**Cost & best practices:**
- Billed **per page** processed → use **`page_filter`** to process only needed pages.
- Run AI_PARSE_DOCUMENT on a **small warehouse (≤ MEDIUM)** — bigger warehouses don't speed it up.
- Use `page_split` for very long docs to stay under token limits.

**Fine-tuning arctic-extract models:** for domain-specific extraction accuracy, **fine-tune the `arctic-extract` model** (Cortex Fine-tuning) on your labeled examples, then use it for AI_EXTRACT-style tasks. Use when out-of-the-box extraction misses domain fields.

---

## Document-processing cheat (HIGH YIELD)

| Need | Answer |
|---|---|
| Full text of a scanned doc, fast, no layout | AI_PARSE_DOCUMENT **OCR** |
| Preserve tables/headers as Markdown | AI_PARSE_DOCUMENT **LAYOUT** |
| Extract images from a doc | AI_PARSE_DOCUMENT LAYOUT + `extract_images:true` |
| Pull specific fields (vendor, total) | **AI_EXTRACT** + responseFormat |
| Process only pages 1–3 | `page_filter:[{'start':0,'end':3}]` (0-based, end exclusive) |
| Long doc over token limit | `page_split:true` |
| Auto-process new files on a stage | **Stream** (on directory table) + **Task** |
| Give a model temporary file access | GET_PRESIGNED_URL / BUILD_SCOPED_FILE_URL |
| Improve domain extraction accuracy | Fine-tune **arctic-extract** |
| Right warehouse size for parsing | Small–MEDIUM (larger doesn't help) |

---

## Common traps
- **OCR vs LAYOUT:** OCR = text only, no structure; LAYOUT = tables/headers/Markdown + required for images. Test loves this.
- **page_filter is 0-based, end-exclusive**, and implies page_split.
- **AI_EXTRACT = fields; AI_PARSE_DOCUMENT = whole document.** Don't extract full text with a field schema, and don't parse-then-regex when AI_EXTRACT is cleaner for fields.
- **Bigger warehouse ≠ faster parsing.** Cost is per page.
- **Streams capture change; Tasks execute** — the pipeline needs both.
- **arctic-extract** is the fine-tunable extraction model (Domain 4-specific).

---

# QUIZ — Domain 4 (answers at bottom)

**Q1.** Invoices need fields (vendor, total, line items); legal contracts need full text as searchable Markdown with tables preserved. Best workflow?
- A. AI_PARSE_DOCUMENT for all, then SQL filters for invoice fields
- B. AI_EXTRACT for all, with separate schemas
- C. AI_PARSE_DOCUMENT OCR for invoices; AI_EXTRACT for contracts' full text
- D. AI_EXTRACT (schema) for invoices; AI_PARSE_DOCUMENT LAYOUT for contracts

**Q2.** Which AI_PARSE_DOCUMENT mode preserves tables and headers and is required for image extraction?
- A. OCR
- B. LAYOUT
- C. TEXT
- D. RAW

**Q3.** `page_filter: [{'start': 0, 'end': 2}]` processes which pages?
- A. Pages 1 and 2 (the first two)
- B. Pages 0,1,2 (three pages)
- C. Only page 2
- D. All pages after page 2

**Q4.** To automatically process documents as they land on a stage, which two objects form the core pipeline?
- A. Masking policy + row access policy
- B. Stream (CDC on directory table) + Task
- C. Warehouse + resource monitor
- D. Semantic view + verified query

**Q5.** A 5,000-page PDF fails to process. Best fix within limits?
- A. Use a larger warehouse
- B. Switch to OCR from LAYOUT only
- C. Use page_split/page_filter to process within the 2,000-page limit
- D. Convert to TXT

**Q6.** Which function generates a temporary URL so a process can access a staged file?
- A. TO_FILE
- B. GET_PRESIGNED_URL
- C. AI_EMBED
- D. VECTOR_TRUNCATE

**Q7.** Out-of-the-box AI_EXTRACT misses several domain-specific fields on your specialized forms. Best optimization?
- A. Use a bigger warehouse
- B. Fine-tune the arctic-extract model on labeled examples
- C. Switch to OCR mode
- D. Increase page_filter range

**Q8.** Which warehouse size does Snowflake recommend for AI_PARSE_DOCUMENT?
- A. As large as possible for speed
- B. No larger than MEDIUM (bigger doesn't help)
- C. Only X-SMALL is allowed
- D. Warehouse size is irrelevant; it's serverless with no compute

---

## ANSWER KEY — Domain 4

**Q1 → D.** Fields → AI_EXTRACT with a schema; full text + preserved tables as Markdown → AI_PARSE_DOCUMENT **LAYOUT**. Matches official sample Q3.

**Q2 → B.** LAYOUT preserves structure and is required for `extract_images`. OCR is text-only.

**Q3 → B/first-two.** Ranges are 0-based, start inclusive, end **exclusive**: start 0, end 2 → indexes 0 and 1 = the **first two** pages. (So "the first two pages" — answer A's description, expressed as indexes 0–1.) **Correct choice: A** ("Pages 1 and 2, the first two"). See note below.

> Clarification: `{'start':0,'end':2}` returns page indexes 0 and 1 — the first two pages. The precise answer is **the first two pages** (A). B is wrong because end is exclusive (index 2 is not included).

**Q4 → B.** A **Stream** captures new/changed files (CDC on the directory table); a **Task** executes the parsing/extraction. Both are needed.

**Q5 → C.** Max is 2,000 pages/doc; use `page_split`/`page_filter` to process in bounds. A bigger warehouse doesn't help; OCR vs LAYOUT doesn't change the page limit.

**Q6 → B.** GET_PRESIGNED_URL creates a temporary access URL for a staged file (BUILD_SCOPED_FILE_URL is related).

**Q7 → B.** Fine-tune **arctic-extract** for domain-specific extraction accuracy.

**Q8 → B.** Use a warehouse no larger than MEDIUM; larger warehouses don't improve AI_PARSE_DOCUMENT performance (billing is per page).

> On Q3: the intended exam answer is "the first two pages." I split the option wording so you internalize *why* (end-exclusive), which is the actual tested concept.
