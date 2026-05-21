"""
Shodan host lookup via REST API (httpx, no shodan SDK dependency).

Returns a list of finding dicts ready to be saved to the findings table.
Skips silently if SHODAN_API_KEY is not configured.
"""
import logging
import socket

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

_BASE = "https://api.shodan.io"
_TIMEOUT = 15.0


def _resolve_ip(hostname: str) -> str | None:
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def _get_host(ip: str, api_key: str) -> dict | None:
    try:
        resp = httpx.get(
            f"{_BASE}/shodan/host/{ip}",
            params={"key": api_key},
            timeout=_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return None
        logger.warning("Shodan returned %d for %s", resp.status_code, ip)
    except httpx.RequestError as exc:
        logger.warning("Shodan request error for %s: %s", ip, exc)
    return None


def lookup(domain: str) -> list[dict]:
    """
    Resolve *domain* to an IP, query Shodan REST API, return finding dicts.
    """
    api_key = get_settings().shodan_api_key
    if not api_key:
        logger.warning("SHODAN_API_KEY not configured — skipping Shodan lookup")
        return []

    ip = _resolve_ip(domain)
    if not ip:
        logger.warning("Could not resolve IP for %s", domain)
        return []

    host = _get_host(ip, api_key)
    if not host:
        return []

    findings: list[dict] = []

    # One INFO finding per open port/service
    for service in host.get("data", []):
        port = service.get("port", "?")
        transport = service.get("transport", "tcp")
        product = service.get("product", "")
        banner = (service.get("data") or "")[:300]
        component = f"{domain}:{port}/{transport}"

        title = f"Servizio esposto: porta {port}/{transport}"
        if product:
            title += f" ({product})"

        findings.append(
            {
                "title": title,
                "description": (
                    f"Shodan ha rilevato il servizio '{product or 'sconosciuto'}' "
                    f"sulla porta {port}/{transport} dell'host {ip} ({domain})."
                ),
                "severity": "INFO",
                "affected_component": component,
                "proof": banner,
                "source": "shodan",
                "nis2_control": "21.2.a",
            }
        )

    # Elevate severity for known CVEs reported by Shodan
    for vuln_id in host.get("vulns", []):
        findings.append(
            {
                "title": f"CVE rilevata da Shodan: {vuln_id}",
                "description": (
                    f"Shodan segnala la vulnerabilità {vuln_id} per l'host "
                    f"{ip} ({domain}). Verificare la versione del software e applicare le patch."
                ),
                "severity": "HIGH",
                "cvss_score": None,
                "affected_component": f"{domain} ({ip})",
                "proof": vuln_id,
                "fix_suggestion": (
                    f"Aggiornare il software affetto da {vuln_id} all'ultima versione stabile."
                ),
                "source": "shodan",
                "nis2_control": "21.2.e",
            }
        )

    return findings
