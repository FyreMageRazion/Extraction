"""
Skill-driven execution flow: Crew with sequential Tasks for main pipeline;
conditional skills (pa_denial_letter_generator, pa_appeal_drafter when decision == DENY)
run as CrewAI ConditionalTasks. Results are stored in a shared case_state.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from crewai import Agent, Crew, Process, Task
from crewai.tasks.conditional_task import ConditionalTask
from crewai.tasks.task_output import TaskOutput

from tools import context as tools_context
from tools import get_pa_tools

# Skill type from skill_loader (avoid circular import by using duck typing)
SkillLike = Any

# --- Guardrails: must appear in every prompt ---
GUARDRAILS = (
    "This is administrative decision support. "
    "Requires human clinical and administrative review. "
    "Do not provide medical advice."
)

# Skills that use tools get the authoritative web search block and tool-usage rules
SKILLS_THAT_USE_TOOLS = frozenset({
    "pa_coding_provider_validation",
    "pa_coverage_eligibility",
    "pa_medical_necessity",
    "pa_appeal_drafter",
})

# Block injected for tool-using skills (from authoritative_web_search skill)
AUTHORITATIVE_WEB_SEARCH_BLOCK = """
## Authoritative Web Search (when you use tools)

Purpose: Controlled, auditable mechanism for retrieving reference information when direct APIs are unavailable. Governs WHERE and HOW web search may be used.

When to Use: When ICD-10/CPT/HCPCS validation, CMS NCD/LCD coverage, FDA approval/recall, PubMed/guideline evidence, or provider/payer references are needed.

Allowed Search Domains: cms.gov, icd.codes, icd10data.com, ama-assn.org, npiregistry.cms.hhs.gov, providerdata.cms.gov, fda.gov, pubmed.ncbi.nlm.nih.gov, specialty society sites. Non-authoritative sites (blogs, forums, marketing) are NOT permitted.

Search Construction Rules: Use explicit site constraints; use exact codes/identifiers; prefer official government or society sources; limit to top 3 relevant findings; do not combine unrelated queries.

Output Requirements: For every search return query used, source URLs, extracted factual summary, confidence (high/medium/low), verification_status (verified/partially_verified/unverified).

Prohibited: Do NOT infer facts not found in results; do NOT claim official determinations; do NOT fabricate citations; do NOT override payer-specific policies.

Cite URLs when using web search tools.
"""


def _build_skill_input(skill_name: str, case_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build the input object for a skill from case_state. Skills define INPUT SCHEMA;
    we map case_state (previous step outputs + documents) to that input.
    """
    if skill_name == "pa_case_normalizer":
        return {"documents": case_state.get("documents", "")}

    normalized = case_state.get("pa_case_normalizer") or {}
    coverage = case_state.get("pa_coverage_eligibility") or {}
    medical = case_state.get("pa_medical_necessity") or {}
    coding = case_state.get("pa_coding_provider_validation") or {}
    decision_out = case_state.get("pa_decision_engine") or {}

    if skill_name == "pa_coverage_eligibility":
        return {
            "procedures_requested": normalized.get("procedures_requested", []),
            "payer": normalized.get("payer", {}),
        }

    if skill_name == "pa_medical_necessity":
        return {
            "diagnoses": normalized.get("diagnoses", []),
            "diagnosis_descriptions": normalized.get("diagnosis_descriptions", []),
            "procedures_requested": normalized.get("procedures_requested", []),
            "procedure_descriptions": normalized.get("procedure_descriptions", []),
            "anatomical_levels": normalized.get("anatomical_levels", []),
            "conservative_therapy": normalized.get("conservative_therapy", {}),
            "imaging": normalized.get("imaging", {}),
            "clinical_findings": normalized.get("clinical_findings", []),
        }

    if skill_name == "pa_coding_provider_validation":
        return {
            "diagnoses": normalized.get("diagnoses", []),
            "procedures_requested": normalized.get("procedures_requested", []),
            "provider": normalized.get("provider", {}),
        }

    if skill_name == "pa_decision_engine":
        issues = coding.get("issues", [])
        return {
            "coverage_eligible": coverage.get("coverage_eligible", False),
            "coverage_basis": coverage.get("coverage_basis", ""),
            "medical_necessity_met": medical.get("medical_necessity_met", False),
            "criteria_met": medical.get("criteria_met", []),
            "criteria_failed": medical.get("criteria_failed", []),
            "diagnosis_codes_valid": coding.get("diagnosis_codes_valid", False),
            "procedure_codes_valid": coding.get("procedure_codes_valid", False),
            "provider_valid": coding.get("provider_valid", False),
            "validation_issues": issues,
        }

    if skill_name == "pa_denial_letter_generator":
        return {
            "decision": decision_out.get("decision", "DENY"),
            "primary_reason": decision_out.get("primary_reason", ""),
            "secondary_reasons": decision_out.get("secondary_reasons", []),
            "payer": normalized.get("payer", {}),
            "case_data": {
                "patient": normalized.get("patient", {}),
                "procedures_requested": normalized.get("procedures_requested", []),
                "provider": normalized.get("provider", {}),
            },
            "denial_codes": decision_out.get("denial_codes", []),
        }

    if skill_name == "pa_appeal_drafter":
        return {
            "denial_reasons": [
                {
                    "primary_reason": decision_out.get("primary_reason", ""),
                    "secondary_reasons": decision_out.get("secondary_reasons", []),
                }
            ],
            "case_data": {
                "patient": normalized.get("patient", {}),
                "diagnoses": normalized.get("diagnoses", []),
                "procedures_requested": normalized.get("procedures_requested", []),
                "conservative_therapy": normalized.get("conservative_therapy", {}),
                "imaging": normalized.get("imaging", {}),
                "provider": normalized.get("provider", {}),
            },
            "medical_necessity_evaluation": {
                "criteria_met": medical.get("criteria_met", []),
                "criteria_failed": medical.get("criteria_failed", []),
            },
            "coverage_assessment": coverage,
        }

    return {}


def _get_tool_usage_block(skill_name: str) -> str:
    """Return tool-usage instructions for skills that use tools, including what to pass and where to get it."""
    if skill_name == "pa_coding_provider_validation":
        return (
            "You MUST use lookup_icd10 for each diagnosis code and lookup_cpt for each procedure code, "
            "and lookup_npi for the provider. Do not infer ICD validity without lookup_icd10. "
            "Do not claim procedure code validity without lookup_cpt. Do not claim NPI validity without lookup_npi. "
            "If a tool is not called for a code or NPI, set that item's status to 'unverified' in the output.\n\n"
            "Where to get tool arguments (from the Input JSON above): "
            "Get diagnosis codes from Input.diagnoses and call lookup_icd10(code=<code>) or lookup_icd10(condition=<description>). "
            "Get procedure codes from Input.procedures_requested and call lookup_cpt(code=<code>). "
            "Get NPI from Input.provider.npi and call lookup_npi(npi=<value>). "
            "Extract these values from the Input; do not call tools without them."
        )
    if skill_name == "pa_coverage_eligibility":
        return (
            "You MUST use lookup_cms_coverage for procedure coverage and lookup_fda for device/drug approval when relevant. "
            "Do not claim coverage or FDA approval without calling these tools. "
            "If you do not call them, mark coverage/FDA fields as 'unverified'.\n\n"
            "Where to get tool arguments (from the Input JSON above): "
            "Get procedure codes from Input.procedures_requested (use the code field for each procedure) and call lookup_cms_coverage(cpt_code=<code>) for each. "
            "For devices or drugs mentioned in the case, call lookup_fda(name=<device or drug name>). "
            "Do not call tools without these arguments from the Input."
        )
    if skill_name == "pa_medical_necessity":
        return (
            "You MUST use search_pubmed for evidence and lookup_fda for indication validation when relevant. "
            "Do not cite literature or FDA status without tool output. "
            "If tools are not used, mark evidence/FDA fields as 'unverified'.\n\n"
            "Where to get tool arguments (from the Input JSON above): "
            "Build search queries from Input (diagnoses, procedure_descriptions, clinical_findings) and call search_pubmed(query=<your query>). "
            "For devices or drugs in the case, call lookup_fda(name=<name>). "
            "Use only values present in the Input."
        )
    if skill_name == "pa_appeal_drafter":
        return (
            "You MUST use search_pubmed to support appeal arguments when citing literature. "
            "Cite URLs when using web search tools. "
            "If you do not use search_pubmed for citations, mark those as 'unverified'.\n\n"
            "Where to get tool arguments (from the Input JSON above): "
            "Build search queries from Input.denial_reasons and case_data. Call search_pubmed(query=<query>) to support appeal arguments. "
            "Use denial reasons and case facts from the Input."
        )
    return "Use tools only when they apply to the input data."


def _prompt_for_skill(
    skill: SkillLike,
    input_data: Dict[str, Any],
) -> str:
    """Build the prompt for one skill execution: guardrails + optional web search block + skill role/instructions + tool usage + input + output schema + metadata."""
    parts = [GUARDRAILS, "", f"I am executing skill: {skill.name}", ""]

    if skill.name in SKILLS_THAT_USE_TOOLS:
        parts.append(AUTHORITATIVE_WEB_SEARCH_BLOCK.strip())
        parts.append("")

    parts.extend([
        "## Your role",
        skill.role,
        "",
        "## Instructions",
        skill.instructions,
        "",
        "## Tool usage",
        _get_tool_usage_block(skill.name),
        "",
        "## Input (use this to produce the output)",
        "```json",
        json.dumps(input_data, indent=2, default=str),
        "```",
        "",
        "## Required output",
        "Respond with ONLY a single JSON object that conforms to this schema. No other text.",
        "Where you used tools, include in the output: source: 'tool' or 'web_search', confidence: 'high' or 'medium' or 'low', and citations: [list of URLs]. "
        "Do not change the rest of the output schema; add these fields only where they apply (e.g. per code or per finding).",
        "```json",
        skill.output_schema,
        "```",
    ])
    return "\n".join(parts)


def _task_description_for_skill(skill: SkillLike, is_first: bool) -> str:
    """Build task description for Crew Task: guardrails, role, instructions, tool usage, input hint, output schema."""
    parts = [GUARDRAILS, "", f"I am executing skill: {skill.name}", ""]
    if skill.name in SKILLS_THAT_USE_TOOLS:
        parts.append(AUTHORITATIVE_WEB_SEARCH_BLOCK.strip())
        parts.append("")
    parts.extend([
        "## Your role",
        skill.role,
        "",
        "## Instructions",
        skill.instructions,
        "",
        "## Tool usage",
        _get_tool_usage_block(skill.name),
        "",
        "## Input",
        "The input documents are: {documents}. Use them as the sole source for this task."
        if is_first
        else "Use the output of your context tasks (previous tasks) as your input. Extract the required fields from the context.",
        "",
        "## Required output",
        "Respond with ONLY a single JSON object that conforms to this schema. No other text.",
        "Where you used tools, include: source, confidence, citations. Do not change the rest of the output schema.",
        "```json",
        skill.output_schema,
        "```",
    ])
    return "\n".join(parts)


def _parse_json_from_output(text: str) -> Optional[Dict[str, Any]]:
    """Extract a JSON object from agent output (e.g. inside ```json ... ``` or raw {...})."""
    if not text or not text.strip():
        return None
    # Prefer ```json ... ``` block
    code_match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
    if code_match:
        raw = code_match.group(1).strip()
    else:
        # Try last {...}
        brace = text.rfind("{")
        if brace >= 0:
            raw = text[brace:]
        else:
            raw = text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _evaluate_condition(condition: Optional[str], case_state: Dict[str, Any]) -> bool:
    """Evaluate skill condition (e.g. decision == \"DENY\") against case_state."""
    if not condition:
        return True
    decision_out = case_state.get("pa_decision_engine") or {}
    decision = decision_out.get("decision")
    if condition.strip() == 'decision == "DENY"':
        return decision == "DENY"
    return True


def _is_deny(output: TaskOutput) -> bool:
    """Condition for ConditionalTask: run denial letter only when decision is DENY."""
    raw = output.raw if hasattr(output, "raw") else str(output)
    parsed = _parse_json_from_output(raw)
    if not parsed:
        return False
    return parsed.get("decision") == "DENY"


def _is_denial_output(output: TaskOutput) -> bool:
    """Condition for ConditionalTask: run appeal drafter only when denial letter was produced."""
    raw = output.raw if hasattr(output, "raw") else str(output)
    parsed = _parse_json_from_output(raw)
    return bool(parsed)


def _contains_unverified(obj: Any) -> bool:
    """Return True if 'unverified' appears in obj (recursively)."""
    if obj == "unverified":
        return True
    if isinstance(obj, dict):
        return any(_contains_unverified(v) for v in obj.values())
    if isinstance(obj, list):
        return any(_contains_unverified(v) for v in obj)
    if isinstance(obj, str) and "unverified" in obj:
        return True
    return False


def run_skill_flow(
    skills: List[SkillLike],
    documents_text: str,
    *,
    agent: Optional[Agent] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Execute main pipeline via Crew (sequential Tasks); then run conditional
    skills (e.g. denial letter, appeal drafter when decision == DENY) via
    agent.kickoff. Results stored in case_state.
    """
    case_state: Dict[str, Any] = {"documents": documents_text}

    # Skills that run in the Crew (no condition, not authoritative_web_search)
    crew_skills = [
        s for s in skills
        if s.name != "authoritative_web_search" and not s.condition
    ]
    denial_skill = next((s for s in skills if s.name == "pa_denial_letter_generator"), None)
    appeal_skill = next((s for s in skills if s.name == "pa_appeal_drafter"), None)

    if agent is None:
        agent = Agent(
            role="Prior authorization specialist",
            goal="Execute each prior authorization skill in order using only the provided documents and previous step outputs.",
            backstory=(
                "You are an administrative PA specialist. You follow skill instructions exactly and output only valid JSON as specified. "
                "You must use tools for validation and policy lookup. Do NOT assume facts without tool output."
            ),
            tools=get_pa_tools(),
            verbose=verbose,
        )

    # Build sequential Tasks for Crew
    tasks: List[Task] = []
    skill_names_in_order: List[str] = []
    for i, skill in enumerate(crew_skills):
        desc = _task_description_for_skill(skill, is_first=(i == 0))
        context = tasks[:i] if i > 0 else None
        t = Task(
            description=desc,
            expected_output="A single JSON object conforming to the required output schema. No other text.",
            agent=agent,
            context=context,
        )
        tasks.append(t)
        skill_names_in_order.append(skill.name)

    # Append ConditionalTasks for denial letter and appeal (only when decision == DENY)
    decision_task = tasks[-1] if tasks else None
    if denial_skill and decision_task:
        denial_desc = _task_description_for_skill(denial_skill, is_first=False)
        denial_task = ConditionalTask(
            description=denial_desc,
            expected_output="A single JSON object conforming to the required output schema. No other text.",
            agent=agent,
            context=[decision_task],
            condition=_is_deny,
        )
        tasks.append(denial_task)
        skill_names_in_order.append("pa_denial_letter_generator")
    if appeal_skill and tasks:
        appeal_desc = _task_description_for_skill(appeal_skill, is_first=False)
        denial_letter_task = tasks[-1]  # last added is denial letter task
        appeal_task = ConditionalTask(
            description=appeal_desc,
            expected_output="A single JSON object conforming to the required output schema. No other text.",
            agent=agent,
            context=[denial_letter_task],
            condition=_is_denial_output,
        )
        tasks.append(appeal_task)
        skill_names_in_order.append("pa_appeal_drafter")

    # Run Crew (sequential process, including conditional tasks)
    if tasks:
        if verbose:
            print("[EXEC] Crew (sequential):", ", ".join(skill_names_in_order))
        try:
            crew = Crew(agents=[agent], tasks=tasks, process=Process.sequential)
            result = crew.kickoff(inputs={"documents": documents_text})
            # Map task outputs to case_state (one output per task, same order)
            for i, task_output in enumerate(result.tasks_output):
                if i >= len(skill_names_in_order):
                    break
                skill_name = skill_names_in_order[i]
                raw = task_output.raw if hasattr(task_output, "raw") else str(task_output)
                # Skip empty outputs (conditional task was skipped)
                if not raw and skill_name in ("pa_denial_letter_generator", "pa_appeal_drafter"):
                    continue
                parsed = _parse_json_from_output(raw)
                if parsed is not None:
                    case_state[skill_name] = parsed
                    if verbose and _contains_unverified(parsed):
                        print(f"[FALLBACK] unverified in output for {skill_name}")
                else:
                    case_state[skill_name] = {"_raw": raw[:2000]}
        except Exception as e:
            if verbose:
                print(f"[ERROR] Crew: {e}")
            case_state["_crew_error"] = str(e)

    return case_state
