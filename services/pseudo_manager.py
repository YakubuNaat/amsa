"""
Pseudopotential Manager (spec section 11).

Implements a source-adapter pattern so one library (SSSP by default) is
supported now, with room to add others later without touching the agent.

*** MANUAL STEP REQUIRED ***
This code expects UPF files to already exist in the local cache directory
configured in config/pseudopotential_sources.yaml. SSSP does not provide a
stable scripted bulk-download endpoint, so:
  1. Go to https://www.materialscloud.org/discover/sssp/table/efficiency
  2. Download the SSSP Efficiency (or Precision) library archive
  3. Unzip it into config/pseudopotentials/sssp_efficiency/
     (one .UPF file per element, named e.g. Fe.upf, O.upf, C.upf ...)
This manager will then find, verify, and register them automatically.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml

from app.config import get_config


class PseudopotentialError(RuntimeError):
    pass


def _load_source_config() -> dict:
    cfg = get_config()
    with open(cfg.config_dir / "pseudopotential_sources.yaml") as f:
        full = yaml.safe_load(f)
    active = full["active_source"]
    return full["sources"][active]


def _find_upf(cache_dir: Path, element: str) -> Optional[Path]:
    if not cache_dir.exists():
        return None
    # SSSP filenames vary in casing/suffix conventions across releases,
    # so match case-insensitively on the element symbol prefix.
    for f in cache_dir.glob("*.[Uu][Pp][Ff]"):
        stem = f.stem.split("_")[0].split(".")[0]
        if stem.lower() == element.lower():
            return f
    return None


def select_pseudopotentials(elements: List[str]) -> Dict[str, str]:
    """Returns {element_symbol: absolute_filepath}. Raises with a clear
    manual-action message if any pseudopotential is missing locally."""
    source = _load_source_config()
    cache_dir = Path(source["local_cache_dir"]).resolve()

    resolved: Dict[str, str] = {}
    missing: List[str] = []

    for el in sorted(set(elements)):
        upf_path = _find_upf(cache_dir, el)
        if upf_path is None:
            missing.append(el)
        else:
            resolved[el] = str(upf_path)

    if missing:
        raise PseudopotentialError(
            f"MANUAL STEP REQUIRED: missing pseudopotentials for {missing} in "
            f"'{cache_dir}'. Download the {source['name']} library from "
            f"https://www.materialscloud.org/discover/sssp/table/efficiency "
            f"and place the .UPF files for these elements in that folder, "
            f"then re-run."
        )

    return resolved


def cutoffs_from_upf_comments(upf_paths: Dict[str, str]) -> Dict[str, float]:
    """
    Best-effort: many SSSP UPF files include a suggested cutoff in a comment
    or header field. If not parseable, the caller (parameter_engine) falls
    back to config defaults, so this never blocks the pipeline.
    """
    cutoffs: Dict[str, float] = {}
    for element, path in upf_paths.items():
        try:
            with open(path, errors="ignore") as f:
                content = f.read(4000)
            for line in content.splitlines():
                if "cutoff" in line.lower() and any(c.isdigit() for c in line):
                    digits = "".join(c if (c.isdigit() or c == ".") else " " for c in line)
                    nums = [float(x) for x in digits.split() if x]
                    if nums:
                        cutoffs[element] = max(nums)
                        break
        except Exception:
            continue
    return cutoffs
