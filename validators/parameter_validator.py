"""
Deterministic parameter sanity checks (spec section 10 / 12).
"""
from __future__ import annotations
from typing import List
from schemas.simulation_plan import SimulationPlan


def validate_parameters(plan: SimulationPlan) -> List[str]:
    problems: List[str] = []

    ecutwfc = plan.get_param("ecutwfc")
    ecutrho = plan.get_param("ecutrho")
    if ecutwfc is not None and ecutrho is not None:
        if ecutrho < ecutwfc:
            problems.append(
                f"ecutrho ({ecutrho}) is smaller than ecutwfc ({ecutwfc}); "
                "ecutrho should normally be >= ecutwfc (often 4x-10x for norm-conserving PPs)."
            )

    calc_type = plan.request.calculation.type
    if calc_type in ("relax", "vc-relax") and plan.get_param("forc_conv_thr") is None:
        problems.append("Missing force convergence threshold (forc_conv_thr) for ionic relaxation.")

    if calc_type == "vc-relax" and plan.get_param("press_conv_thr") is None:
        problems.append("Missing pressure convergence threshold (press_conv_thr) for cell relaxation.")

    return problems
