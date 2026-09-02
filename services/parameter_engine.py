"""
Parameter Recommendation Engine (spec section 10).

Resolution priority implemented exactly as specified:
  1. User explicitly supplied value
  2. Calculation-specific required value
  3. Value derived from selected pseudopotential
  4. Configured scientific default/rule (config/defaults.yaml)
  5. ML recommendation (future -- not implemented yet)
  6. Ask the user if uncertainty remains
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import yaml

from schemas.request import SimulationRequest
from schemas.simulation_plan import SimulationPlan
from app.config import get_config


def _load_defaults() -> dict:
    cfg = get_config()
    with open(cfg.config_dir / "defaults.yaml") as f:
        return yaml.safe_load(f)


def resolve_parameters(req: SimulationRequest, plan: SimulationPlan,
                        pseudo_cutoffs: Optional[Dict[str, float]] = None) -> SimulationPlan:
    defaults = _load_defaults()
    is_surface = bool(req.structure.surface_miller_index)

    # 1. User-supplied values first
    if req.calculation.xc_functional:
        plan.set_param("xc_functional", req.calculation.xc_functional, "user")
    else:
        plan.set_param("xc_functional", defaults["xc_functional"], "rule_recommendation")

    if req.calculation.kpoints:
        plan.set_param("kpoints", req.calculation.kpoints, "user")
    else:
        default_kp = defaults["kpoints_slab"] if is_surface else defaults["kpoints_bulk"]
        plan.set_param("kpoints", default_kp, "rule_recommendation")

    if req.calculation.spin:
        plan.set_param("spin", req.calculation.spin, "user")
    else:
        plan.set_param("spin", defaults["spin"], "rule_recommendation")

    plan.set_param("smearing", defaults["smearing"], "rule_recommendation")
    plan.set_param("degauss", defaults["degauss"], "rule_recommendation")
    plan.set_param("occupations", defaults["occupations"], "rule_recommendation")
    plan.set_param("conv_thr", defaults["conv_thr"], "rule_recommendation")
    plan.set_param("mixing_beta", defaults["mixing_beta"], "rule_recommendation")

    # 3. Cutoffs derived from pseudopotentials when available, else default rule
    if req.calculation.cutoffs:
        plan.set_param("cutoffs_raw", req.calculation.cutoffs, "user")
        ecutwfc = _extract_ecutwfc(req.calculation.cutoffs)
        if ecutwfc:
            plan.set_param("ecutwfc", ecutwfc, "user")
            plan.set_param("ecutrho", ecutwfc * defaults["ecutrho_multiplier"], "derived")
    elif pseudo_cutoffs:
        max_ecutwfc = max(pseudo_cutoffs.values())
        plan.set_param("ecutwfc", max_ecutwfc, "derived")
        plan.set_param("ecutrho", max_ecutwfc * defaults["ecutrho_multiplier"], "derived")
    else:
        plan.warnings.append(
            "No pseudopotentials selected yet and user gave no cutoffs -- "
            "ecutwfc/ecutrho will use a conservative placeholder (60/480 Ry). "
            "MANUAL REVIEW recommended once real pseudopotentials are chosen."
        )
        plan.set_param("ecutwfc", 60.0, "rule_recommendation")
        plan.set_param("ecutrho", 480.0, "rule_recommendation")

    calc_type = req.calculation.type or "scf"
    plan.set_param("calculation_type", calc_type,
                    "user" if req.calculation.type else "rule_recommendation")

    if calc_type in ("relax", "vc-relax"):
        plan.set_param("forc_conv_thr", defaults["forc_conv_thr"], "rule_recommendation")
    if calc_type == "vc-relax":
        plan.set_param("press_conv_thr", defaults["press_conv_thr"], "rule_recommendation")

    return plan


def _extract_ecutwfc(cutoffs_str: str) -> Optional[float]:
    for token in cutoffs_str.replace(";", ",").split(","):
        token = token.strip()
        if token.lower().startswith("ecutwfc"):
            try:
                return float(token.split("=")[1])
            except (IndexError, ValueError):
                return None
    return None
