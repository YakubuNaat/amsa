"""
LLM Interpretation Layer (spec section 3, Step 2-3).

Calls Groq's OpenAI-compatible chat completions endpoint and forces the
model to return ONLY a JSON object matching SimulationRequest. The LLM
NEVER invents values -- the prompt explicitly instructs it to leave
unknown fields null, and this file does not fill in any defaults itself
(that is the Parameter Engine's job, later, with tracked provenance).
"""
from __future__ import annotations

import json
import re

from groq import Groq

from app.config import get_config
from schemas.request import SimulationRequest

SYSTEM_PROMPT = """You are the parsing layer of a materials-science simulation assistant.

Extract structured information from the user's natural-language request about a
computational materials simulation (DFT / Quantum ESPRESSO).

Rules:
- Return ONLY a single JSON object. No markdown fences, no commentary, no preamble.
- The JSON must match this shape exactly (all keys present):
  {
    "structure": {
      "host_material": string|null,
      "crystal_structure": string|null,
      "surface_miller_index": string|null,
      "supercell": string|null,
      "slab_layers": integer|null,
      "vacuum": number|null
    },
    "doping": {
      "dopant": string|null,
      "type": "substitutional"|"interstitial"|null,
      "location": string|null,
      "concentration_or_count": string|null
    } | null,
    "adsorption": {
      "adsorbate": string|null,
      "site": "top"|"bridge"|"hollow"|"other"|null,
      "orientation": string|null,
      "initial_height": number|null
    } | null,
    "calculation": {
      "type": "scf"|"relax"|"vc-relax"|null,
      "xc_functional": string|null,
      "kpoints": string|null,
      "cutoffs": string|null,
      "spin": string|null,
      "smearing": string|null,
      "convergence": string|null
    }
  }
- If the user did not mention doping at all, set "doping" to null (not an object of nulls).
- If the user did not mention adsorption at all, set "adsorption" to null.
- Do NOT guess a value the user did not state or clearly imply. Leave it null.
- "top", "bridge", "hollow" only ever describe an adsorption site, never a dopant location.
"""


def _extract_json(text: str) -> dict:
    """Groq models occasionally wrap JSON in markdown fences despite instructions."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    return json.loads(text)


def parse_user_request(raw_text: str) -> SimulationRequest:
    cfg = get_config()
    client = Groq(api_key=cfg.groq_api_key)

    completion = client.chat.completions.create(
        model=cfg.groq_model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
    )
    raw_output = completion.choices[0].message.content
    data = _extract_json(raw_output)
    data["raw_user_text"] = raw_text
    return SimulationRequest.model_validate(data)
