"""
Nuclei wrapper — safe template scan (CVEs, misconfigs, exposures, technologies).

Runs nuclei as a subprocess and streams JSONL output.
Only non-intrusive template categories are used; no fuzzing or brute-force.
"""
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Safe template tags — never include: brute-force, fuzz, dos, intrusive
_SAFE_TAGS = "cve,misconfig,exposure,config,tech,default-login,takeover"
_TIMEOUT = 480  # seconds


def _build_cmd(target_url: str, out_path: Path) -> list[str]:
    return [
        "nuclei",
        "-u", target_url,
        "-tags", _SAFE_TAGS,
        "-json",
        "-o", str(out_path),
        "-silent",
        "-no-interactsh",       # disable OOB callbacks (safer, no external deps)
        "-rate-limit", "30",    # req/sec — polite to target
        "-timeout", "15",       # per-request timeout
        "-max-host-error", "30",
        "-no-color",
    ]


def scan(domain: str) -> list[dict]:
    """
    Run nuclei against https://<domain> (fallback http://) and return
    a list of raw Nuclei result dicts (JSONL parsed).
    """
    if not shutil.which("nuclei"):
        logger.warning("nuclei not found in PATH — skipping web scan")
        return []

    results: list[dict] = []

    for scheme in ("https", "http"):
        target_url = f"{scheme}://{domain}"
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
            out_path = Path(tmp.name)

        try:
            cmd = _build_cmd(target_url, out_path)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
            if proc.returncode not in (0, 1):  # 1 = found results
                logger.warning("nuclei exited %d: %s", proc.returncode, proc.stderr[:300])

            for line in out_path.read_text(errors="ignore").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    logger.debug("nuclei: skipping non-JSON line: %s", line[:80])

            if results:
                break  # HTTPS worked, no need to try HTTP

        except subprocess.TimeoutExpired:
            logger.warning("nuclei timed out after %ds for %s", _TIMEOUT, target_url)
        except Exception as exc:
            logger.exception("nuclei error for %s: %s", target_url, exc)
        finally:
            out_path.unlink(missing_ok=True)

    logger.info("nuclei found %d results for %s", len(results), domain)
    return results
