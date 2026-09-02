# AMSA — Agentic Materials Simulation Assistant

AMSA turns a single natural-language request — *"Build a 3×3 Fe(110) slab with
substitutional Ni in the top layer and run a PBE relax"* — into a reproducible
Quantum ESPRESSO + SLURM project folder, ready for human review.

It's a **human-in-the-loop** agentic system built around one core principle:
**LLM reasoning is kept strictly separate from deterministic scientific
execution.** The LLM (via Groq's free API) only parses intent into a
structured request. Everything that actually matters scientifically —
structure construction, parameter selection, pseudopotential compatibility,
input-file generation — is done by deterministic Python (ASE, pymatgen,
rule-based logic), never guessed by the model.

The first version does **not** submit to an HPC cluster. It prepares
everything and hands the reviewed package back to a human.

## How it works

```
Natural-language request
        │
        ▼
LLM parses intent (Groq)  ──►  structured SimulationRequest
        │
        ▼
Deterministic completeness check ──► asks only for what's missing
        │
        ▼
ASE / pymatgen build the structure
        │
        ▼
Parameter engine resolves values (with full provenance: user / rule / derived)
        │
        ▼
Pseudopotential manager selects compatible UPF files
        │
        ▼
Quantum ESPRESSO input + SLURM script generated deterministically
        │
        ▼
Reproducible package: structure files + pw.in + job.slurm + metadata.json
        │
        ▼
Human reviews and submits manually
```

Full architecture rationale is in
[`AMSA_Architecture_Implementation_Design_Specification.docx`](./AMSA_Architecture_Implementation_Design_Specification.docx).

## Features

- Natural-language → structured `SimulationRequest` via Groq (free tier)
- Asks only for genuinely missing information, never re-asks what you already gave
- ASE/pymatgen structure builder: bulk, slabs, supercells, substitutional
  doping, adsorbate placement, layer constraints
- Rule-based parameter engine with full provenance tracking (`user` /
  `rule_recommendation` / `derived`)
- Pseudopotential source adapter (SSSP by default)
- Deterministic Quantum ESPRESSO (`pw.in`) and SLURM script generation via
  Jinja2 templates
- Reproducible output package with `metadata.json` and a per-run README
- Every generated parameter's origin is traceable — nothing is a silent guess

## Requirements

- Python 3.11
- A free [Groq API key](https://console.groq.com) (no credit card required)
- Conda/Miniforge (recommended) or a modern C/C++ toolchain if using plain pip

## Quick start

```bash
git clone https://github.com/YakubuNaat/amsa.git
cd amsa

# Recommended: conda avoids compiling scipy from source
conda env create -f environment.yml
conda activate amsa

# Add your Groq API key
cp .env.example .env
# edit .env: GROQ_API_KEY=gsk_...

python main.py "Build a 3x3 Fe(110) slab and run a PBE relax"
```

If you don't use conda, see [`environment.yml`](./environment.yml) vs.
[`requirements.txt`](./requirements.txt) — plain `pip install -r
requirements.txt` requires a modern compiler (SciPy ≥1.15 needs Clang ≥15)
and can fail on older systems.

## Manual steps required

By design, a few things need a human (or a second free account) rather than
being automated silently:

| Step | Why | What to do |
|---|---|---|
| **Pseudopotentials** | SSSP has no scripted bulk download | Download the [SSSP Efficiency library](https://www.materialscloud.org/discover/sssp/table/efficiency) and place `.UPF` files in `config/pseudopotentials/sssp_efficiency/` |
| **Compound bulk structures** (optional) | ASE's built-in `bulk()` only covers simple elemental lattices | Get a free [Materials Project API key](https://next-gen.materialsproject.org/api), set `MP_API_KEY` in `.env` |
| **Interstitial doping** | Site placement needs human/chemical judgment, not a guess | AMSA stops and explains; use pymatgen's `VoronoiInterstitialGenerator` and verify visually |
| **HPC/SLURM profile** | Partition names, modules, and executables vary per cluster | Edit `config/hpc_profiles.yaml` with your cluster's real values |
| **Final review** | Adsorbate-site placement is an approximation beyond simple terminations | Open `system.cif` in VESTA/OVITO/ASE GUI before running `sbatch job.slurm` |

AMSA never calls `sbatch` for you — you always review and submit manually.

## Project layout

```
amsa/
├── app/          # config & settings
├── agent/        # LangGraph orchestration, Groq parser, question routing
├── schemas/      # Pydantic request/plan schemas
├── services/     # structure builder, parameter engine, pseudopotential
│                   manager, QE/SLURM generators, package builder
├── validators/   # completeness, structure, and parameter validation
├── templates/    # Jinja2 templates for pw.in and job.slurm
├── config/       # defaults.yaml, hpc_profiles.yaml, pseudopotential sources
└── tests/        # pytest unit tests
```

## Status

Implements phases 1–9 of the project roadmap: schemas, LLM parsing,
completeness-driven clarification, structure building, parameter resolution
with provenance, pseudopotential selection, QE/SLURM generation, and
packaging.

Not yet implemented (intentionally, per the design spec): ML-based parameter
recommendation and automated HPC submission/monitoring.

## Tech stack

Python · [Groq API](https://console.groq.com) · [LangGraph](https://github.com/langchain-ai/langgraph) · [Pydantic](https://docs.pydantic.dev) · [ASE](https://wiki.fysik.dtu.dk/ase/) · [pymatgen](https://pymatgen.org) · [Quantum ESPRESSO](https://www.quantum-espresso.org) · Jinja2 · SLURM

## Contributing

Issues and PRs are welcome — this is an early-stage MVP. See the "Status"
section above for what's out of scope for now (ML recommendations, HPC
auto-submission).

## License

See [LICENSE](./LICENSE).
