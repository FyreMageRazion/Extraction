# Healthcare Prior Authorization POC

Skill-driven agentic flow using **CrewAI** and **skill.md files** as guidance artifacts (not Codex tools). Skills define WHAT to do, WHEN, ROLE, INSTRUCTIONS, and INPUT/OUTPUT schemas; the code reads and uses them to guide the flow.

## Scope

- **Administrative decision support** — not medical advice. Requires human clinical and administrative review.
- **No UI, no database.** POC uses tool-backed lookups (Tavily web search + NPI API) for validation and policy lookup.

## Setup

1. **Virtual environment** (already created at `.venv`):

   ```bash
   .venv\Scripts\activate
   ```

2. **Install dependencies** (from project root):

   ```bash
   pip install -r requirements.txt
   ```

   If install fails with "file in use" or similar, close other Python/IDE processes using the `.venv` and run again.

3. **API keys** (in `.env` in project root):

   - `OPENAI_API_KEY` — required for CrewAI/LLM.
   - `TAVILY_API_KEY` — required for web-backed tools (ICD-10, CPT, CMS coverage, FDA, PubMed lookups). Get one at [tavily.com](https://tavily.com). NPI lookup uses the public CMS API and needs no key.

4. **Input PDFs**:
   - Place prior authorization PDFs in `./inputs/`.
   - If `./inputs/` is missing or empty, the app uses `./input/` (where your existing PDFs are).

## Run

From project root with `.venv` activated:

```bash
python main.py
```

## Flow (driven by skills in `./skills/`)

1. **pa_case_normalizer** — Ingest PDFs from `./inputs/` (or `./input/`), normalize into structured case JSON.
2. **pa_coverage_eligibility** — Assess coverage using tools (lookup_cms_coverage, lookup_fda).
3. **pa_medical_necessity** — Evaluate against Carelon-style criteria using tools (search_pubmed, lookup_fda).
4. **pa_coding_provider_validation** — Validate diagnosis/procedure codes and provider using tools (lookup_icd10, lookup_cpt, lookup_npi).
5. **pa_decision_engine** — Render APPROVE / DENY / PENDING from coverage, medical necessity, and admin validity.
6. **pa_denial_letter_generator** — Only if decision == DENY; draft denial letter with appeal rights.
7. **pa_appeal_drafter** — Only if decision == DENY; draft appeal letter and list missing evidence.

Conditions (e.g. “only when DENY”) are enforced in code; execution order comes from each skill’s `execution_order` in its `.md` frontmatter.

## Output

- **Normalized case JSON** (from pa_case_normalizer).
- **Decision output** (from pa_decision_engine).
- If **DENY**: printed **denial letter**, **appeal letter**, and **missing evidence list**.

## Project layout

- `main.py` — Entry point; loads skills, loads PDFs, runs skill flow, prints results.
- `skills/` — `.md` skill definitions (name, description, execution_order, condition, role, instructions, input/output schema).
- `inputs/` — Prior auth PDFs (optional; falls back to `input/`).
- `input/` — Alternate PDF folder (used if `inputs/` has no PDFs).
- `utils/skill_loader.py` — Reads `./skills/*.md`, parses into `Skill` objects.
- `utils/pdf_loader.py` — Loads PDFs from a directory, returns concatenated text.
- `agents/runner.py` — Skill-aware execution: one CrewAI agent with tools, prompts built from each skill’s ROLE + INSTRUCTIONS + authoritative web search rules (for tool-using steps) + input + output schema; results stored in `case_state`.
- `tools/` — Tool layer: lookup_icd10, lookup_cpt, lookup_npi (NPI API), lookup_cms_coverage, lookup_fda, search_pubmed (Tavily). All fail gracefully and return "unverified" when no results. Tool calls are logged with the skill that triggered them.
- `skills/authoritative_web_search.md` — General web-search skill (injected into tool-using steps; not run as a separate step).

## Guardrails

Every agent prompt includes:

- “This is administrative decision support.”
- “Requires human clinical and administrative review.”
- “Do not provide medical advice.”

## Philosophy

- **Skill .md files are living specs** — code does not hardcode logic that contradicts them.
- **Clarity over cleverness** — POC-quality, clean, and extensible.
