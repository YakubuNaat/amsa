"""
Structure Service (spec section 9). Wraps ASE and pymatgen to build bulk
material, slab, supercell, substitutional doping, and adsorbate placement.

Deterministic. No LLM calls happen anywhere in this file.

NOTE: bulk structure lookup uses pymatgen's MPRester (Materials Project),
which requires ITS OWN free API key -- separate from Groq. See the
"Manual steps" section in README.md. If no Materials Project key is
configured, this falls back to ASE's built-in bulk() generator, which
covers common elemental crystal structures (bcc/fcc/hcp/diamond) but not
arbitrary compounds.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from ase import Atoms
from ase.build import bulk, surface, add_adsorbate, molecule as ase_molecule
from ase.constraints import FixAtoms

from schemas.request import SimulationRequest


class StructureBuildError(RuntimeError):
    pass


def get_bulk_structure(host_material: str, crystal_structure: Optional[str]) -> Atoms:
    """
    Try Materials Project (pymatgen) first if MP_API_KEY is set, else fall
    back to ase.build.bulk for elemental lattices.
    """
    mp_key = os.environ.get("MP_API_KEY")
    if mp_key:
        try:
            from mp_api.client import MPRester
            with MPRester(mp_key) as mpr:
                docs = mpr.summary.search(formula=host_material, fields=["structure"])
                if docs:
                    pmg_structure = docs[0].structure
                    from pymatgen.io.ase import AseAtomsAdaptor
                    return AseAtomsAdaptor.get_atoms(pmg_structure)
        except Exception as e:
            # Fall through to ASE fallback rather than failing hard.
            print(f"[structure_builder] Materials Project lookup failed ({e}); "
                  f"falling back to ase.build.bulk.")

    # ASE fallback: works well for pure elements with a known crystal_structure
    try:
        kwargs = {}
        if crystal_structure:
            kwargs["crystalstructure"] = crystal_structure.lower()
        return bulk(host_material, **kwargs)
    except Exception as e:
        raise StructureBuildError(
            f"Could not build bulk structure for '{host_material}' "
            f"(crystal_structure={crystal_structure}). If this is a compound "
            f"(not a pure element), set MP_API_KEY to enable Materials Project "
            f"lookup, or supply a CIF manually. Original error: {e}"
        )


def _parse_miller(index_str: str) -> Tuple[int, int, int]:
    digits = [c for c in index_str if c.strip()]
    if len(digits) == 3 and all(c.lstrip("-").isdigit() for c in digits):
        return tuple(int(c) for c in digits)  # type: ignore
    # fallback: comma/space separated like "1 1 0" or "1,1,0"
    parts = [p for p in index_str.replace(",", " ").split() if p]
    if len(parts) == 3:
        return tuple(int(p) for p in parts)  # type: ignore
    raise StructureBuildError(f"Could not parse Miller index from '{index_str}'")


def build_slab(bulk_atoms: Atoms, miller_index: str, layers: int, vacuum: float) -> Atoms:
    hkl = _parse_miller(miller_index)
    try:
        slab = surface(bulk_atoms, hkl, layers, vacuum=vacuum / 2)
        slab.center(vacuum=vacuum / 2, axis=2)
        return slab
    except Exception as e:
        raise StructureBuildError(f"Failed to build ({miller_index}) slab: {e}")


def _parse_supercell(supercell_str: str) -> Tuple[int, int, int]:
    parts = supercell_str.lower().replace("x", " ").split()
    if len(parts) == 2:
        parts.append("1")
    if len(parts) != 3:
        raise StructureBuildError(f"Could not parse supercell '{supercell_str}' (expected e.g. '3x3x1')")
    return tuple(int(p) for p in parts)  # type: ignore


def apply_supercell(slab: Atoms, supercell_str: str) -> Atoms:
    nx, ny, nz = _parse_supercell(supercell_str)
    return slab.repeat((nx, ny, nz))


def apply_substitutional_doping(atoms: Atoms, dopant: str, location: str) -> Atoms:
    """
    Deterministic layer-based substitution: replaces one atom in the
    layer described by `location` (e.g. "top layer") with `dopant`.
    This is intentionally simple/explicit rather than "smart" -- the spec
    requires substitutional doping to come from deterministic layer/symmetry
    logic, not arbitrary LLM placement.
    """
    atoms = atoms.copy()
    z_coords = atoms.positions[:, 2]
    if "top" in location.lower():
        target_index = int(z_coords.argmax())
    elif "bottom" in location.lower():
        target_index = int(z_coords.argmin())
    else:
        raise StructureBuildError(
            f"Cannot automatically resolve doping location '{location}'. "
            f"MANUAL STEP REQUIRED: specify 'top layer' or 'bottom layer', "
            f"or edit the exported CIF/XYZ by hand to place the dopant."
        )
    atoms[target_index].symbol = dopant
    return atoms


def place_adsorbate(atoms: Atoms, adsorbate: str, site: str, height: Optional[float]) -> Atoms:
    """
    Places a molecule/atom above the slab. Uses ASE's g2 molecule database
    when the adsorbate name matches a known molecule (e.g. 'CO2', 'H2O');
    otherwise treats it as a single atom.

    NOTE: exact (x, y) site coordinates for 'top'/'bridge'/'hollow' depend
    on the specific surface geometry. This function computes an approximate
    site from the slab's top-layer atom positions. For anything beyond the
    simplest terminations, MANUAL VERIFICATION of the adsorbate position in
    a visualizer (e.g. VESTA, OVITO, ASE GUI) is recommended before
    submitting the QE job -- flagged again in structure_validator output.
    """
    atoms = atoms.copy()
    height = height if height is not None else 2.0

    try:
        ads = ase_molecule(adsorbate)
    except Exception:
        ads = Atoms(adsorbate)  # single atom fallback

    top_z = atoms.positions[:, 2].max()
    surface_atoms_idx = [i for i, p in enumerate(atoms.positions) if abs(p[2] - top_z) < 0.5]

    import numpy as np
    if site == "top" and surface_atoms_idx:
        anchor = atoms.positions[surface_atoms_idx[0]][:2]
    elif site in ("bridge", "hollow") and len(surface_atoms_idx) >= 2:
        pts = np.array([atoms.positions[i][:2] for i in surface_atoms_idx[:3 if site == "hollow" else 2]])
        anchor = pts.mean(axis=0)
    else:
        anchor = atoms.positions[surface_atoms_idx[0]][:2] if surface_atoms_idx else atoms.get_center_of_mass()[:2]

    add_adsorbate(atoms, ads, height=height, position=tuple(anchor))
    return atoms


def apply_slab_constraints(atoms: Atoms, fixed_layers_from_bottom: int = 1) -> Atoms:
    """Fix the bottom N layers, per spec section 9 constraints row."""
    atoms = atoms.copy()
    z = atoms.positions[:, 2]
    threshold = sorted(set(round(v, 2) for v in z))[:fixed_layers_from_bottom]
    if not threshold:
        return atoms
    max_fixed_z = max(threshold) + 0.3
    fixed_indices = [i for i, p in enumerate(atoms.positions) if p[2] <= max_fixed_z]
    atoms.set_constraint(FixAtoms(indices=fixed_indices))
    return atoms


def build_full_structure(req: SimulationRequest) -> Atoms:
    """Top-level orchestration matching spec Step 7."""
    if not req.structure.host_material:
        raise StructureBuildError("host_material is required to build a structure.")

    atoms = get_bulk_structure(req.structure.host_material, req.structure.crystal_structure)

    is_surface = bool(req.structure.surface_miller_index)
    if is_surface:
        layers = req.structure.slab_layers or 4
        vacuum = req.structure.vacuum if req.structure.vacuum is not None else 15.0
        atoms = build_slab(atoms, req.structure.surface_miller_index, layers, vacuum)

    if req.structure.supercell:
        atoms = apply_supercell(atoms, req.structure.supercell)

    if req.doping and req.doping.type == "substitutional" and req.doping.dopant and req.doping.location:
        atoms = apply_substitutional_doping(atoms, req.doping.dopant, req.doping.location)
    elif req.doping and req.doping.type == "interstitial":
        raise StructureBuildError(
            "MANUAL STEP REQUIRED: interstitial doping needs pymatgen's "
            "interstitial site-generation (e.g. VoronoiInterstitialGenerator), "
            "reviewed by a human before acceptance -- not yet automated here. "
            "Build the slab/bulk first, then insert the interstitial atom manually."
        )

    if req.adsorption and req.adsorption.adsorbate and req.adsorption.site:
        atoms = place_adsorbate(atoms, req.adsorption.adsorbate, req.adsorption.site,
                                 req.adsorption.initial_height)

    if is_surface:
        atoms = apply_slab_constraints(atoms, fixed_layers_from_bottom=1)

    return atoms
