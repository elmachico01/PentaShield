"""
Subfinder wrapper — enumerates subdomains via subprocess.

If subfinder is not installed the function returns an empty list and logs a
warning rather than crashing (graceful degradation for dev environments).
"""
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_TIMEOUT = 120  # seconds


def enumerate_subdomains(domain: str) -> list[str]:
    """
    Run subfinder against *domain* and return the list of discovered subdomains.
    Always includes the root domain itself.
    """
    subdomains: set[str] = {domain}

    if not shutil.which("subfinder"):
        logger.warning("subfinder not found in PATH — skipping subdomain enumeration")
        return list(subdomains)

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        out_path = Path(tmp.name)

    try:
        result = subprocess.run(
            ["subfinder", "-d", domain, "-silent", "-o", str(out_path)],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("subfinder exited %d: %s", result.returncode, result.stderr[:200])
        for line in out_path.read_text(errors="ignore").splitlines():
            sub = line.strip().lower()
            if sub:
                subdomains.add(sub)
    except subprocess.TimeoutExpired:
        logger.warning("subfinder timed out after %ds for %s", _TIMEOUT, domain)
    except Exception as exc:
        logger.exception("subfinder error for %s: %s", domain, exc)
    finally:
        out_path.unlink(missing_ok=True)

    return sorted(subdomains)
