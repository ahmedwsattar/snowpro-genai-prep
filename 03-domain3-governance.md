# Domain 3.0 — Snowflake Gen AI Governance (29%)

Second-largest domain. Four pillars: **model access control**, **RBAC/privileges**, **cost management**, and **AI observability**. Memorize the role names, the ACCOUNT_USAGE views, and the two model-access mechanisms.

---

## 3.1 Model access controls

### Two mechanisms to control which models can be used
1. **Role-Based Access Control (RBAC) — recommended, fine-grained.**
   - Cortex base models appear as objects in the **`SNOWFLAKE.MODELS`** schema (refreshed daily; `CALL SNOWFLAKE.MODELS.CORTEX_BASE_MODELS_REFRESH()` to refresh on demand).
   - Snowflake creates **application roles** per model, e.g. `SNOWFLAKE."CORTEX-MODEL-ROLE-LLAMA3.1-70B"`, plus `CORTEX-MODEL-ROLE-ALL` for all models.
   - Grant to a user role: `GRANT APPLICATION ROLE SNOWFLAKE."CORTEX-MODEL-ROLE-ALL" TO ROLE my_role;`
2. **Account-level allowlist parameter — legacy, being deprecated.**
   - `ALTER ACCOUNT SET CORTEX_MODELS_ALLOWLIST = 'All' | 'None' | 'model-a,model-b';`
   - Account-level only; ACCOUNTADMIN only; model names are **case-sensitive, lowercase**.

**How they interact:** access is granted if **either** RBAC USAGE **or** the allowlist permits the model (OR relationship). Denied only if both fail. To use RBAC exclusively, set the allowlist to `'None'`. **ACCOUNTADMIN always has access to all models** regardless — test restrictions with a non-admin role and `USE SECONDARY ROLES NONE`.

### Data safety & security considerations
- **Cross-region inference** — governance angle: data residency/compliance (payload transient, not persisted in processing region; encrypted in transit). Set `CORTEX_ENABLED_CROSS_REGION` to scope routing (DISABLED for strict residency).
- **Guardrails** — **Cortex AI Guardrails** (Horizon Catalog) protect against prompt injection / jailbreaks for CoCo, CoWork, and Cortex Agents. Enterprise Edition. Enable via account `AI_SETTINGS` parameter. (Historically "Cortex Guard" filtered harmful COMPLETE output.) Monitor with `CORTEX_AI_GUARDRAILS_USAGE_HISTORY`.
- **Sensitive data management** — use **AI_REDACT** to strip PII before sending to a model or storing outputs.
- **Reduce hallucinations & bias** — ground responses with **RAG** (Cortex Search), use **Verified Queries** for Analyst, apply guardrails, prefer capable models, and evaluate with AI Observability/TruLens.

### REST API authentication methods (know all three)
Snowflake Cortex REST APIs accept: **PAT** (programmatic access token), **key-pair JWT**, and **OAuth**.

---

## 3.2 RBAC — grant/revoke roles & privileges

### The privilege model for AI functions (know this precisely)
To call Cortex AI functions a user needs **BOTH**:
1. Account privilege **`USE AI FUNCTIONS`** (granted to PUBLIC by default; or per-function `USE AI FUNCTION <name>`), **and**
2. A database role: **`SNOWFLAKE.CORTEX_USER`** *or* **`SNOWFLAKE.AI_FUNCTIONS_USER`**.

### The Cortex database roles (the guide lists these; here's the accurate mapping)
| Role | Grants access to | Default on PUBLIC? |
|---|---|---|
| **SNOWFLAKE.CORTEX_USER** | All "covered" Cortex AI features (functions, Search, Agents, Analyst-eligible, fine-tuned model use) | **Yes** (via PUBLIC) |
| **SNOWFLAKE.AI_FUNCTIONS_USER** | Scalar AI functions only (all except the aggregate AI_AGG/AI_SUMMARIZE_AGG) — no access to Cortex services | No — grant explicitly |
| **SNOWFLAKE.CORTEX_AGENT_USER** | Cortex Agents only | No — grant explicitly |
| **SNOWFLAKE.CORTEX_EMBED_USER** | Embedding functions (AI_EMBED, EMBED_TEXT_768/1024) + create Search services with managed embeddings | No — grant explicitly |

> **Exam nuance:** database roles **cannot be granted directly to users** — grant them to a custom account role, then grant that role to users. Example:
> ```sql
> USE ROLE ACCOUNTADMIN;
> CREATE ROLE cortex_agent_user_role;
> GRANT DATABASE ROLE SNOWFLAKE.CORTEX_AGENT_USER TO ROLE cortex_agent_user_role;
> GRANT ROLE cortex_agent_user_role TO USER example_user;
> ```
>
> **Study-guide vs. reality:** the guide lists a `CORTEX_ANALYST_USER` role. In practice **Cortex Analyst is gated by the `ENABLE_CORTEX_ANALYST` account parameter (opt-in) plus CORTEX_USER**, not a standalone "CORTEX_ANALYST_USER" database role. If the exam offers `CORTEX_ANALYST_USER` as the "Analyst access" answer, pick it to match the guide — but understand the real mechanism is the account parameter + CORTEX_USER.

### Feature-specific access requirements
- **Cortex Analyst:** `ENABLE_CORTEX_ANALYST = TRUE` (opt-in) + CORTEX_USER; USAGE on the semantic view + warehouse.
- **Cortex Search:** CORTEX_USER (or embed role to build) + USAGE on the search service and its DB/schema/table.
- **Cortex Agents:** CORTEX_USER or CORTEX_AGENT_USER; the user's **default role** (not session role) needs USAGE on the agent, its DB/schema, the default warehouse, and on every tool object (search service, semantic view tables, custom functions). Users also need a **default warehouse**.
- **Snowflake Intelligence:** relies on the underlying Agent/Search access controls.

### Revoking / opting out
- Revoke defaults from PUBLIC: `REVOKE DATABASE ROLE SNOWFLAKE.CORTEX_USER FROM ROLE PUBLIC;` (and optionally `REVOKE IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE FROM ROLE PUBLIC;` — but this also removes ACCOUNT_USAGE access, so be careful).
- Disable Analyst: `ALTER ACCOUNT SET ENABLE_CORTEX_ANALYST = FALSE;`
- `REVOKE PRIVILEGE ON APPLICATION ROLE` / `GRANT DATABASE ROLE` appear in the guide's links — know the DDL shapes.

---

## 3.3 Manage, monitor & optimize Cortex costs

### How Cortex is billed
- **Token-based** for LLM functions (credits per million tokens, varies by **model** and **function** — see Service Consumption Table). Use **AI_COUNT_TOKENS** to estimate.
- Plus standard **warehouse compute** for the query running the function.
- Cortex Search adds: **indexing/embedding** cost + **serving** cost + the warehouse behind it.

### Cost controls by feature
- **Cortex Agents:** limit token usage (agent config); resource budgets.
- **Cortex Search:** cost types = virtual warehouse (build), **EMBED_TEXT** (embedding), **serving**, **indexing**.
- **Cortex AI functions:** minimize tokens (shorter prompts/outputs, smaller models); token cost implications per model.
- **SPCS:** track **compute pool** credits (pools bill while running — suspend when idle).
- **Provisioned Throughput:** reserved-capacity billing.

### ACCOUNT_USAGE / metering views (HIGH YIELD — know which view for what)
| View (SNOWFLAKE.ACCOUNT_USAGE.*) | Tracks |
|---|---|
| **METERING_HISTORY** | Hourly credits by service type (incl. `AI_SERVICES`) |
| **METERING_DAILY_HISTORY** | **Daily** credit consumption by service type — *the answer for "daily AI cost"* |
| **CORTEX_ANALYST_USAGE_HISTORY** | Analyst messages/credits by user (hourly) |
| **CORTEX_AISQL_USAGE_HISTORY** | Per-query LLM function token usage (canonical for per-query AI function cost) |
| **CORTEX_SEARCH_DAILY_USAGE_HISTORY** | Cortex Search serving/token usage (daily) |
| **CORTEX_REST_API_USAGE_HISTORY** | REST inference token usage (billed in dollars) |
| **CORTEX_PROVISIONED_THROUGHPUT_USAGE_HISTORY** | PTU hours |
| **CORTEX_FUNCTIONS_USAGE_HISTORY** | (legacy) per-function usage — superseded by CORTEX_AI_FUNCTIONS_USAGE_HISTORY |

> **Official sample Q1 fact:** daily AI credit consumption →
> `SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY WHERE SERVICE_TYPE='AI_SERVICES';`
> Note: **ACCOUNT_USAGE** (not INFORMATION_SCHEMA), and **METERING_DAILY_HISTORY** for *daily*.

### Usage quotas & object tagging
- Set **usage quotas / budgets** (incl. resource budgets and shared resource budgets for AI features) to cap/alert on spend.
- **Object tagging:** tag AI objects (e.g., agents, warehouses) to attribute and monitor AI-service costs by team/cost-center.

---

## 3.4 AI Observability tools

Evaluate and monitor Gen AI apps (RAG, agents) for quality and safety.

**Features:**
- **Evaluation metrics** — score outputs (e.g., the **RAG Triad**: context relevance, groundedness, answer relevance) using an **LLM-as-a-judge**.
- **Comparisons** — compare app versions/configs side by side.
- **Tracing** — capture each step of a request (retrieval, prompt, response) for debugging.
- **Logging** + **Event tables** — telemetry is written to an **event table** for analysis.

**Implementation:** the **TruLens SDK** (open-source, integrated into Snowflake) instruments the app, runs evaluations, and logs traces/metrics that surface in Snowsight AI Observability.

---

## Governance cheat (HIGH YIELD)

| Need | Answer |
|---|---|
| Daily AI credit cost | `ACCOUNT_USAGE.METERING_DAILY_HISTORY`, `SERVICE_TYPE='AI_SERVICES'` |
| Analyst usage by user | `CORTEX_ANALYST_USAGE_HISTORY` |
| Per-query AI function tokens | `CORTEX_AISQL_USAGE_HISTORY` |
| Restrict which models a role can call | Model **RBAC** (SNOWFLAKE.MODELS app roles); allowlist is legacy |
| Give only Agents access | `SNOWFLAKE.CORTEX_AGENT_USER` |
| Give only embedding access | `SNOWFLAKE.CORTEX_EMBED_USER` |
| Turn on Cortex Analyst | `ENABLE_CORTEX_ANALYST = TRUE` |
| Block prompt injection on agents | Cortex AI Guardrails (`AI_SETTINGS`) |
| Remove PII before inference | AI_REDACT |
| Evaluate RAG quality | AI Observability + TruLens (RAG Triad) |
| Estimate token cost pre-run | AI_COUNT_TOKENS |
| Attribute AI cost to a team | Object tagging + budgets |

---

## Common traps
- **Two things needed for AI functions:** `USE AI FUNCTIONS` privilege **AND** a CORTEX_USER/AI_FUNCTIONS_USER role. Missing either → denied.
- **Database roles can't be granted directly to users** — go through a custom role.
- **METERING_DAILY_HISTORY** (daily) vs **METERING_HISTORY** (hourly); both live in **ACCOUNT_USAGE**, not INFORMATION_SCHEMA.
- **RBAC vs allowlist:** OR relationship; allowlist is legacy/deprecating; ACCOUNTADMIN bypasses both.
- **Agents use the caller's *default* role**, not the current session role — a classic "why does it fail" question.
- **TruLens** is the SDK behind AI Observability; **event tables** store the telemetry.
- **AI_REDACT** = sensitive-data governance; **Guardrails** = prompt-injection/jailbreak defense. Different problems.

---

# QUIZ — Domain 3 (answers at bottom)

**Q1.** Which query retrieves **daily** credit consumption for AI services?
- A. `SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY WHERE SERVICE_TYPE='AI_SERVICES';`
- B. `SELECT * FROM SNOWFLAKE.INFORMATION_SCHEMA.METERING_HISTORY WHERE SERVICE_TYPE='AI_SERVICES';`
- C. `SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY WHERE SERVICE_TYPE='AI_SERVICES';`
- D. `SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_DAILY_HISTORY WHERE SERVICE_TYPE='AI_SERVICES';`

**Q2.** A user has the `USE AI FUNCTIONS` account privilege but calls to AI_COMPLETE fail. Most likely missing?
- A. A default warehouse
- B. The CORTEX_USER (or AI_FUNCTIONS_USER) database role
- C. ORGADMIN
- D. A semantic view

**Q3.** You must restrict a specific analyst role to only Cortex **Agents** (not other Cortex features). Which grant?
- A. `GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE analyst_role;`
- B. `GRANT DATABASE ROLE SNOWFLAKE.CORTEX_AGENT_USER TO ROLE analyst_role;` (and revoke CORTEX_USER)
- C. `GRANT ROLE SNOWFLAKE.CORTEX_AGENT_USER TO USER analyst_user;`
- D. `ALTER ACCOUNT SET ENABLE_CORTEX_ANALYST = TRUE;`

**Q4.** Recommended, fine-grained way to control which LLMs a role may call?
- A. CORTEX_MODELS_ALLOWLIST parameter (it's the go-forward mechanism)
- B. Model RBAC via application roles in SNOWFLAKE.MODELS
- C. Network policies
- D. Masking policies

**Q5.** Which tool set evaluates a RAG app's answer quality and groundedness inside Snowflake?
- A. AI Observability with the TruLens SDK
- B. Resource monitors
- C. AI_REDACT
- D. VECTOR_COSINE_SIMILARITY

**Q6.** Before sending customer support text to an LLM, you must remove PII. Which function?
- A. AI_CLASSIFY
- B. AI_REDACT
- C. AI_FILTER
- D. AI_TRANSLATE

**Q7.** How do RBAC model access and the account allowlist interact?
- A. Both must permit the model (AND)
- B. Access granted if either permits it (OR); denied only if both fail
- C. Allowlist always overrides RBAC
- D. RBAC only works for ACCOUNTADMIN

**Q8.** A Cortex Agent call fails for a user even though their current session role has all privileges. Likely cause?
- A. The agent needs a masking policy
- B. Agents evaluate the user's **default** role/warehouse, which lack the grants
- C. Cross-region inference is disabled
- D. The allowlist is set to 'All'

**Q9.** Which is TRUE about granting Cortex database roles?
- A. They can be granted directly to a user
- B. They must be granted to a role, which is then granted to users
- C. Only ORGADMIN can grant them
- D. They're granted with GRANT APPLICATION ROLE only

**Q10.** To defend Cortex Agents against prompt-injection/jailbreak attempts, you enable:
- A. AI_REDACT
- B. Cortex AI Guardrails (via AI_SETTINGS)
- C. A resource monitor
- D. VECTOR_NORMALIZE

---

## ANSWER KEY — Domain 3

**Q1 → D.** Daily → `METERING_DAILY_HISTORY`, in **ACCOUNT_USAGE**. C is hourly; B uses INFORMATION_SCHEMA (wrong); A is QUERY_HISTORY (no credit column by service). Matches official sample Q1.

**Q2 → B.** AI functions need **both** the account privilege and a CORTEX_USER/AI_FUNCTIONS_USER database role. Having only the privilege isn't enough.

**Q3 → B.** Grant `CORTEX_AGENT_USER` (Agents-only) and revoke `CORTEX_USER` (which would re-open all features). C is wrong because database roles can't be granted directly to users; D enables Analyst.

**Q4 → B.** Model RBAC (application roles in `SNOWFLAKE.MODELS`) is the recommended, fine-grained, go-forward mechanism; the allowlist is legacy/deprecating.

**Q5 → A.** AI Observability + the TruLens SDK provide evaluation metrics (RAG Triad), tracing, and comparisons.

**Q6 → B.** AI_REDACT removes/masks sensitive data (PII).

**Q7 → B.** OR relationship — either mechanism grants access; denied only if both fail. (ACCOUNTADMIN bypasses both.)

**Q8 → B.** Cortex Agents determine permissions from the querying user's **default** role and require a **default warehouse** — not the current session role.

**Q9 → B.** SNOWFLAKE database roles can't be granted directly to users; grant to a custom role, then to users.

**Q10 → B.** Cortex AI Guardrails (configured via the account `AI_SETTINGS` parameter) protect against prompt injection/jailbreaks. AI_REDACT handles PII, a different concern.
