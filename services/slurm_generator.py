"""
SLURM Generator (spec section 13). Uses configurable HPC profiles rather
than hardcoding machine-specific commands (config/hpc_profiles.yaml).
Generates only -- never submits (spec section 19).
"""
from __future__ import annotations

from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from app.config import get_config


def generate_slurm_script(job_name: str, input_file: str, output_path: Path,
                           profile_name: str | None = None) -> Path:
    cfg = get_config()
    with open(cfg.config_dir / "hpc_profiles.yaml") as f:
        hpc_cfg = yaml.safe_load(f)

    profile_name = profile_name or hpc_cfg["active_profile"]
    profile = hpc_cfg["profiles"][profile_name]

    env = Environment(loader=FileSystemLoader(str(cfg.templates_dir)),
                       trim_blocks=True, lstrip_blocks=True)
    template = env.get_template("job.slurm.j2")

    rendered = template.render(
        job_name=job_name,
        partition=profile["partition"],
        nodes=profile["nodes"],
        ntasks_per_node=profile["ntasks_per_node"],
        walltime=profile["walltime"],
        memory=profile["memory"],
        modules=profile["modules"],
        qe_exec=profile["qe_exec"],
        input_file=input_file,
        output_file=input_file.replace(".in", ".out"),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    return output_path
