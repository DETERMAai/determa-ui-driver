from typing import Any, Dict, List


def _module_usage_hits(module_path: str, traces: List[Dict[str, Any]]) -> int:
    module_name = module_path.split("/")[-1].replace(".py", "").lower()
    hits = 0
    for trace in traces:
        trace_text = f"{trace.get('trace_type', '')} {trace.get('payload', {})}".lower()
        if module_name in trace_text:
            hits += 1
    return hits


def build_runtime_reduction_report(
    architecture_layout: Dict[str, List[str]],
    system_planes: Dict[str, List[str]],
    operational_traces: List[Dict[str, Any]],
    benchmark_runs: List[Dict[str, Any]],
    red_team_runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    module_candidates = []
    for plane, modules in architecture_layout.items():
        for module_path in modules:
            hits = _module_usage_hits(module_path, operational_traces)
            if hits == 0 and plane in {"extensions", "integrations", "operators"}:
                module_candidates.append(
                    {
                        "module": module_path,
                        "plane": plane,
                        "reason": "no_recent_operational_trace_hits",
                        "recommendation": "consider_lazy_loading_or_removal",
                    }
                )

    duplicate_flow_candidates = [
        {
            "paths": ["/approve/{job_id}", "/approvals/approve/{job_id}"],
            "recommendation": "merge_to_single_operator_entrypoint",
        },
        {
            "paths": ["/runtime/start", "/runtime/resume"],
            "recommendation": "merge_semantics_or_alias_with_single_handler",
        },
        {
            "paths": ["/runtime/stop", "/runtime/pause"],
            "recommendation": "merge_semantics_or_alias_with_single_handler",
        },
    ]

    low_value_paths = []
    if not benchmark_runs:
        low_value_paths.append(
            {
                "path": "/benchmarks/run/{benchmark_name}",
                "reason": "no_benchmark_runs_recorded",
                "recommendation": "defer_heavy_validation_until_needed",
            }
        )
    if not red_team_runs:
        low_value_paths.append(
            {
                "path": "/redteam/run/{scenario_name}",
                "reason": "no_red_team_runs_recorded",
                "recommendation": "schedule_periodic_red_team_jobs_instead_of_manual_path",
            }
        )

    simplification_recommendations = [
        "Keep canonical execution path in core/execution.py as the only execution orchestrator.",
        "Route approval semantics through a single public endpoint and keep the other as compatibility alias.",
        "Move optional observability/reporting endpoints behind feature flags in production.",
    ]

    return {
        "unused_module_candidates": module_candidates,
        "duplicated_flow_candidates": duplicate_flow_candidates,
        "low_value_orchestration_paths": low_value_paths,
        "simplification_recommendations": simplification_recommendations,
        "context": {
            "trace_count": len(operational_traces),
            "benchmark_runs": len(benchmark_runs),
            "red_team_runs": len(red_team_runs),
            "planes": {key: len(value) for key, value in system_planes.items()},
        },
    }
