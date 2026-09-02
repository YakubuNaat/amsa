"""
SimulationPlan: the fully-resolved internal plan (spec section 6, 7).
Every parameter tracks its provenance per spec section 6.2.
"""
from __future__ import annotations
from typing import Optional, Literal, Any, Dict, List
from pydantic import BaseModel, Field

from schemas.request import SimulationRequest

ProvenanceSource = Literal["user", "rule_recommendation", "derived", "ml_recommendation"]


class ProvenancedValue(BaseModel):
    value: Any
    source: ProvenanceSource
    confidence: Optional[float] = None


class SimulationPlan(BaseModel):
    request: SimulationRequest
    resolved_parameters: Dict[str, ProvenancedValue] = Field(default_factory=dict)
    pseudopotentials: Dict[str, str] = Field(default_factory=dict)  # element -> filepath
    structure_paths: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

    def set_param(self, name: str, value: Any, source: ProvenanceSource,
                  confidence: Optional[float] = None) -> None:
        self.resolved_parameters[name] = ProvenancedValue(
            value=value, source=source, confidence=confidence
        )

    def get_param(self, name: str, default: Any = None) -> Any:
        pv = self.resolved_parameters.get(name)
        return pv.value if pv is not None else default
