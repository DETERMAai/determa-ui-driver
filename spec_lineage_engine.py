import hashlib
import json
from typing import Any, Dict, List, Optional

from spec_registry import get_spec


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_spec_lineage(spec_id: str) -> Dict[str, Any]:
    current = get_spec(spec_id)
    if current is None:
        return {"status": "not_found", "spec_id": spec_id}

    ancestry: List[Dict[str, Any]] = []
    seen = set()
    node = current
    while node is not None:
        node_id = str(node.get("spec_id"))
        if node_id in seen:
            break
        seen.add(node_id)
        ancestry.append(
            {
                "spec_id": node_id,
                "scope": node.get("scope"),
                "status": node.get("status"),
                "derived_from": node.get("derived_from"),
                "superseded_by": node.get("superseded_by"),
                "governance_approvals": list(node.get("governance_approvals", [])),
            }
        )
        parent_id = node.get("derived_from")
        node = get_spec(str(parent_id)) if parent_id else None

    lineage_hash = _stable_hash(ancestry)
    return {
        "status": "ok",
        "spec_id": str(spec_id),
        "lineage": ancestry,
        "lineage_hash": lineage_hash,
        "derived_from": current.get("derived_from"),
        "superseded_by": current.get("superseded_by"),
        "semantic_ancestry_depth": len(ancestry),
        "governance_approvals": list(current.get("governance_approvals", [])),
    }
