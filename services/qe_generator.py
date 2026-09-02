"""
Quantum ESPRESSO Input Generator (spec section 12).
Deterministic Jinja2 rendering from a validated SimulationPlan + Atoms.
The LLM is never involved in writing pw.in.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from jinja2 import Environment, FileSystemLoader

from app.config import get_config
from schemas.simulation_plan import SimulationPlan

ATOMIC_MASSES = {
    "H": 1.008, "C": 12.011, "N": 14.007, "O": 15.999, "Fe": 55.845,
    "Ni": 58.693, "Cu": 63.546, "Al": 26.982, "Ti": 47.867, "Si": 28.085,
    # Extend as needed; ASE's ase.data.atomic_masses is a good fallback.
}


def _mass_for(symbol: str) -> float:
    if symbol in ATOMIC_MASSES:
        return ATOMIC_MASSES[symbol]
    try:
        from ase.data import atomic_numbers, atomic_masses
        return float(atomic_masses[atomic_numbers[symbol]])
    except Exception:
        return 1.0  # placeholder; flagged via warnings upstream


def generate_pw_input(atoms, plan: SimulationPlan, upf_paths: Dict[str, str],
                       output_path: Path, prefix: str = "amsa_calc") -> Path:
    cfg = get_config()
    env = Environment(loader=FileSystemLoader(str(cfg.templates_dir)),
                       trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("pw.in.j2")

    symbols_in_order = list(dict.fromkeys(atoms.get_chemical_symbols()))  # unique, ordered
    species = [
        {
            "symbol": s,
            "mass": _mass_for(s),
            "upf_filename": Path(upf_paths[s]).name,
        }
        for s in symbols_in_order if s in upf_paths
    ]

    fixed_indices = set()
    for c in atoms.constraints:
        if hasattr(c, "index"):
            fixed_indices.update(c.index)

    atom_rows = [
        {"symbol": sym, "x": pos[0], "y": pos[1], "z": pos[2], "fixed": i in fixed_indices}
        for i, (sym, pos) in enumerate(zip(atoms.get_chemical_symbols(), atoms.get_positions()))
    ]

    rendered = template.render(
        calculation_type=plan.get_param("calculation_type", "scf"),
        prefix=prefix,
        nat=len(atoms),
        ntyp=len(species),
        ecutwfc=plan.get_param("ecutwfc"),
        ecutrho=plan.get_param("ecutrho"),
        occupations=plan.get_param("occupations"),
        smearing=plan.get_param("smearing"),
        degauss=plan.get_param("degauss"),
        spin=plan.get_param("spin"),
        conv_thr=plan.get_param("conv_thr"),
        mixing_beta=plan.get_param("mixing_beta"),
        press_conv_thr=plan.get_param("press_conv_thr"),
        species=species,
        atoms=atom_rows,
        cell=atoms.get_cell().tolist(),
        kpoints=plan.get_param("kpoints", "4 4 1").replace("x", " "),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    return output_path
