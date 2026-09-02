from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from schemas.request import SimulationRequest
from schemas.simulation_plan import SimulationPlan


class AgentState(BaseModel):
    """Persists across the whole conversation so the LLM never has to
    re-parse the entire workflow from scratch (spec section 7)."""

    original_request: str
    extracted_request: Optional[SimulationRequest] = None
    missing_fields: List[str] = Field(default_factory=list)
    user_answers: Dict[str, Any] = Field(default_factory=dict)
    simulation_plan: Optional[SimulationPlan] = None
    validation_results: List[str] = Field(default_factory=list)
    structure_paths: Dict[str, str] = Field(default_factory=dict)
    pseudopotential_paths: Dict[str, str] = Field(default_factory=dict)
    qe_input_path: Optional[str] = None
    slurm_path: Optional[str] = None
    package_path: Optional[str] = None
    is_complete: bool = False
