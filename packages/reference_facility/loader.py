"""Load and validate the synthetic reference facility FAC-001.

The JSON files under :mod:`packages.reference_facility.data` are the single
source of truth for the facility. This module reads them and validates them
into the canonical electrical model, returning a :class:`ReferenceFacility`.

All values are synthetic (``DataProvenance.SYNTHETIC``): every node and every
rated quantity is labelled with ``ProvenanceSource.SYNTHETIC`` so downstream
analytics can see, unambiguously, that nothing here is measured or nameplate
data from a real asset. FAC-001 is not based on any real facility.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.canonical_electrical_model import (
    AssetType,
    Criticality,
    ElectricalEdge,
    ElectricalNode,
    Facility,
    Provenance,
    ProvenanceSource,
    RatedData,
    SourceNode,
)

from .models import MeteringPlan, ReferenceFacility

_DATA_DIR = Path(__file__).parent / "data"
_FACILITY_ID = "FAC-001"
_REFERENCE = "FAC-001 synthetic reference facility"


def _read_json(name: str) -> Any:
    with (_DATA_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def _strip_annotations(raw: dict[str, Any]) -> dict[str, Any]:
    """Drop documentation-only keys (those beginning with an underscore)."""
    return {key: value for key, value in raw.items() if not key.startswith("_")}


def _synthetic_provenance() -> dict[str, Any]:
    return {"source": ProvenanceSource.SYNTHETIC.value, "reference": _REFERENCE}


def _build_rated(raw: dict[str, Any]) -> RatedData:
    """Wrap each raw scalar rating into a synthetic-provenance ``Provenanced``."""
    wrapped = {
        field: {"value": value, "provenance": _synthetic_provenance()}
        for field, value in raw.items()
    }
    return RatedData.model_validate(wrapped)


def _build_node(raw: dict[str, Any]) -> ElectricalNode:
    # ``subtype`` is descriptive documentation only and is intentionally not
    # forwarded to the canonical node (which forbids unknown fields).
    return ElectricalNode(
        id=raw["id"],
        name=raw["name"],
        asset_type=AssetType(raw["asset_type"]),
        nominal_voltage_v=raw.get("nominal_voltage_v"),
        phases=raw["phases"],
        parent_facility_id=_FACILITY_ID,
        criticality=Criticality(raw["criticality"]),
        rated=_build_rated(raw["rated"]),
        provenance=Provenance(source=ProvenanceSource.SYNTHETIC, reference=_REFERENCE),
    )


def load_reference_facility() -> ReferenceFacility:
    """Load, validate, and return the synthetic reference facility FAC-001.

    The returned :class:`ReferenceFacility` holds only validated canonical
    objects and has passed referential-integrity checks (unique node ids, all
    edge/source/meter cross-references resolve, and the intentional metering gap
    remains unmetered).
    """
    facility = Facility.model_validate(_strip_annotations(_read_json("facility.json")))
    nodes = [_build_node(node) for node in _read_json("nodes.json")["nodes"]]
    edges = [ElectricalEdge.model_validate(edge) for edge in _read_json("edges.json")["edges"]]
    sources = [
        SourceNode.model_validate(source) for source in _read_json("sources.json")["sources"]
    ]
    metering = MeteringPlan.model_validate(_strip_annotations(_read_json("metering.json")))

    return ReferenceFacility(
        facility=facility,
        nodes=nodes,
        edges=edges,
        sources=sources,
        metering=metering,
    )
