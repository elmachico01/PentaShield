"""
Finding normalizer — maps raw Nuclei / ZAP output to the Finding schema dict.

Both normalizers return dicts compatible with models.Finding fields.
"""
from __future__ import annotations

import re

# ── Severity maps ─────────────────────────────────────────────────────────────

_NUCLEI_SEV = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
    "info": "INFO",
    "unknown": "INFO",
}

_ZAP_RISK = {
    "High": "HIGH",
    "Medium": "MEDIUM",
    "Low": "LOW",
    "Informational": "INFO",
}

# ── CWE → NIS2 Article 21 mapping ────────────────────────────────────────────

_CWE_NIS2: dict[int, str] = {
    79: "21.2.e",    # XSS
    89: "21.2.e",    # SQL injection
    352: "21.2.e",   # CSRF
    22: "21.2.e",    # Path traversal
    78: "21.2.e",    # OS command injection
    287: "21.2.i",   # Improper authentication
    306: "21.2.i",   # Missing auth
    798: "21.2.i",   # Hard-coded credentials
    311: "21.2.h",   # Missing encryption
    319: "21.2.h",   # Cleartext transmission
    200: "21.2.h",   # Information exposure
    16: "21.2.a",    # Configuration
    693: "21.2.a",   # Protection mechanism failure
}

_DEFAULT_NIS2 = "21.2.e"

# ── Nuclei tag → NIS2 ────────────────────────────────────────────────────────

_TAG_NIS2: dict[str, str] = {
    "auth": "21.2.i",
    "authentication": "21.2.i",
    "default-login": "21.2.i",
    "misconfig": "21.2.a",
    "config": "21.2.a",
    "exposure": "21.2.h",
    "cve": "21.2.e",
    "takeover": "21.2.a",
    "tech": "21.2.g",
}


def _nis2_from_cwe(cwe_str: str | int) -> str:
    try:
        cwe_id = int(re.sub(r"\D", "", str(cwe_str)))
        return _CWE_NIS2.get(cwe_id, _DEFAULT_NIS2)
    except (ValueError, TypeError):
        return _DEFAULT_NIS2


def _nis2_from_tags(tags: list[str]) -> str:
    for tag in tags:
        if tag.lower() in _TAG_NIS2:
            return _TAG_NIS2[tag.lower()]
    return _DEFAULT_NIS2


# ── Nuclei normalizer ─────────────────────────────────────────────────────────

def normalize_nuclei(raw: dict, domain: str) -> dict:
    """
    Convert a single Nuclei JSONL result dict into a Finding-compatible dict.
    """
    info = raw.get("info", {})
    name = info.get("name", raw.get("template-id", "Unknown"))
    severity_raw = info.get("severity", "info").lower()
    severity = _NUCLEI_SEV.get(severity_raw, "INFO")

    matched_at = raw.get("matched-at") or raw.get("host") or domain
    template_id = raw.get("template-id", "")

    # CVSS score
    classification = info.get("classification", {})
    cvss = classification.get("cvss-score")

    # CVE IDs
    cve_ids: list[str] = classification.get("cve-id") or []
    cve_str = ", ".join(cve_ids) if cve_ids else ""

    # NIS2 from tags
    tags: list[str] = info.get("tags", [])
    nis2 = _nis2_from_tags(tags)

    # Description
    description_parts = [info.get("description", "").strip()]
    if cve_str:
        description_parts.append(f"CVE: {cve_str}")
    if raw.get("extracted-results"):
        description_parts.append(f"Estratto: {'; '.join(raw['extracted-results'][:3])}")
    description = "\n".join(p for p in description_parts if p)

    # Proof (request/response excerpt)
    proof_parts = []
    if raw.get("curl-command"):
        proof_parts.append(f"Request: {raw['curl-command'][:500]}")
    proof = "\n".join(proof_parts) if proof_parts else f"template: {template_id}"

    # Fix suggestion
    fix = info.get("remediation", "").strip()
    if not fix:
        references = info.get("reference", [])
        if references:
            fix = "Riferimenti: " + ", ".join(references[:2])

    return {
        "title": f"[Nuclei] {name}" + (f" ({cve_str})" if cve_str else ""),
        "description": description or name,
        "severity": severity,
        "cvss_score": float(cvss) if cvss else None,
        "affected_component": matched_at,
        "proof": proof,
        "fix_suggestion": fix or None,
        "nis2_control": nis2,
        "source": "nuclei",
    }


# ── ZAP normalizer ────────────────────────────────────────────────────────────

def normalize_zap(alert: dict) -> dict:
    """
    Convert a ZAP alert dict into a Finding-compatible dict.
    """
    risk = alert.get("risk", "Low")
    severity = _ZAP_RISK.get(risk, "LOW")
    name = alert.get("name", "Unknown")
    url = alert.get("url", "")
    cwe_id = alert.get("cweid", "")
    nis2 = _nis2_from_cwe(cwe_id) if cwe_id and cwe_id != "0" else _DEFAULT_NIS2

    # Build proof from evidence + request/response snippet
    evidence = alert.get("evidence", "")
    proof = f"URL: {url}"
    if evidence:
        proof += f"\nEvidenza: {evidence[:300]}"

    description = alert.get("description", name).strip()
    solution = alert.get("solution", "").strip()
    reference = alert.get("reference", "").strip()

    fix = solution
    if reference and len(fix) < 50:
        fix += f"\nRiferimento: {reference[:200]}"

    confidence = alert.get("confidence", "")
    if confidence:
        description += f"\n\nConfidenza: {confidence}"

    return {
        "title": f"[ZAP] {name}",
        "description": description,
        "severity": severity,
        "cvss_score": None,
        "affected_component": url or "sconosciuto",
        "proof": proof,
        "fix_suggestion": fix or None,
        "nis2_control": nis2,
        "source": "zap",
    }
