"""
Nmap wrapper — TCP connect scan with service version detection.

Uses -sT (no root required) by default.
Parses XML output into a list of PortResult dicts.
"""
import logging
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_TIMEOUT = 300  # seconds


@dataclass
class PortResult:
    host: str
    ip: str
    port: int
    protocol: str
    state: str
    service: str
    product: str
    version: str
    extra_info: str
    cpe: list[str] = field(default_factory=list)

    @property
    def component(self) -> str:
        return f"{self.host}:{self.port}/{self.protocol}"

    @property
    def version_string(self) -> str:
        parts = [p for p in (self.product, self.version, self.extra_info) if p]
        return " ".join(parts)


def _parse_xml(xml_path: Path, original_host: str) -> list[PortResult]:
    results: list[PortResult] = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        logger.error("Failed to parse nmap XML: %s", exc)
        return results

    for host_el in root.findall("host"):
        # IP address
        ip = ""
        for addr in host_el.findall("address"):
            if addr.get("addrtype") == "ipv4":
                ip = addr.get("addr", "")
                break

        # Hostname (prefer user-supplied)
        hostname = original_host
        hostnames_el = host_el.find("hostnames")
        if hostnames_el is not None:
            hn = hostnames_el.find("hostname")
            if hn is not None and hn.get("name"):
                hostname = hn.get("name", original_host)

        ports_el = host_el.find("ports")
        if ports_el is None:
            continue

        for port_el in ports_el.findall("port"):
            state_el = port_el.find("state")
            if state_el is None or state_el.get("state") != "open":
                continue

            service_el = port_el.find("service")
            cpe_list = [
                cpe.text or ""
                for cpe in (port_el.findall("service/cpe") if service_el is not None else [])
            ]

            results.append(
                PortResult(
                    host=hostname,
                    ip=ip,
                    port=int(port_el.get("portid", 0)),
                    protocol=port_el.get("protocol", "tcp"),
                    state="open",
                    service=(service_el.get("name", "") if service_el is not None else ""),
                    product=(service_el.get("product", "") if service_el is not None else ""),
                    version=(service_el.get("version", "") if service_el is not None else ""),
                    extra_info=(service_el.get("extrainfo", "") if service_el is not None else ""),
                    cpe=cpe_list,
                )
            )
    return results


def scan(target: str, top_ports: int = 1000) -> list[PortResult]:
    """
    Run nmap against *target* and return open port results.
    Falls back to empty list if nmap is not installed (dev env).
    """
    if not shutil.which("nmap"):
        logger.warning("nmap not found in PATH — skipping network scan")
        return []

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp:
        out_path = Path(tmp.name)

    cmd = [
        "nmap",
        "-sT",                        # TCP connect (no root needed)
        "-sV",                         # service + version detection
        "--version-intensity", "5",    # balance speed/accuracy
        "-T4",                         # aggressive timing
        f"--top-ports", str(top_ports),
        "-oX", str(out_path),
        "--open",                      # only show open ports
        target,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("nmap exited %d: %s", result.returncode, result.stderr[:300])
    except subprocess.TimeoutExpired:
        logger.warning("nmap timed out after %ds for %s", _TIMEOUT, target)
        return []
    except Exception as exc:
        logger.exception("nmap error for %s: %s", target, exc)
        return []
    finally:
        pass  # parse even if non-zero exit (partial results)

    results = _parse_xml(out_path, target)
    out_path.unlink(missing_ok=True)
    logger.info("nmap found %d open ports on %s", len(results), target)
    return results
