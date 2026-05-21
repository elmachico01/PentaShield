"""
OWASP ZAP API client — passive + optional active scan.

ZAP runs as a Docker service (see infra/docker-compose.yml).
Degrades gracefully if ZAP is unreachable.

Passive scan: spider → wait for passive analysis → collect alerts.
Active scan:  run OWASP ZAP active scanner with rate limiting (scope=full only).
"""
import logging
import time

import httpx

from backend.config import get_settings

logger = logging.getLogger(__name__)

_CONNECT_TIMEOUT = 5.0
_REQUEST_TIMEOUT = 30.0
_POLL_INTERVAL = 3       # seconds between status polls
_SPIDER_WAIT = 120       # max seconds to wait for spider
_PASSIVE_WAIT = 90       # max seconds to wait for passive scan queue
_ACTIVE_WAIT = 300       # max seconds to wait for active scan


def _zap_url(path: str) -> str:
    base = get_settings().zap_api_url.rstrip("/")
    return f"{base}{path}"


def _params(extra: dict | None = None) -> dict:
    api_key = get_settings().zap_api_key
    p = {"apikey": api_key} if api_key else {}
    if extra:
        p.update(extra)
    return p


def _get(path: str, params: dict | None = None) -> dict | None:
    try:
        resp = httpx.get(
            _zap_url(path),
            params=_params(params),
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        logger.debug("ZAP GET %s failed: %s", path, exc)
        return None


def _is_available() -> bool:
    try:
        resp = httpx.get(_zap_url("/JSON/core/view/version/"), timeout=_CONNECT_TIMEOUT)
        return resp.status_code == 200
    except httpx.RequestError:
        return False


def _wait_for(poll_fn, done_fn, max_wait: int, label: str) -> bool:
    """Poll until done_fn returns True or timeout."""
    elapsed = 0
    while elapsed < max_wait:
        result = poll_fn()
        if result is not None and done_fn(result):
            return True
        time.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
    logger.warning("ZAP %s timed out after %ds", label, max_wait)
    return False


def _new_session() -> bool:
    data = _get("/JSON/core/action/newSession/", {"overwrite": "true"})
    return data is not None


def _spider(target_url: str) -> bool:
    """Start ZAP spider and wait for completion."""
    start = _get("/JSON/spider/action/scan/", {"url": target_url, "recurse": "true"})
    if not start:
        return False
    scan_id = start.get("scan", "0")

    return _wait_for(
        poll_fn=lambda: _get("/JSON/spider/view/status/", {"scanId": scan_id}),
        done_fn=lambda r: int(r.get("status", 0)) >= 100,
        max_wait=_SPIDER_WAIT,
        label="spider",
    )


def _wait_passive() -> None:
    """Wait until passive scan queue is empty."""
    _wait_for(
        poll_fn=lambda: _get("/JSON/pscan/view/recordsToScan/"),
        done_fn=lambda r: int(r.get("recordsToScan", 1)) == 0,
        max_wait=_PASSIVE_WAIT,
        label="passive scan",
    )


def _active_scan(target_url: str) -> None:
    """Start ZAP active scanner with a scan policy and wait."""
    start = _get(
        "/JSON/ascan/action/scan/",
        {
            "url": target_url,
            "recurse": "true",
            "scanPolicyName": "",
            "method": "",
            "postData": "",
        },
    )
    if not start:
        return
    scan_id = start.get("scan", "0")
    _wait_for(
        poll_fn=lambda: _get("/JSON/ascan/view/status/", {"scanId": scan_id}),
        done_fn=lambda r: int(r.get("status", 0)) >= 100,
        max_wait=_ACTIVE_WAIT,
        label="active scan",
    )


def _get_alerts(base_url: str) -> list[dict]:
    data = _get("/JSON/alert/view/alerts/", {"baseurl": base_url, "count": "500"})
    if not data:
        return []
    return data.get("alerts", [])


def scan(domain: str, active: bool = False) -> list[dict]:
    """
    Run ZAP passive (and optionally active) scan against *domain*.
    Returns raw ZAP alert dicts.
    """
    if not _is_available():
        logger.warning("ZAP not reachable at %s — skipping", get_settings().zap_api_url)
        return []

    target_url = f"https://{domain}"
    logger.info("ZAP: starting scan of %s (active=%s)", domain, active)

    _new_session()
    _spider(target_url)
    _wait_passive()

    if active:
        logger.info("ZAP: running active scan on %s", domain)
        _active_scan(target_url)

    alerts = _get_alerts(target_url)
    logger.info("ZAP: found %d alerts for %s", len(alerts), domain)
    return alerts
