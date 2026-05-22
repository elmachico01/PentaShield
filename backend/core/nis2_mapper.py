"""
NIS2 Article 21 compliance mapper.

Computes a per-control gap analysis and overall compliance score (0–100)
from a list of findings. Higher score = better compliance.
"""
from __future__ import annotations

from collections import defaultdict

from shared.constants import NIS2_CONTROLS

_SEVERITY_WEIGHT: dict[str, int] = {
    "CRITICAL": 10,
    "HIGH": 5,
    "MEDIUM": 2,
    "LOW": 1,
    "INFO": 0,
}

_MAX_PENALTY_PER_CONTROL = 10


def compute_compliance(findings: list[dict]) -> dict:
    """
    Return NIS2 compliance analysis:
      - score: 0-100 (100 = fully compliant, no findings)
      - controls: per-control status dict
      - gaps: list of control IDs that are non-compliant
      - total_findings: int
    """
    control_findings: dict[str, list[dict]] = defaultdict(list)
    uncovered: list[dict] = []

    for f in findings:
        ctrl = (f.get("nis2_control") or "").strip()
        if ctrl in NIS2_CONTROLS:
            control_findings[ctrl].append(f)
        else:
            uncovered.append(f)

    total_penalty = 0
    max_penalty = len(NIS2_CONTROLS) * _MAX_PENALTY_PER_CONTROL
    controls_out: dict[str, dict] = {}

    for ctrl_id, description in NIS2_CONTROLS.items():
        ctrl_f = control_findings.get(ctrl_id, [])
        penalty = min(
            sum(_SEVERITY_WEIGHT.get(f.get("severity", "INFO"), 0) for f in ctrl_f),
            _MAX_PENALTY_PER_CONTROL,
        )
        total_penalty += penalty

        if penalty == 0:
            status = "compliant"
        elif penalty < 5:
            status = "partial"
        else:
            status = "non_compliant"

        controls_out[ctrl_id] = {
            "description": description,
            "status": status,
            "penalty": penalty,
            "finding_count": len(ctrl_f),
            "critical_findings": [
                f["title"]
                for f in ctrl_f
                if f.get("severity") in ("CRITICAL", "HIGH")
            ][:5],
        }

    score = max(0, round(100 * (1 - total_penalty / max_penalty)))

    return {
        "score": score,
        "controls": controls_out,
        "gaps": [cid for cid, c in controls_out.items() if c["status"] == "non_compliant"],
        "partial_controls": [cid for cid, c in controls_out.items() if c["status"] == "partial"],
        "total_findings": len(findings),
        "uncovered_findings": len(uncovered),
    }
