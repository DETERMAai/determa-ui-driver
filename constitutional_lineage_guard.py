from typing import Any, Dict, List

from spec_registry import get_spec


MAX_LINEAGE_DEPTH = 12


def _lineage_nodes(spec_id: str) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    seen = set()
    node = get_spec(spec_id)
    while node is not None:
        node_id = str(node.get("spec_id"))
        if node_id in seen:
            nodes.append(
                {
                    "spec_id": node_id,
                    "recursive": True,
                }
            )
            break
        seen.add(node_id)
        nodes.append(
            {
                "spec_id": node_id,
                "scope": node.get("scope"),
                "status": node.get("status"),
                "derived_from": node.get("derived_from"),
            }
        )
        parent_id = node.get("derived_from")
        node = get_spec(str(parent_id)) if parent_id else None
    return nodes


def validate_constitutional_lineage(spec_id: str) -> Dict[str, Any]:
    spec = get_spec(spec_id)
    if spec is None:
        return {
            "valid": False,
            "reason": "spec_not_found",
            "recursive_expansion": False,
            "lineage_depth": 0,
            "max_allowed_depth": MAX_LINEAGE_DEPTH,
            "lineage": [],
        }

    lineage = _lineage_nodes(str(spec_id))
    recursive_expansion = any(bool(node.get("recursive")) for node in lineage)
    lineage_depth = len([node for node in lineage if not node.get("recursive")])
    excessive_depth = lineage_depth > MAX_LINEAGE_DEPTH

    valid = not recursive_expansion and not excessive_depth
    reason = "lineage_valid"
    if recursive_expansion:
        reason = "recursive_spec_expansion_detected"
    elif excessive_depth:
        reason = "lineage_depth_exceeded"

    return {
        "valid": valid,
        "reason": reason,
        "recursive_expansion": recursive_expansion,
        "lineage_depth": lineage_depth,
        "max_allowed_depth": MAX_LINEAGE_DEPTH,
        "lineage": lineage,
    }
