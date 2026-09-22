# Domain 3 Deep-Dive: Snowflake Gen AI Governance

> Content sourced from Snowflake documentation as of: 2026-08-24 (via `cortex search docs` + docs.snowflake.com)
> Exam: SnowPro Specialty: Gen AI (GES-C02)
> Domain weight: 29% (second-highest — heavy on privileges, model access, cost, and evaluation)

This domain tests access control for AI functions, how model access is governed (RBAC vs. the deprecating allowlist), safety guardrails, cost tracking, and how you *evaluate* an AI app (AI Observability / TruLens, the RAG Triad). **The privilege model changed recently — memorize the current rules below; older study notes are out of date here.**

---

## 3.1 Access control for Cortex AI Functions (the current model)

**Calling any Cortex AI function requires TWO things together:**
1. The **`USE AI FUNCTIONS`** account-level privilege (or a per-function `USE AI FUNCTION <name>` privilege), AND
2. One of the database roles **`CORTEX_USER`** or **`AI_FUNCTIONS_USER`**.

Both defaults land on `PUBLIC`: `USE AI FUNCTIONS` and `CORTEX_USER` are granted to `PUBLIC` by default, so all users can call AI functions until you revoke.

**The database roles differ in scope:**
- **`SNOWFLAKE.CORTEX_USER`** — full Cortex AI functions + Cortex services (Search, Analyst, Agents, Fine-tuning). Granted to `PUBLIC` by default.
- **`SNOWFLAKE.AI_FUNCTIONS_USER`** — **scalar AI functions only** (everything *except* the aggregates `AI_AGG` and `AI_SUMMARIZE_AGG`), and **no** access to Cortex services. NOT granted to PUBLIC by default.
- **`SNOWFLAKE.CORTEX_EMBED_USER`** — only the embedding functions (`AI_EMBED`, `EMBED_TEXT_768`, `EMBED_TEXT_1024`) and creating Search Services with managed embeddings. NOT on PUBLIC by default.

**Snowflake implementation:**
```sql
USE ROLE ACCOUNTADMIN;

-- Lock down: remove blanket access from everyone
REVOKE USE AI FUNCTIONS ON ACCOUNT FROM ROLE PUBLIC;
REVOKE DATABASE ROLE SNOWFLAKE.CORTEX_USER FROM ROLE PUBLIC;

-- Grant to a purpose-built role instead
CREATE ROLE cortex_user_role;
GRANT USE AI FUNCTIONS ON ACCOUNT TO ROLE cortex_user_role;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE cortex_user_role;
GRANT ROLE cortex_user_role TO USER example_user;
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Two-part requirement | `USE AI FUNCTIONS` (account) **AND** `CORTEX_USER`/`AI_FUNCTIONS_USER` (db role) |
| Default grants | Both `USE AI FUNCTIONS` and `CORTEX_USER` → PUBLIC |
| Special case | With `USE AI FUNCTIONS` but **no** `CORTEX_USER`, a user can still call `AI_AGG` and `AI_SUMMARIZE_AGG` |
| DB roles → users | Cannot be granted directly to a user; grant to a role, then role to user |
| Native apps | `USE AI FUNCTIONS` does not currently apply to AI calls inside native apps |

---

## 3.2 Per-function privileges (the OR relationship)

You can grant **`USE AI FUNCTION <name>`** for individual functions instead of the blanket privilege. The blanket and per-function privileges have an **OR** relationship:

- Has `USE AI FUNCTIONS` → can call **all** functions, regardless of per-function grants/revokes.
- Has only `USE AI FUNCTION AI_COMPLETE` → can call only `AI_COMPLETE`.
- Per-function still requires the `CORTEX_USER`/`AI_FUNCTIONS_USER` database role.

**Snowflake implementation:**
```sql
USE ROLE ACCOUNTADMIN;
REVOKE USE AI FUNCTIONS ON ACCOUNT FROM ROLE PUBLIC;

CREATE ROLE ai_complete_user_role;
GRANT USE AI FUNCTION AI_COMPLETE ON ACCOUNT TO ROLE ai_complete_user_role;
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE ai_complete_user_role;
GRANT ROLE ai_complete_user_role TO USER example_user;
```

**Key exam point:** If a role has *both* the blanket and a per-function grant, revoking the per-function grant does **not** cut access — the blanket privilege still applies.

---

## 3.3 Controlling model access: RBAC vs. CORTEX_MODELS_ALLOWLIST

Two mechanisms govern which *models* a role may invoke. They combine with an **OR** — access is granted if **either** permits it; denied only if both fail.

**A) RBAC (recommended, go-forward):** Snowflake auto-populates the `SNOWFLAKE.MODELS` schema (refreshed daily) with objects representing each Cortex model, plus application roles `CORTEX-MODEL-ROLE-<model>` and `CORTEX-MODEL-ROLE-ALL`. Grant those application roles to control access per-role.

**B) `CORTEX_MODELS_ALLOWLIST` (legacy, being deprecated):** account-level parameter set by ACCOUNTADMIN to `'All'`, `'None'`, or a comma-separated list. **Model names are case-sensitive and must be lowercase** (`'mistral-large2'`, not `'MISTRAL-LARGE2'`). **Starting August 2026 you can only change it to `'None'`; it is removed entirely later in 2026.** Migrate to RBAC.

**Snowflake implementation:**
```sql
-- RBAC: grant access to one model, or all current+future models
GRANT APPLICATION ROLE SNOWFLAKE."CORTEX-MODEL-ROLE-LLAMA3.1-70B" TO ROLE my_role;
GRANT APPLICATION ROLE SNOWFLAKE."CORTEX-MODEL-ROLE-ALL"        TO ROLE my_role;

-- Pick up brand-new models without waiting for the daily refresh
CALL SNOWFLAKE.MODELS.CORTEX_BASE_MODELS_REFRESH();

-- Use RBAC exclusively by disabling the allowlist fallback
ALTER ACCOUNT SET CORTEX_MODELS_ALLOWLIST = 'None';
```

**Decision framework:**
| Goal | Mechanism | Why |
|------|-----------|-----|
| Per-role, fine-grained, future-proof model control | RBAC (`SNOWFLAKE.MODELS` app roles) | Recommended; go-forward; survives allowlist removal |
| Quick account-wide default (legacy) | `CORTEX_MODELS_ALLOWLIST` | Simple, but deprecating in 2026 — avoid for new work |
| RBAC only (no fallback) | Set allowlist to `'None'` | Ensures only RBAC grants determine access |

**Key details:**
| Aspect | Detail |
|--------|--------|
| Relationship | RBAC OR allowlist — either grants access |
| ACCOUNTADMIN | Always has access to all models, regardless of either mechanism |
| Secondary roles | Can mask restrictions; test with `USE SECONDARY ROLES NONE` |
| Model access ≠ function access | Function call still gated by `CORTEX_USER`/`USE AI FUNCTIONS` |

---

## 3.4 Safety: Cortex Guard (guardrails)

**Cortex Guard filters potentially unsafe/harmful model responses.** It is enabled via the `guardrails` option on the completion call (either `TRUE` or `FALSE`, **default `FALSE`**). Under the hood it uses **Meta's Llama Guard** to filter the model's **output**.

**Snowflake implementation:**
```sql
SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-4-sonnet',
  [{'role':'user','content':'...'}],
  {'guardrails': TRUE});
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Default | `guardrails = FALSE` (off) |
| Mechanism | Llama Guard filtering of model **output** (a safety filter) |
| Not the same as | Groundedness/hallucination reduction — that's RAG grounding + evaluation, NOT Guard |

---

## 3.5 Cost tracking for AI workloads

AI function and Cortex service consumption bills as credits under the **`AI_SERVICES`** service type. Track it with ACCOUNT_USAGE views.

**Snowflake implementation:**
```sql
-- Daily AI credit consumption
SELECT usage_date, credits_used
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY
WHERE service_type = 'AI_SERVICES'
ORDER BY usage_date DESC;

-- Per-function / per-model token & credit detail
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.CORTEX_FUNCTIONS_USAGE_HISTORY
ORDER BY start_time DESC;
```

**Key details:**
| Aspect | Detail |
|--------|--------|
| Daily credits | `METERING_DAILY_HISTORY`, `service_type = 'AI_SERVICES'` |
| Function/model detail | `CORTEX_FUNCTIONS_USAGE_HISTORY` (tokens, model, credits) [VERIFY exact columns] |
| Billing basis | Number of tokens processed (input + output), not file size |
| `AI_COUNT_TOKENS` | Estimate tokens before running to forecast cost |

---

## 3.6 AI Observability: evaluating apps with TruLens & the RAG Triad

**AI Observability lets you run batch evaluations on a custom AI app (agent, RAG pipeline) instrumented with TruLens.** Evaluations invoke the app against a dataset, store traces, and compute **LLM-as-a-judge** metrics. The classic **RAG Triad**:

- **Context relevance** — are the retrieved chunks relevant to the question?
- **Groundedness** — is the answer supported by the retrieved context (i.e., not hallucinated)?
- **Answer relevance / correctness** — does the answer actually address the question?

Workflow: build+instrument the app with TruLens → register it in Snowflake (TruApp/framework wrapper) → create a run with a dataset + metric list → invoke the run → review metrics in Snowsight or via SQL. (For Cortex *Agent* evals specifically, use the Snowsight Evaluations tab / `EXECUTE_AI_EVALUATION` / GPA metrics.)

**Decision framework — reducing hallucinations vs. blocking unsafe content:**
| Goal | Use | Not |
|------|-----|-----|
| Stop the model inventing facts | Ground answers in retrieved context (RAG / Cortex Search) + measure **groundedness** | Cortex Guard (that's safety, not accuracy) |
| Block harmful/unsafe output | Cortex Guard (`guardrails=TRUE`) | Groundedness metric |
| Prove app quality on a dataset | AI Observability + TruLens (RAG Triad) | A single ad-hoc prompt |

---

## 3.Y Key Exam Traps for This Domain

1. **`CORTEX_USER` alone is no longer the whole story.** Current model = `USE AI FUNCTIONS` account privilege **AND** a database role (`CORTEX_USER` or `AI_FUNCTIONS_USER`). A question that grants only one and expects success is a trap.
2. **`AI_FUNCTIONS_USER` excludes the aggregates.** It covers scalar functions only — NOT `AI_AGG`/`AI_SUMMARIZE_AGG` — and grants no access to Cortex services (Search/Analyst/Agents).
3. **Allowlist is deprecating and lowercase-sensitive.** `CORTEX_MODELS_ALLOWLIST` model names must be lowercase; from Aug 2026 it can only be set to `'None'`. The recommended answer for new model governance is **RBAC**, not the allowlist.
4. **RBAC OR allowlist.** Model access is granted if *either* mechanism permits it. To make RBAC authoritative, set the allowlist to `'None'`.
5. **Database roles can't be granted to users directly.** Grant `CORTEX_USER`/`AI_FUNCTIONS_USER`/`CORTEX_EMBED_USER` to a role, then the role to the user.
6. **Cortex Guard ≠ groundedness.** Guard = Llama Guard output *safety* filter (default OFF). Hallucination reduction comes from RAG grounding + measuring **groundedness** in AI Observability. Don't swap them.
7. **ACCOUNTADMIN & secondary roles mask restrictions.** ACCOUNTADMIN always sees all models; a user with ACCOUNTADMIN as a *secondary* role does too. Verify governance with `USE SECONDARY ROLES NONE` under a non-admin role.

---

## Quick Reference Links

- [Privileges and model access for Cortex AI Functions](https://docs.snowflake.com/en/user-guide/snowflake-cortex/aisql-privileges-and-access)
- [Evaluate applications with TruLens (AI Observability)](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability/evaluate-applications-trulens)
- [AI_COMPLETE (Single string) — guardrails/options](https://docs.snowflake.com/en/sql-reference/functions/ai_complete-single-string)
- [SHOW CORTEX BASE MODELS](https://docs.snowflake.com/en/sql-reference/sql/show-cortex-base-models)
- [METERING_DAILY_HISTORY view](https://docs.snowflake.com/en/sql-reference/account-usage/metering_daily_history)
- [Official Exam Guide](https://learn.snowflake.com/en/certifications/) (search "SnowPro Specialty: Gen AI")
- [Schedule your exam](https://learn.snowflake.com/en/certifications/)
