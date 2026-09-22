# Domain 1 Deep-Dive: Snowflake for Gen AI Overview

> Content sourced from Snowflake documentation as of: 2026-08-24 (via `cortex search docs`)
> Exam: SnowPro Specialty: Gen AI (GES-C02)
> Domain weight: 18% (foundational — the "which product do I pick?" domain)

This domain is about knowing what each Cortex product *is* and, above all, **when to choose one over another**. The exam leans hard on scenario questions: given a use case, pick Search vs. Analyst vs. Agents vs. Intelligence vs. a raw AI function.

---

## 1.1 The Cortex AI product family (what each one is)

Snowflake Cortex is a suite of LLM-powered features that run inside Snowflake's governed environment:

- **Cortex AI Functions** — SQL functions (`AI_COMPLETE`, `AI_CLASSIFY`, `EMBED_TEXT_*`, etc.) for row-level and aggregate AI over your data.
- **Cortex Search** — managed **hybrid (vector + keyword)** search over **unstructured text**; the RAG retrieval engine.
- **Cortex Analyst** — fully managed, LLM-powered **text-to-SQL** over your **structured** data via a semantic model/view; exposed as a REST API.
- **Cortex Agents** — a managed **agentic** platform: an agent reasons, plans, calls tools (Search + Analyst + custom), executes, and responds — no orchestration loop to build.
- **Snowflake Intelligence** — a no-code business-user chat experience built on top of agents/data.
- **Cortex Fine-tuning** — customize a base model on your data.

**Key details:**
| Product | Data type | Core job |
|---------|-----------|----------|
| AI Functions | any (rows) | Per-row/aggregate AI tasks in SQL |
| Cortex Search | unstructured text | Semantic/hybrid retrieval (RAG) |
| Cortex Analyst | structured tables | Natural-language → SQL answers |
| Cortex Agents | both | Multi-tool orchestration |
| Snowflake Intelligence | both | No-code chat UI for business users |

---

## 1.2 Cortex Search — retrieval over unstructured text

**Cortex Search powers low-latency, high-quality "fuzzy" search** over text in Snowflake, and is the standard RAG engine for LLM chatbots. It's a **hybrid** engine (vector + keyword) that handles embedding, indexing, and refresh for you, so you don't tune search infrastructure.

**When to use:** RAG chatbot over PDFs / a knowledge base, or enterprise search across documents.

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE kb_search
  ON chunk
  WAREHOUSE = search_wh
  TARGET_LAG = '1 hour'
  AS (SELECT chunk, source FROM kb_chunks);
```

---

## 1.3 Cortex Analyst — natural language over structured data

**Cortex Analyst answers business questions over structured tables** by generating text-to-SQL — no SQL from the user. It requires a **semantic model/semantic view** that defines tables, metrics, dimensions, and relationships so the LLM maps questions to correct SQL. It's delivered as a **REST API** you embed in apps.

**When to use:** "What were Q3 sales by region?" over governed tables — self-service analytics without writing SQL.

**Key details:**
| Aspect | Detail |
|--------|--------|
| Input data | Structured tables |
| Requires | A semantic model / semantic view |
| Interface | REST API |
| Output | Generated SQL + answer |

---

## 1.4 Cortex Agents — orchestrating multiple tools

**Cortex Agents is a fully managed agentic platform.** An agent reasons over a request, plans, calls tools, executes code, and generates a response — without you building an orchestration loop, runtime, or sandbox. It brings **structured + unstructured** data into one governed workflow: it generates SQL over structured data using **Cortex Analyst** semantic views and retrieves from unstructured sources via **Cortex Search**. Data access is governed by Snowflake privileges and each tool's execution context.

**When to use:** A single assistant that must both query tables *and* search documents, choosing tools automatically.

---

## 1.5 Snowflake Intelligence — no-code business chat

**Snowflake Intelligence is the no-code, business-user-facing chat experience** built over your agents and data. Business users converse with their data; builders configure the agents/tools behind it. It's the "front door" UI, distinct from the Agents platform that does the orchestration.

---

## 1.X Decision Framework (memorize cold — this is most of the domain)

| Scenario | Pick | Why |
|----------|------|-----|
| Search unstructured docs / build a RAG chatbot over PDFs | **Cortex Search** | Managed hybrid retrieval engine for text |
| Natural-language questions over structured tables | **Cortex Analyst** | Text-to-SQL over a semantic view |
| One assistant that uses Search + Analyst + custom tools | **Cortex Agents** | Managed multi-tool orchestration |
| No-code chat UI for business users over your data | **Snowflake Intelligence** | Business-facing front end |
| Generate/transform text row-by-row in SQL | **AI Functions** (`AI_COMPLETE`, …) | Direct SQL AI tasks |
| Adapt a base model to your domain data | **Cortex Fine-tuning** | Custom model behavior |

---

## 1.Y Key Exam Traps for This Domain

1. **Search vs. Analyst is the #1 distractor.** Unstructured text/documents → Cortex **Search**. Structured tables / metrics → Cortex **Analyst**. If the scenario says "PDFs / knowledge base / support articles," it's Search; if it says "sales table / natural-language BI," it's Analyst.
2. **Analyst needs a semantic view.** Cortex Analyst can't do reliable text-to-SQL without a semantic model/view — a scenario lacking one is a setup step, not a reason to switch products.
3. **Agents vs. Intelligence.** Agents = the *orchestration platform* (reasons + calls tools). Snowflake Intelligence = the *no-code chat UI* on top. Don't answer "Intelligence" when the question is about tool orchestration logic.
4. **Cortex Search is hybrid, not pure vector.** It combines vector + keyword search; describing it as "vector-only" is wrong.
5. **Agents unify governed access.** Agent tool access is governed by Snowflake privileges and each tool's execution context — it doesn't bypass RBAC.

---

## Quick Reference Links

- [Snowflake AI and ML (product suite overview)](https://docs.snowflake.com/en/guides-overview-ai-features)
- [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview)
- [Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)
- [Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents)
- [Official Exam Guide](https://learn.snowflake.com/en/certifications/) (search "SnowPro Specialty: Gen AI")
- [Schedule your exam](https://learn.snowflake.com/en/certifications/)
