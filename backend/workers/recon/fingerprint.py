"""
HTTP header tech fingerprinting — Wappalyzer-style, header-only approach.

Sends a GET request to the target and analyses response headers + HTML body
to identify the tech stack. Returns a list of finding dicts.
"""
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0

# (header_name, regex_pattern, technology_label)
_HEADER_SIGNATURES: list[tuple[str, str, str]] = [
    ("server", r"apache", "Apache HTTP Server"),
    ("server", r"nginx", "Nginx"),
    ("server", r"iis", "Microsoft IIS"),
    ("server", r"litespeed", "LiteSpeed"),
    ("server", r"cloudflare", "Cloudflare"),
    ("x-powered-by", r"php/?([\d.]+)?", "PHP"),
    ("x-powered-by", r"asp\.net", "ASP.NET"),
    ("x-powered-by", r"express", "Express.js"),
    ("x-aspnet-version", r".+", "ASP.NET"),
    ("x-aspnetmvc-version", r".+", "ASP.NET MVC"),
    ("x-generator", r"wordpress", "WordPress"),
    ("x-generator", r"drupal", "Drupal"),
    ("x-generator", r"joomla", "Joomla"),
    ("x-shopify-stage", r".+", "Shopify"),
    ("x-wp-super-cache", r".+", "WordPress + WP Super Cache"),
    ("x-drupal-cache", r".+", "Drupal"),
    ("x-varnish", r".+", "Varnish Cache"),
]

# Body patterns: (regex, tech_label)
_BODY_SIGNATURES: list[tuple[str, str]] = [
    (r"wp-content/", "WordPress"),
    (r"Drupal\.settings", "Drupal"),
    (r"Joomla!", "Joomla"),
    (r"Magento", "Magento"),
    (r"laravel_session", "Laravel"),
    (r"__VIEWSTATE", "ASP.NET WebForms"),
    (r"ng-version=", "Angular"),
    (r'id="__next"', "Next.js"),
    (r"__NUXT__", "Nuxt.js"),
]

# Headers that leak sensitive info
_SENSITIVE_HEADERS: list[str] = [
    "x-powered-by",
    "x-aspnet-version",
    "x-aspnetmvc-version",
    "server",
    "x-generator",
]


def _fetch(url: str) -> tuple[dict[str, str], str]:
    """Return (headers_lower, body_excerpt). Raises on network error."""
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True, verify=False) as client:
        resp = client.get(url)
        headers = {k.lower(): v for k, v in resp.headers.items()}
        body = resp.text[:8192]
        return headers, body


def fingerprint(domain: str) -> list[dict]:
    """
    Attempt HTTPS then HTTP, fingerprint headers + body, return findings.
    """
    headers: dict[str, str] = {}
    body: str = ""
    final_url = ""

    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            headers, body = _fetch(url)
            final_url = url
            break
        except httpx.RequestError as exc:
            logger.debug("fingerprint: %s unreachable via %s: %s", domain, scheme, exc)

    if not headers:
        return []

    findings: list[dict] = []
    seen_techs: set[str] = set()

    # Header-based detection
    for header_name, pattern, tech in _HEADER_SIGNATURES:
        value = headers.get(header_name, "")
        if value and re.search(pattern, value, re.IGNORECASE):
            if tech not in seen_techs:
                seen_techs.add(tech)
                findings.append(
                    {
                        "title": f"Tecnologia rilevata: {tech}",
                        "description": (
                            f"L'header HTTP '{header_name}: {value}' rivela l'utilizzo di {tech} "
                            f"su {domain}. Queste informazioni possono facilitare attacchi mirati."
                        ),
                        "severity": "INFO",
                        "affected_component": domain,
                        "proof": f"{header_name}: {value}",
                        "source": "fingerprint",
                        "nis2_control": "21.2.g",
                    }
                )

    # Body-based detection
    for pattern, tech in _BODY_SIGNATURES:
        if re.search(pattern, body, re.IGNORECASE) and tech not in seen_techs:
            seen_techs.add(tech)
            findings.append(
                {
                    "title": f"Tecnologia rilevata (HTML): {tech}",
                    "description": (
                        f"Il corpo della risposta HTTP di {domain} contiene pattern "
                        f"tipici di {tech}."
                    ),
                    "severity": "INFO",
                    "affected_component": domain,
                    "proof": f"Pattern trovato nel body: {pattern}",
                    "source": "fingerprint",
                    "nis2_control": "21.2.g",
                }
            )

    # Flag sensitive header disclosure as LOW severity
    for h in _SENSITIVE_HEADERS:
        if h in headers:
            findings.append(
                {
                    "title": f"Header informativo esposto: {h}",
                    "description": (
                        f"L'header '{h}: {headers[h]}' rivela dettagli tecnici del server. "
                        f"Rimuovere o oscurare gli header che espongono la versione software."
                    ),
                    "severity": "LOW",
                    "affected_component": domain,
                    "proof": f"{h}: {headers[h]}",
                    "fix_suggestion": (
                        f"Configurare il server per rimuovere o oscurare l'header '{h}'."
                    ),
                    "source": "fingerprint",
                    "nis2_control": "21.2.g",
                }
            )
            break  # one finding for info disclosure is enough

    return findings
