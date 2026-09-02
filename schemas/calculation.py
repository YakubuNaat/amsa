from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


class CalculationRequest(BaseModel):
    type: Optional[Literal["scf", "relax", "vc-relax"]] = None
    xc_functional: Optional[str] = Field(None, description="e.g. 'PBE'")
    kpoints: Optional[str] = Field(None, description="e.g. '4x4x1'")
    cutoffs: Optional[str] = Field(None, description="e.g. 'ecutwfc=60,ecutrho=480'")
    spin: Optional[str] = Field(None, description="'none', 'collinear', 'noncollinear'")
    smearing: Optional[str] = None
    convergence: Optional[str] = None
