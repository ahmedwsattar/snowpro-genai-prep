# SnowPro Specialty: Gen AI (GES-C02) — Study Companion

Built from the official study guide (Last Updated: April 30, 2026) and grounded against live Snowflake docs.

## What's in this folder

| File | Purpose |
|---|---|
| `00-START-HERE.md` | This file — exam facts, study plan, how to use the material |
| `01-domain1-overview.md` | Domain 1.0 notes + quiz (18%) |
| `02-domain2-functions.md` | Domain 2.0 notes + quiz (38%) |
| `03-domain3-governance.md` | Domain 3.0 notes + quiz (29%) |
| `04-domain4-documents.md` | Domain 4.0 notes + quiz (15%) |
| `05-link-index.md` | All doc/blog links from the guide, grouped by domain, with verified URLs |

Each domain file ends with a **quiz** (scenario-style, like the real exam) and a separate **answer key with explanations**. Try the quiz before reading the answers.

## Exam facts

- **Exam:** SnowPro Specialty: Gen AI
- **Format:** Scenario-based, interactive, and real-world multiple-choice questions
- **Prerequisites/audience:** 1+ years of Gen AI experience on Snowflake; Python proficiency helpful; SQL + data engineering assumed
- **Recert:** All SnowPro certs expire **2 years** after issue; recertify via Snowflake Continuing Education (eligible ILT courses or an equal/higher SnowPro cert). You must hold a valid cert to use the CE program.
- **Estimated guide study time:** 10–13 hours

## Domain weightings (memorize this)

| Domain | Weight | Priority |
|---|---|---|
| 1.0 Snowflake for Gen AI Overview | 18% | Foundational |
| **2.0 Snowflake Gen AI Functions** | **38%** | **Highest — spend the most time here** |
| 3.0 Snowflake Gen AI Governance | 29% | Second priority |
| 4.0 Snowflake Document Processing | 15% | Smallest, but overlaps with Domain 2 |

Domains 2 + 3 together are **67%** of the exam. Functions and governance are where the exam is won.

## Recommended study plan

**Session 1 — Foundation (Domain 1)**
Read `01-domain1-overview.md`. Goal: know what each Cortex product *is* and when to pick it (Search vs. Analyst vs. Agents vs. Intelligence). Take the quiz.

**Session 2 & 3 — Functions (Domain 2, the big one)**
Read `02-domain2-functions.md` in two passes:
- Pass A: the AI_* task functions and when to use each; AI_COMPLETE vs. task-specific; structured outputs.
- Pass B: vector functions, RAG pipeline mechanics (chunking, embedding, reranking), multi-turn chat, SPCS + Model Registry for BYO models.
Take the quiz after each pass.

**Session 4 — Governance (Domain 3)**
Read `03-domain3-governance.md`. Drill the database roles, the ACCOUNT_USAGE cost views, model access control (RBAC vs. allowlist), and AI Observability/TruLens. Take the quiz.

**Session 5 — Document Processing (Domain 4)**
Read `04-domain4-documents.md`. Focus on AI_PARSE_DOCUMENT (OCR vs. LAYOUT) vs. AI_EXTRACT, and Streams + Tasks pipelines. Take the quiz.

**Session 6 — Review + official practice**
- Re-take every quiz cold.
- Do the official sample questions (in the guide, also reproduced with explanations at the end of the domain files where relevant).
- Skim `05-link-index.md` and open any link on a topic you're still shaky on.

## High-yield "decision" cheat (know these cold)

- **Search unstructured docs / build a RAG chatbot over PDFs →** Cortex Search
- **Natural-language questions over structured tables (text-to-SQL) →** Cortex Analyst (needs a semantic view/model)
- **Orchestrate multiple tools (Search + Analyst + custom) in one agent →** Cortex Agents
- **No-code business chat UI over your agents/data →** Snowflake Intelligence
- **Generate free-form text from a prompt →** AI_COMPLETE
- **Extract structured fields from a doc →** AI_EXTRACT
- **Convert a whole doc to text/Markdown (OCR or layout) →** AI_PARSE_DOCUMENT
- **Daily AI credit consumption →** `SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY` (service type `AI_SERVICES`)

> Version note: This material was verified against Snowflake docs in 2026. The study guide lists a few role names loosely (e.g., "CORTEX_ANALYST_USER"). See `03-domain3-governance.md` for exactly which roles/parameters are real vs. how the guide phrases them — I flag the differences so you're not caught out.
