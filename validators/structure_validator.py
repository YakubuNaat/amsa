"""
Deterministic structure validation (spec section 10).
Runs AFTER ASE/pymatgen build the structure, before export.
"""
from __future__ import annotations
from typing import List

MIN_INTERATOMIC_DISTANCE_ANGSTROM = 0.7


def validate_structure(atoms) -> List[str]:
    """atoms: an ase.Atoms object. Returns a list of warning/error strings."""
    problems: List[str] = []
    try:
        distances = atoms.get_all_distances(mic=True)
    except Exception as e:  # pragma: no cover - defensive
        return [f"Could not compute interatomic distances: {e}"]

    n = len(atoms)
    for i in range(n):
        for j in range(i + 1, n):
            d = distances[i][j]
            if d < MIN_INTERATOMIC_DISTANCE_ANGSTROM:
                problems.append(
                    f"Atoms {i} ({atoms[i].symbol}) and {j} ({atoms[j].symbol}) "
                    f"are only {d:.2f} A apart (< {MIN_INTERATOMIC_DISTANCE_ANGSTROM} A)."
                )

    cell = atoms.get_cell()
    if cell.volume <= 0:
        problems.append("Cell volume is non-positive; check the cell definition.")

    return problems
