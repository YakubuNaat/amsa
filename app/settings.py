"""
Non-secret, hardcoded runtime constants. Anything a researcher should be able
to tune per-run belongs in config/*.yaml, not here.
"""

SUPPORTED_CALC_TYPES = ["scf", "relax", "vc-relax"]
SUPPORTED_XC = ["PBE", "PBEsol", "LDA"]
ADSORPTION_SITES = ["top", "bridge", "hollow", "other"]
DOPING_TYPES = ["substitutional", "interstitial"]

DEFAULT_VACUUM_ANGSTROM = 15.0
DEFAULT_SLAB_LAYERS = 4
