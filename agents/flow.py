"""
Prior Authorization Flow: CrewAI Flow wrapper with typed state.

@start() loads documents (from kickoff inputs); @listen() runs the PA Crew
and stores results in state. main.py can kickoff with inputs={"documents": pdf_text}
and read flow.state for the same case_state shape as run_skill_flow.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from crewai.flow.flow import Flow, listen, start

from agents.runner import run_skill_flow

# Skill type from skill_loader (duck typing)
SkillLike = Any


class PAState(BaseModel):
    """Typed state for the PA flow; matches case_state shape for main.py."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Flow state ID")
    documents: str = Field(default="", description="Raw document text")
    pa_case_normalizer: Optional[Dict[str, Any]] = None
    pa_coverage_eligibility: Optional[Dict[str, Any]] = None
    pa_medical_necessity: Optional[Dict[str, Any]] = None
    pa_coding_provider_validation: Optional[Dict[str, Any]] = None
    pa_decision_engine: Optional[Dict[str, Any]] = None
    pa_denial_letter_generator: Optional[Dict[str, Any]] = None
    pa_appeal_drafter: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}  # Allow _crew_error and other runtime keys


class PAFlow(Flow[PAState]):
    """Flow that runs the PA Crew and stores results in PAState."""

    initial_state = PAState(documents="")

    def __init__(
        self,
        skills: List[SkillLike],
        *,
        verbose: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._skills = skills
        self._verbose = verbose

    @start()
    def load_documents(self) -> str:
        """Entry point; documents are set via kickoff(inputs={"documents": ...})."""
        return self.state.documents or ""

    @listen(load_documents)
    def run_pa_crew(self, _: str) -> Dict[str, Any]:
        """Run the PA Crew (sequential + conditional tasks) and store result in state."""
        documents_text = self.state.documents or ""
        case_state = run_skill_flow(
            self._skills,
            documents_text,
            verbose=self._verbose,
        )
        # Update state with all case_state keys (same shape as runner contract)
        for k, v in case_state.items():
            setattr(self.state, k, v)
        return case_state

    def case_state(self) -> Dict[str, Any]:
        """Return state as a dict matching run_skill_flow() for main.py compatibility."""
        return self.state.model_dump()
