"""
NVD (National Vulnerability Database) API v2 client.

Queries CVEs by product + version keyword search.
Fetches CVSS v3.1 base scores (falls back to v2).
Respects NVD rate limits: 5 req/30s without key, 50 req/30s with key.
"""
import logging
import time

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_TIMEOUT = 20.0
_MAX_RESULTS_PER_QUERY = 5        # cap CVEs per service to avoid noise
_RATE_LIMIT_DELAY = 0.7           # seconds between requests (safe for keyed access)


def _get_headers() -> dict[str, str]:
    api_key = get_settings().nvd_api_key
    if api_key:
        return {"apiKey": api_key}
    return {}


def _extract_cvss(cve: dict) -> float | None:
    metrics = cve.get("metrics", {})
    # Try CVSSv3.1 first, then v3.0, then v2
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key, [])
        if entries:
            return entries[0].get("cvssData", {}).get("baseScore")
    return None


def _severity_from_cvss(score: float | None) -> str:
    if score is None:
        return "MEDIUM"
    if score >= 9.0:
        return "CRITICAL"
    if score >= 7.0:
        return "HIGH"
    if score >= 4.0:
        return "MEDIUM"
    if score > 0:
        return "LOW"
    return "INFO"


def lookup_cves(product: str, version: str) -> list[dict]:
    """
    Search NVD for CVEs matching *product* + *version*.
    Returns a list of finding dicts.
    """
    if not product:
        return []

    keyword = f"{product} {version}".strip()
    params: dict = {
        "keywordSearch": keyword,
        "resultsPerPage": _MAX_RESULTS_PER_QUERY,
        "noRejected": "",
    }

    try:
        time.sleep(_RATE_LIMIT_DELAY)
        resp = httpx.get(
            _BASE,
            params=params,
            headers=_get_headers(),
            timeout=_TIMEOUT,
        )
        if resp.status_code == 429:
            logger.warning("NVD rate limit hit — sleeping 35s")
            time.sleep(35)
            resp = httpx.get(_BASE, params=params, headers=_get_headers(), timeout=_TIMEOUT)
        if resp.status_code != 200:
            logger.warning("NVD returned %d for '%s'", resp.status_code, keyword)
            return []
        data = resp.json()
    except httpx.RequestError as exc:
        logger.warning("NVD request error for '%s': %s", keyword, exc)
        return []

    findings: list[dict] = []
    for vuln in data.get("vulnerabilities", []):
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "")
        cvss = _extract_cvss(cve)
        severity = _severity_from_cvss(cvss)

        # English description
        description = next(
            (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
            "Nessuna descrizione disponibile.",
        )

        # Published date
        published = cve.get("published", "")[:10]

        findings.append(
            {
                "title": f"{cve_id} — {product} {version}".strip(),
                "description": (
                    f"[NVD] {description}\n\n"
                    f"CVE: {cve_id} | Pubblicata: {published} | CVSS: {cvss or 'N/A'}"
                ),
                "severity": severity,
                "cvss_score": cvss,
                "proof": cve_id,
                "fix_suggestion": (
                    f"Aggiornare {product} alla versione più recente. "
                    f"Consultare https://nvd.nist.gov/vuln/detail/{cve_id} per i dettagli."
                ),
                "source": "nvd",
                "nis2_control": "21.2.e",
            }
        )

    return findings
