"""
SimulationRequest: the LLM-facing schema described in spec section 6.1.

The LLM must populate this schema and MUST NOT invent values for fields
it cannot infer from the user's statement -- those stay null and get
picked up by the completeness validator.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

from schemas.structure import StructureRequest, DopingRequest, AdsorptionRequest
from schemas.calculation import CalculationRequest


class SimulationRequest(BaseModel):
    raw_user_text: str
    structure: StructureRequest = Field(default_factory=StructureRequest)
    doping: Optional[DopingRequest] = None
    adsorption: Optional[AdsorptionRequest] = None
    calculation: CalculationRequest = Field(default_factory=CalculationRequest)

    class Config:
        extra = "forbid"
