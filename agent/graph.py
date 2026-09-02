"""
Agent Orchestrator (spec section 2 & 4). Implemented as a LangGraph state
machine matching the runtime workflow in spec section 3.

This module exposes plain functions for each node PLUS a compiled
LangGraph graph, so it can be used either as "real" LangGraph orchestration
or called step-by-step from a simple CLI (see main.py) if you'd rather not
stand up LangGraph immediately.
"""
from __future__ import annotations

from pathlib import Path

from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.parser import parse_user_request
from agent.question_router import build_questions
from validators.completeness import check_completeness
from services import structure_builder, parameter_engine, pseudo_manager
from services import qe_generator, slurm_generator, package_builder
from validators.structure_validator import validate_structure
from validators.parameter_validator import validate_parameters
from schemas.simulation_plan import SimulationPlan
from app.config import get_config


def node_parse(state: AgentState) -> AgentState:
    state.extracted_request = parse_user_request(state.original_request)
    return state


def node_check_completeness(state: AgentState) -> AgentState:
    state.missing_fields = check_completeness(state.extracted_request)
    state.is_complete = len(state.missing_fields) == 0
    return state


def node_ask_questions(state: AgentState) -> AgentState:
    """In interactive use, this just records the questions to display;
    main.py handles the actual terminal prompt / answer merge loop."""
    state.validation_results.append(
        "QUESTIONS: " + " | ".join(build_questions(state.missing_fields))
    )
    return state


def node_build_plan_and_structure(state: AgentState) -> AgentState:
    req = state.extracted_request
    plan = SimulationPlan(request=req)

    atoms = structure_builder.build_full_structure(req)
    elements = sorted(set(atoms.get_chemical_symbols()))

    upf_paths = pseudo_manager.select_pseudopotentials(elements)
    derived_cutoffs = pseudo_manager.cutoffs_from_upf_comments(upf_paths)

    plan = parameter_engine.resolve_parameters(req, plan, derived_cutoffs)

    struct_problems = validate_structure(atoms)
    param_problems = validate_parameters(plan)
    plan.warnings.extend(struct_problems + param_problems)

    state.simulation_plan = plan
    state.pseudopotential_paths = upf_paths
    state._atoms = atoms  # type: ignore[attr-defined]
    return state


def node_export_and_generate(state: AgentState) -> AgentState:
    cfg = get_config()
    atoms = state._atoms  # type: ignore[attr-defined]
    plan = state.simulation_plan

    sim_name = (plan.request.structure.host_material or "simulation").replace(" ", "_")
    work_dir = cfg.output_dir / "_staging" / sim_name
    work_dir.mkdir(parents=True, exist_ok=True)

    cif_path = work_dir / "system.cif"
    xyz_path = work_dir / "system.xyz"
    vasp_path = work_dir / "system.vasp"
    atoms.write(cif_path)
    atoms.write(xyz_path)
    atoms.write(vasp_path, format="vasp")
    state.structure_paths = {"cif": str(cif_path), "xyz": str(xyz_path), "vasp": str(vasp_path)}

    pw_in_path = qe_generator.generate_pw_input(
        atoms, plan, state.pseudopotential_paths, work_dir / "pw.in"
    )
    state.qe_input_path = str(pw_in_path)

    slurm_path = slurm_generator.generate_slurm_script(
        job_name=sim_name, input_file="pw.in", output_path=work_dir / "job.slurm"
    )
    state.slurm_path = str(slurm_path)

    package_root = package_builder.build_package(
        simulation_name=sim_name,
        output_root=cfg.output_dir,
        plan=plan,
        structure_files={"cif": cif_path, "xyz": xyz_path, "vasp": vasp_path},
        pw_in_path=pw_in_path,
        upf_paths=state.pseudopotential_paths,
        slurm_path=slurm_path,
    )
    state.package_path = str(package_root)
    return state


def route_after_completeness(state: AgentState) -> str:
    return "ask_questions" if not state.is_complete else "build_plan_and_structure"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("parse", node_parse)
    graph.add_node("check_completeness", node_check_completeness)
    graph.add_node("ask_questions", node_ask_questions)
    graph.add_node("build_plan_and_structure", node_build_plan_and_structure)
    graph.add_node("export_and_generate", node_export_and_generate)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "check_completeness")
    graph.add_conditional_edges(
        "check_completeness", route_after_completeness,
        {"ask_questions": "ask_questions", "build_plan_and_structure": "build_plan_and_structure"},
    )
    graph.add_edge("ask_questions", END)  # pause for human answers (spec Step 5)
    graph.add_edge("build_plan_and_structure", "export_and_generate")
    graph.add_edge("export_and_generate", END)

    return graph.compile()
