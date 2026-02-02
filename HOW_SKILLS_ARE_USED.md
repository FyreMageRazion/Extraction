# How Skills Are Used in the PA POC

This document explains how the markdown skill files in `E:\openAI_healthcare_poc\skills` are loaded, interpreted, and used to drive the prior authorization (PA) pipeline. **Skills are not executable code** — they are **instructional contracts** (specs) that tell the agent *what* to do, *when*, and *how*, including input/output shapes.

---

## 1. What a Skill File Is

Each file in `skills/` is a **Markdown document** with:

1. **YAML frontmatter** (between `---` lines) defining:
   - **`name`** — Unique skill identifier (e.g. `pa_case_normalizer`, `pa_denial_letter_generator`).
   - **`description`** — Short summary of the skill.
   - **`execution_order`** — Integer used to sort skills (lower = earlier). Controls the order of steps in the pipeline.
   - **`condition`** (optional) — When present (e.g. `decision == "DENY"`), the skill runs only if that condition is true after a previous step.

2. **Body sections** parsed by the loader:
   - **`## Role`** — The persona/role the agent should adopt for this step.
   - **`## Instructions`** — Detailed steps and rules for the agent.
   - **`## Input Schema`** — A JSON schema (in a fenced code block) describing the expected input shape.
   - **`## Output Schema`** — A JSON schema describing the required output shape.

The code **never executes** the markdown. It **reads and parses** it into a `Skill` object and uses those fields to build prompts and tasks.

---

## 2. How Skills Are Loaded

| Where | What happens |
|-------|------------------|
| **`main.py`** | Calls `load_skills_from_dir(SKILLS_DIR)` with the path to `skills/`. |
| **`utils/skill_loader.py`** | `load_skills_from_dir()` globs all `*.md` files in that directory, parses each with `load_skill(path)`, and returns a **list of `Skill` objects** sorted by **`execution_order`**. |

**Parsing (skill_loader.py):**

- **Frontmatter**: YAML between the first `---` and second `---` is parsed to get `name`, `description`, `execution_order`, `condition`.
- **Body**: Regex is used to extract:
  - Text under `## Role` → `skill.role`
  - Text under `## Instructions` → `skill.instructions`
  - First JSON code block under `## Input Schema` → `skill.input_schema`
  - First JSON code block under `## Output Schema` → `skill.output_schema`

The resulting **`Skill`** dataclass has: `name`, `description`, `execution_order`, `condition`, `role`, `instructions`, `input_schema`, `output_schema`, `raw_content`.

---

## 3. How Skills Drive the Pipeline

The loaded list of skills is passed into **`PAFlow`** (and underneath, **`run_skill_flow()`** in `agents/runner.py`). The pipeline does **not** run “the skill file”; it uses each skill’s fields to:

1. **Decide execution order and which steps are conditional**
2. **Build CrewAI Tasks** (one task per skill, with descriptions and expected output)
3. **Map prior outputs to each step’s input** (according to the skill’s logical input needs)
4. **Inject tool-usage and web-search rules** for skills that use tools

So: **skills define the workflow and the prompts**; the **runner and flow** turn them into a Crew with sequential and conditional tasks.

---

## 4. Skill Categories and Execution

### 4.1 Skills that run as sequential Crew tasks

All skills **except** the two below run in order as **CrewAI sequential Tasks**:

| Skill name | execution_order | Purpose |
|------------|-----------------|---------|
| `pa_case_normalizer` | 1 | Extract and normalize case data from documents → structured JSON |
| `pa_coverage_eligibility` | 2 | Assess coverage (CMS, FDA, etc.) using tools |
| `pa_medical_necessity` | 3 | Evaluate medical necessity using guidelines and tools |
| `pa_coding_provider_validation` | 4 | Validate ICD-10/CPT codes and NPI using tools |
| `pa_decision_engine` | 5 | Combine prior outputs → APPROVE / DENY / PENDING |

**Excluded from the Crew task list:**

- **`authoritative_web_search`** — Not run as its own task. Its *content* is used as a **block of instructions** injected into the prompts of any skill that uses tools (see below).
- **`pa_denial_letter_generator`** and **`pa_appeal_drafter`** — Have a **`condition`** in frontmatter; they are run as **ConditionalTasks** (see 4.2).

So the “main” Crew is: normalizer → coverage → medical necessity → coding validation → decision engine.

---

### 4.2 Conditional skills (only when decision is DENY)

Two skills have **`condition: decision == "DENY"`** in their frontmatter:

| Skill name | execution_order | Condition | Purpose |
|------------|-----------------|-----------|---------|
| `pa_denial_letter_generator` | 6 | Run only if decision is DENY | Generate denial letter with rationale and appeal rights |
| `pa_appeal_drafter` | 7 | Run only if denial letter was produced | Draft appeal letter and missing evidence |

In **`agents/runner.py`**:

- These are turned into **CrewAI `ConditionalTask`** instances.
- **`pa_denial_letter_generator`** runs only when the **decision task** output has `decision == "DENY"` (condition `_is_deny`).
- **`pa_appeal_drafter`** runs only when the **denial letter task** actually produced output (condition `_is_denial_output`).

So the *when* (only on DENY, only after denial letter) comes from the skill’s **`condition`** and **order**; the *what* and *how* come from **Role**, **Instructions**, and **Output Schema**.

---

## 5. How a Skill Becomes a CrewAI Task

For each (non-conditional, non–authoritative_web_search) skill, the runner builds a **CrewAI `Task`** (or `ConditionalTask`):

1. **Task description** — Built by **`_task_description_for_skill(skill, is_first)`**:
   - Guardrails (administrative decision support, human review, no medical advice).
   - “I am executing skill: &lt;skill.name&gt;”.
   - For skills that use tools: the **Authoritative Web Search** block (derived from the `authoritative_web_search` skill’s purpose and rules).
   - **Role** and **Instructions** from the skill’s `## Role` and `## Instructions`.
   - **Tool usage** — From `_get_tool_usage_block(skill.name)` (which tools to call and where to get arguments from; see below).
   - **Input** — Either “The input documents are: {documents}…” (first task) or “Use the output of your context tasks…” (later tasks).
   - **Required output** — “Respond with ONLY a single JSON object…” plus the skill’s **Output Schema** (the `## Output Schema` block from the .md file).

2. **Expected output** — Fixed string: “A single JSON object conforming to the required output schema. No other text.”

3. **Context** — Previous tasks in order, so the agent receives prior step outputs as context.

So: **skill.name**, **skill.role**, **skill.instructions**, and **skill.output_schema** (and for tool-using skills, the Authoritative Web Search block and tool-usage block) are **directly injected** into the task description the agent sees.

---

## 6. Where Each Skill Gets Its Input From (case_state)

The pipeline keeps a **`case_state`** dict that accumulates outputs keyed by skill name (e.g. `pa_case_normalizer`, `pa_decision_engine`). The runner’s **`_build_skill_input(skill_name, case_state)`** maps **case_state** into the **logical input** for that skill. That mapping is **hard-coded per skill name** to match the intended data flow (and the Input Schemas in the .md files):

| Skill | Input built from case_state |
|-------|-----------------------------|
| `pa_case_normalizer` | `documents` (raw PDF text) |
| `pa_coverage_eligibility` | Normalized `procedures_requested`, `payer` |
| `pa_medical_necessity` | Normalized diagnoses, procedures, anatomy, conservative therapy, imaging, clinical findings |
| `pa_coding_provider_validation` | Normalized diagnoses, procedures, provider |
| `pa_decision_engine` | Coverage, medical necessity, and coding outputs (flags, criteria_met/failed, validation_issues, etc.) |
| `pa_denial_letter_generator` | Decision output (decision, reasons, denial_codes) + normalized payer/case_data |
| `pa_appeal_drafter` | Denial reasons, case_data, medical necessity evaluation, coverage assessment |

So the **skill’s Input Schema** in the .md describes the *shape* of input; the **runner** is responsible for *filling* that shape from **case_state** (and from Crew context for later tasks). The .md files do not specify *where* the data comes from; that wiring is in `_build_skill_input`.

---

## 7. Skills That Use Tools and “Authoritative Web Search”

Some skills are designated as **tool-using** in the runner:

```text
SKILLS_THAT_USE_TOOLS = {
  "pa_coding_provider_validation",
  "pa_coverage_eligibility",
  "pa_medical_necessity",
  "pa_appeal_drafter",
}
```

For these tasks only, the runner adds:

1. **Authoritative Web Search block** — A fixed block of text (in `agents/runner.py`) that encodes the *purpose and rules* from the **`authoritative_web_search`** skill: allowed domains, search rules, output requirements (URLs, confidence, verification_status), and prohibitions. So the **authoritative_web_search** skill is not run as a task; its *content* is reused as **instructions** inside other skills’ tasks.

2. **Tool-usage block** — From **`_get_tool_usage_block(skill.name)`**: which tools to call (e.g. `lookup_icd10`, `lookup_cpt`, `lookup_npi`, `lookup_cms_coverage`, `search_pubmed`) and **where to get their arguments** (e.g. “from Input.diagnoses”, “from Input.provider.npi”). This ties the skill’s logical input (from context/case_state) to the actual tool parameters.

So:

- **authoritative_web_search.md** → Defines *how* web search and tools should be used; that is injected into every **tool-using** skill’s task.
- **Tool-using skills’ .md files** → Define role, instructions, and output schema; the runner adds the web-search and tool-usage text when building the task.

---

## 8. End-to-End Flow Summary

```
main.py
  → load_skills_from_dir(skills/)     # Parse all .md → list[Skill] by execution_order
  → PAFlow(skills).kickoff(inputs={"documents": pdf_text})
       → run_skill_flow(skills, documents_text)
            → Split skills: crew_skills (no condition, not authoritative_web_search)
                         + denial_skill, appeal_skill (for ConditionalTasks)
            → Build one Task (or ConditionalTask) per skill:
                 - description = guardrails + skill.name + [Authoritative Web Search]
                                 + skill.role + skill.instructions + tool usage + input hint
                                 + skill.output_schema
                 - context = previous tasks
            → Crew(agents=[agent], tasks=tasks, process=sequential).kickoff(inputs={"documents": ...})
            → Parse each task output as JSON → case_state[skill_name] = parsed
  → flow.case_state() → same shape as before for main.py (normalized case, decision, denial/appeal)
```

So:

- **Skills** = Markdown specs (name, order, condition, role, instructions, input/output schema).
- **Loader** = Turns .md into `Skill` objects.
- **Runner/Flow** = Turn skills into Crew tasks, wire context/inputs from **case_state**, inject Authoritative Web Search and tool usage for tool-using skills, and run the Crew. Outputs are written back to **case_state** by skill name.

---

## 9. Summary Table: Skills and Their Use

| File | Run as task? | How it’s used |
|------|------------------|----------------|
| `authoritative_web_search.md` | No | Its *purpose and rules* are injected into every **tool-using** skill’s task description. |
| `pa_case_normalizer.md` | Yes (1st) | Task description from role, instructions, output schema; input = documents. |
| `pa_coverage_eligibility.md` | Yes (2nd) | Same + Authoritative Web Search + tool usage (e.g. CMS, FDA); input from normalizer. |
| `pa_medical_necessity.md` | Yes (3rd) | Same + Authoritative Web Search + tool usage (e.g. PubMed, FDA); input from normalizer. |
| `pa_coding_provider_validation.md` | Yes (4th) | Same + Authoritative Web Search + tool usage (ICD-10, CPT, NPI); input from normalizer. |
| `pa_decision_engine.md` | Yes (5th) | Task from role, instructions, output schema; input from coverage, medical necessity, coding. |
| `pa_denial_letter_generator.md` | ConditionalTask (6th) | Only if decision == DENY; task from role, instructions, output schema; input from decision + normalizer. |
| `pa_appeal_drafter.md` | ConditionalTask (7th) | Only if denial letter was produced; task + Authoritative Web Search + tool usage; input from denial + case. |

Together, these markdown files fully specify **what** each step does, **when** it runs, and **what** shape it consumes and produces; the **code** implements the workflow, task building, and data wiring.
