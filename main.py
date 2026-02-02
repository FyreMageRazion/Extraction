"""
Healthcare Prior Authorization POC — skill-driven agentic flow.

1. Ingests PDFs from ./inputs/ (or ./input/ if inputs/ empty)
2. Normalizes them via pa_case_normalizer
3. Applies coverage, medical necessity, coding validation, then decision
4. If DENY: runs denial letter generator and appeal drafter
5. Prints normalized case, decision, and (if denied) appeal letter + missing evidence

Skills in ./skills/ define WHAT to do, WHEN, ROLE, INSTRUCTIONS, and INPUT/OUTPUT
schemas. The code reads and uses these .md files to guide the flow; they are
NOT executable tools.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from agents.flow import PAFlow
from utils.pdf_loader import load_pdfs_from_directory
from utils.skill_loader import load_skills_from_dir

# Load env (e.g. OPENAI_API_KEY)
load_dotenv()

# Paths: inputs/ per spec; fallback to input/ if inputs/ missing or empty
PROJECT_ROOT = Path(__file__).resolve().parent
SKILLS_DIR = PROJECT_ROOT / "skills"
INPUTS_DIR = PROJECT_ROOT / "inputs"
FALLBACK_INPUT_DIR = PROJECT_ROOT / "input"


def main() -> None:
    # 1. Load skills (living specs — execution order and conditions from .md)
    skills = load_skills_from_dir(SKILLS_DIR)
    if not skills:
        print("No skills found in", SKILLS_DIR)
        return

    # 2. Load PDFs — raw text goes ONLY to pa_case_normalizer
    pdf_text = load_pdfs_from_directory(
        INPUTS_DIR,
        fallback_directory=FALLBACK_INPUT_DIR,
    )
    if not pdf_text.strip():
        pdf_text = load_pdfs_from_directory(FALLBACK_INPUT_DIR)
    if not pdf_text.strip():
        print("No PDF text found in", INPUTS_DIR, "or", FALLBACK_INPUT_DIR)
        return

    # 3. Run PA flow (Crew + ConditionalTasks; state in PAFlow)
    flow = PAFlow(skills, verbose=True)
    flow.kickoff(inputs={"documents": pdf_text})
    case_state = flow.case_state()

    # 4. Output: normalized case, decision, and if DENY — appeal letter + missing evidence
    normalized = case_state.get("pa_case_normalizer")
    if normalized and "_error" not in normalized:
        print("\n--- Normalized case JSON ---")
        print(json.dumps(normalized, indent=2, default=str))

    decision_out = case_state.get("pa_decision_engine")
    if decision_out and "_error" not in decision_out:
        print("\n--- Decision output ---")
        print(json.dumps(decision_out, indent=2, default=str))

    decision = (decision_out or {}).get("decision") if decision_out else None
    if decision == "DENY":
        denial = case_state.get("pa_denial_letter_generator")
        if denial and "_error" not in denial and "denial_letter" in denial:
            print("\n--- Denial letter ---")
            print(denial["denial_letter"])

        appeal = case_state.get("pa_appeal_drafter")
        if appeal and "_error" not in appeal:
            if "appeal_letter" in appeal:
                print("\n--- Appeal letter ---")
                print(appeal["appeal_letter"])
            if "missing_evidence" in appeal:
                print("\n--- Missing evidence list ---")
                print(json.dumps(appeal["missing_evidence"], indent=2, default=str))


if __name__ == "__main__":
    main()
