"""
Basic unit tests for the deterministic completeness validator.
Run with: pytest tests/
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas.request import SimulationRequest
from schemas.structure import StructureRequest, AdsorptionRequest
from validators.completeness import check_completeness


def test_missing_host_material():
    req = SimulationRequest(raw_user_text="test")
    missing = check_completeness(req)
    assert "structure.host_material" in missing


def test_surface_requires_miller_and_vacuum():
    req = SimulationRequest(
        raw_user_text="test",
        structure=StructureRequest(host_material="Fe", surface_miller_index="110"),
    )
    missing = check_completeness(req)
    assert "structure.supercell" in missing
    assert "structure.slab_layers" in missing
    assert "structure.vacuum" in missing


def test_adsorption_requires_site():
    req = SimulationRequest(
        raw_user_text="test",
        structure=StructureRequest(host_material="Fe"),
        adsorption=AdsorptionRequest(adsorbate="CO2"),
    )
    missing = check_completeness(req)
    assert "adsorption.site" in missing


def test_complete_bulk_request_has_no_missing_structure_fields():
    req = SimulationRequest(
        raw_user_text="test",
        structure=StructureRequest(host_material="Fe"),
    )
    req.calculation.type = "scf"
    req.calculation.xc_functional = "PBE"
    missing = check_completeness(req)
    assert missing == []
