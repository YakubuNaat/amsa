# AMSA — Agentic Materials Simulation Assistant

Implementation of the architecture in `AMSA_Architecture_Implementation_Design_Specification.docx`,
using **Groq** (free tier) as the LLM for the interpretation layer, with everything
scientific (structure building, parameters, pseudopotentials, QE/SLURM files)
done deterministically in Python — never by the LLM.

## 1. Get a free Groq API key (required)

1. Go to **https://console.groq.com** and sign up (email only, no credit card).
2. Verify your email.
3. In the left sidebar, open **API Keys**.
4. Click **Create API Key**, name it (e.g. `amsa-dev`), and copy it immediately —
   Groq only shows it once. Keys look like `gsk_...`.
5. Free tier gives you access to all models with rate limits (roughly 30
   requests/minute and a daily token cap) — plenty for this project.

Then:

```bash
cp .env.example .env
# edit .env and paste your key:
# GROQ_API_KEY=gsk_...
```

The default model is `llama-3.3-70b-versatile` (good accuracy/speed balance).
You can swap to a faster/smaller one (e.g. `openai/gpt-oss-20b`) by setting
`GROQ_MODEL` in `.env` — see https://console.groq.com/docs/models for the
current list, since Groq adds/retires models over time.

## 2. Install dependencies

### Recommended: conda / miniforge (avoids compiling scipy from source)
If you don't have conda yet, install **Miniforge** (free, no license issues):
https://github.com/conda-forge/miniforge#download

```bash
conda env create -f environment.yml
conda activate amsa
```

This installs numpy/scipy/ase/pymatgen as prebuilt conda-forge binaries (no
C compiler involved at all), then installs Groq/LangGraph/LangChain via pip
*inside* that same environment (those don't have conda-forge builds).

### Alternative: plain pip + venv
Only do this if you have a modern C/C++ toolchain (e.g. Xcode ≥15 command
line tools on macOS, or build-essential on Linux) — pip will otherwise try
to compile scipy from source and can fail like:
`SciPy requires clang >= 15.0`.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3. Run it

```bash
python main.py "Build a 3x3 Fe(110) slab and run a PBE relax"
```

The agent will:
- call Groq to parse your sentence into a structured `SimulationRequest`
- ask you (in the terminal) only for whatever's missing
- build the structure with ASE, resolve parameters, select pseudopotentials
- write a reproducible package to `output/<name>/`

Review `output/<name>/README.md` inside the generated package before doing
anything with the SLURM script.

---

## 4. Parts YOU must do manually

This spec (section 19) deliberately keeps the LLM out of anything
scientifically consequential. A few pieces genuinely need a human, or a
second free account, before the pipeline is fully useful:

### 4a. Pseudopotentials (required before QE generation will succeed)
`services/pseudo_manager.py` expects `.UPF` files to already be sitting in
`config/pseudopotentials/sssp_efficiency/`. Groq has nothing to do with
pseudopotentials, and SSSP doesn't offer a stable scripted bulk-download.
**Manual step:**
1. Go to https://www.materialscloud.org/discover/sssp/table/efficiency
2. Download the SSSP Efficiency (or Precision) library archive (free, no
   account needed for the download itself).
3. Unzip so each element has its own file, e.g.
   `config/pseudopotentials/sssp_efficiency/Fe.upf`, `O.upf`, etc.

If a pseudopotential is missing, `main.py` will stop and tell you exactly
which element is unresolved rather than guessing.

### 4b. Bulk structures for compounds (optional but recommended)
`ase.build.bulk()` (the built-in fallback) only knows simple elemental
lattices (bcc/fcc/hcp/diamond/etc.). For real compounds (oxides, alloys,
minerals...), the code tries the Materials Project API instead.
**Manual step (optional, also free):**
1. Get a free API key at https://next-gen.materialsproject.org/api
2. Add to `.env`: `MP_API_KEY=your_key_here`
3. `pip install mp-api pymatgen` (pymatgen is already in requirements.txt)

Without this, requests for compounds AMSA can't find will raise a clear
`StructureBuildError` telling you to supply a CIF by hand instead.

### 4c. Interstitial doping
Deliberately **not automated**. The spec calls for
"pymatgen + validation... avoid arbitrary placement" — this needs a human
to pick/verify a chemically sensible interstitial site (e.g. via
pymatgen's `VoronoiInterstitialGenerator`, then visual check). If your
request includes interstitial doping, AMSA will build everything else and
stop with instructions rather than guess a site.

### 4d. HPC-specific SLURM details
`config/hpc_profiles.yaml` ships with placeholder values (partition name,
module names, executable path). **Manual step:** ask your cluster admin
for the real partition name, the correct `module load` line for Quantum
ESPRESSO, and update that YAML file. AMSA will never submit the job for
you (per spec section 19) — you run `sbatch job.slurm` yourself after
reviewing it.

### 4e. Visual inspection before submission
Always open `output/<name>/00_structure/system.cif` in a visualizer
(VESTA, OVITO, or `ase gui system.cif`) before submitting. AMSA validates
interatomic distances and cell sanity automatically, but adsorbate-site
placement in particular is an approximation for anything beyond simple
terminations — worth a human glance.

---

## 5. What's implemented vs. roadmap

Implemented (Phases 1–9 of the spec's roadmap, section 15):
schemas, Groq-based parsing, completeness validation + targeted questions,
ASE/pymatgen structure builder (bulk/slab/supercell/substitutional
doping/adsorbate placement/constraints), rule-based parameter engine with
provenance tracking, pseudopotential source adapter, deterministic QE and
SLURM generation, and packaging with metadata.json + README.

Not yet implemented (later roadmap phases, intentionally):
ML-based parameter recommendation (Phase 11), automated HPC submission and
monitoring (Phase 12). Interstitial doping site-generation is scaffolded
but requires the manual step above (4c).

## 6. Project layout

See `AMSA_Architecture_Implementation_Design_Specification.docx` section 5
for the full rationale; the code mirrors it 1:1 (`app/`, `agent/`,
`schemas/`, `services/`, `validators/`, `templates/`, `config/`, `tests/`).
