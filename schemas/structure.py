from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


class StructureRequest(BaseModel):
    host_material: Optional[str] = Field(None, description="e.g. 'Fe', 'TiO2', 'graphene'")
    crystal_structure: Optional[str] = Field(None, description="e.g. 'bcc', 'fcc', 'rutile'")
    surface_miller_index: Optional[str] = Field(None, description="e.g. '110', '100'")
    supercell: Optional[str] = Field(None, description="e.g. '3x3x1'")
    slab_layers: Optional[int] = None
    vacuum: Optional[float] = Field(None, description="Vacuum thickness in Angstrom")


class DopingRequest(BaseModel):
    dopant: Optional[str] = None
    type: Optional[Literal["substitutional", "interstitial"]] = None
    location: Optional[str] = Field(None, description="e.g. 'top layer'")
    concentration_or_count: Optional[str] = None


class AdsorptionRequest(BaseModel):
    adsorbate: Optional[str] = None
    site: Optional[Literal["top", "bridge", "hollow", "other"]] = None
    orientation: Optional[str] = None
    initial_height: Optional[float] = Field(None, description="Angstrom above surface")
