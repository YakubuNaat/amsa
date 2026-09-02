"""
Deterministic completeness validator (spec section 4 & 8).
NEVER uses the LLM. Pure rule-based logic on the SimulationRequest.
"""
from __future__ import annotations
from typing import List

from schemas.request import SimulationRequest


def check_completeness(req: SimulationRequest) -> List[str]:
    missing: List[str] = []

    # Structure basics -- always required
    if not req.structure.host_material:
        missing.append("structure.host_material")

    # Surface calculation requirements
    is_surface = bool(req.structure.surface_miller_index) or bool(req.structure.slab_layers)
    if is_surface:
        if not req.structure.surface_miller_index:
            missing.append("structure.surface_miller_index")
        if not req.structure.supercell:
            missing.append("structure.supercell")
        if not req.structure.slab_layers:
            missing.append("structure.slab_layers")
        if req.structure.vacuum is None:
            missing.append("structure.vacuum")

    # Doping requirements
    if req.doping is not None:
        if not req.doping.dopant:
            missing.append("doping.dopant")
        if not req.doping.type:
            missing.append("doping.type")
        elif req.doping.type == "substitutional" and not req.doping.location:
            missing.append("doping.location")
        elif req.doping.type == "interstitial" and not req.doping.concentration_or_count:
            missing.append("doping.interstitial_strategy")

    # Adsorption requirements
    if req.adsorption is not None:
        if not req.adsorption.adsorbate:
            missing.append("adsorption.adsorbate")
        if not req.adsorption.site:
            missing.append("adsorption.site")

    # Calculation requirements
    if not req.calculation.type:
        missing.append("calculation.type")
    else:
        # SCF baseline
        if not req.calculation.xc_functional:
            missing.append("calculation.xc_functional")
        # relax / vc-relax inherit SCF requirements (handled by same field above)

    return missing
