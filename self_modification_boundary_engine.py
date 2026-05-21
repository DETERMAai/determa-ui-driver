from typing import Any, Dict, List, Set


def _as_set(content: Dict[str, Any], key: str) -> Set[str]:
    value = content.get(key, [])
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def evaluate_self_modification_boundary(mutation_context: Dict[str, Any]) -> Dict[str, Any]:
    context = dict(mutation_context or {})

    autonomous = bool(context.get("autonomous", False))
    operation = str(context.get("operation") or "unknown").strip().lower()
    targets_constitutional_core = bool(context.get("targets_constitutional_core", False))
    widens_autonomy_boundary = bool(context.get("widens_autonomy_boundary", False))

    allowed_recommendations = {"recommend_reduction", "recommend_simplification"}

    if autonomous and operation in allowed_recommendations:
        return {
            "allowed": True,
            "reason": "autonomous_recommendation_allowed",
            "boundary": "recommendation_only",
        }

    if autonomous and (targets_constitutional_core or widens_autonomy_boundary):
        return {
            "allowed": False,
            "reason": "autonomous_constitutional_mutation_blocked",
            "boundary": "immutable_foundation",
        }

    if autonomous and operation in {"canonicalize_spec", "mutate_governance", "expand_autonomy"}:
        return {
            "allowed": False,
            "reason": "autonomous_governance_mutation_blocked",
            "boundary": "self_modification_limit",
        }

    return {
        "allowed": True,
        "reason": "manual_or_non_mutating_context",
        "boundary": "bounded_self_modification",
    }
