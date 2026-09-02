"""
Generates only the necessary clarifying questions from missing-field
metadata (spec section 5, section 8). Groups related questions together
instead of firing one question at a time.
"""
from __future__ import annotations
from typing import Dict, List

FIELD_QUESTIONS: Dict[str, str] = {
    "structure.host_material": "What is the host material (e.g. Fe, TiO2, graphene)?",
    "structure.surface_miller_index": "What Miller index surface should be used (e.g. 110, 100, 111)?",
    "structure.supercell": "What supercell size should be built (e.g. 3x3x1)?",
    "structure.slab_layers": "How many atomic layers should the slab have?",
    "structure.vacuum": "How much vacuum spacing, in Angstrom, should separate periodic slab images?",
    "doping.dopant": "Which element is the dopant?",
    "doping.type": "Is the doping substitutional or interstitial?",
    "doping.location": "Where should the dopant be placed (e.g. top layer, specific site)?",
    "doping.interstitial_strategy": "What interstitial-site placement strategy should be used (e.g. octahedral, tetrahedral)?",
    "adsorption.adsorbate": "Which molecule/atom should be adsorbed?",
    "adsorption.site": "What adsorption site should be used (top, bridge, hollow, other)?",
    "calculation.type": "What calculation type do you want: scf, relax, or vc-relax?",
    "calculation.xc_functional": "Which exchange-correlation functional should be used (e.g. PBE)?",
    "calculation.spin": "Should this be spin-polarized (collinear), non-collinear, or non-spin-polarized?",
}

GROUPS: List[List[str]] = [
    ["structure.host_material", "structure.surface_miller_index",
     "structure.supercell", "structure.slab_layers", "structure.vacuum"],
    ["doping.dopant", "doping.type", "doping.location", "doping.interstitial_strategy"],
    ["adsorption.adsorbate", "adsorption.site"],
    ["calculation.type", "calculation.xc_functional", "calculation.spin"],
]


def build_questions(missing_fields: List[str]) -> List[str]:
    """Return questions grouped in the order defined by GROUPS, only for
    fields that are actually missing, skipping empty groups entirely."""
    missing_set = set(missing_fields)
    questions: List[str] = []
    for group in GROUPS:
        group_qs = [FIELD_QUESTIONS[f] for f in group if f in missing_set]
        questions.extend(group_qs)
    return questions
