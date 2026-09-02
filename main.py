#!/usr/bin/env python3
"""
AMSA CLI entrypoint -- runs the full spec Section 3 workflow for ONE
natural-language request, asking follow-up questions in the terminal
if information is missing, then producing a reproducible package under
./output/<simulation_name>/.

Usage:
    python main.py "Build a 3x3 Fe(110) slab and run a PBE relax"
"""
from __future__ import annotations

import sys

from agent.state import AgentState
from agent.parser import parse_user_request
from agent.question_router import build_questions
from validators.completeness import check_completeness
from agent.graph import node_build_plan_and_structure, node_export_and_generate


FIELD_SETTERS = {
    "structure.host_material": lambda req, v: setattr(req.structure, "host_material", v),
    "structure.surface_miller_index": lambda req, v: setattr(req.structure, "surface_miller_index", v),
    "structure.supercell": lambda req, v: setattr(req.structure, "supercell", v),
    "structure.slab_layers": lambda req, v: setattr(req.structure, "slab_layers", int(v)),
    "structure.vacuum": lambda req, v: setattr(req.structure, "vacuum", float(v)),
    "calculation.type": lambda req, v: setattr(req.calculation, "type", v),
    "calculation.xc_functional": lambda req, v: setattr(req.calculation, "xc_functional", v),
    "calculation.spin": lambda req, v: setattr(req.calculation, "spin", v),
}


def run(raw_text: str) -> None:
    state = AgentState(original_request=raw_text)
    state.extracted_request = parse_user_request(raw_text)

    # Loop: ask only for what's missing, merge answers, re-validate.
    while True:
        state.missing_fields = check_completeness(state.extracted_request)
        if not state.missing_fields:
            break
        print("\nA few details are needed before AMSA can build this simulation:\n")
        for field, question in zip(state.missing_fields, build_questions(state.missing_fields)):
            answer = input(f"  {question} ")
            setter = FIELD_SETTERS.get(field)
            if setter:
                setter(state.extracted_request, answer)
            else:
                print(f"    (No automatic setter for '{field}' yet -- edit the structure "
                      f"or the exported files manually after generation.)")

    print("\nRequest is complete. Building structure, resolving parameters, "
          "selecting pseudopotentials...\n")

    state = node_build_plan_and_structure(state)
    if state.simulation_plan.warnings:
        print("Warnings raised during build:")
        for w in state.simulation_plan.warnings:
            print(f"  - {w}")

    state = node_export_and_generate(state)

    print(f"\nDone. Reproducible package written to: {state.package_path}")
    print("Review 00_structure/*.cif in a visualizer before submitting job.slurm.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python main.py "your natural language simulation request"')
        sys.exit(1)
    run(" ".join(sys.argv[1:]))
