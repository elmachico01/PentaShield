"""
Finding deduplication logic.

Prevents inserting duplicate findings for the same scan.
Dedup key: (scan_id, affected_component, title_prefix)
CVE findings use the CVE ID as the dedup key.
"""
import re
import uuid
from sqlalchemy.orm import Session

from backend.models.finding import Finding

_CVE_RE = re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE)


def _dedup_key(finding: dict) -> str:
    """Derive a stable dedup key from a finding dict."""
    title = finding.get("title", "")
    component = finding.get("affected_component", "")
    cve_match = _CVE_RE.search(title)
    if cve_match:
        return f"cve:{cve_match.group().upper()}:{component}"
    # For non-CVE findings use title + component (lowercased, truncated)
    return f"{title[:80].lower()}:{component.lower()}"


def deduplicate(
    db: Session,
    scan_id: uuid.UUID,
    new_findings: list[dict],
) -> list[dict]:
    """
    Return only findings not already present in the DB for this scan.
    Also deduplicates within the new_findings list itself.
    """
    # Load existing finding keys from DB
    existing = db.query(Finding).filter(Finding.scan_id == scan_id).all()
    existing_keys: set[str] = set()
    for f in existing:
        existing_keys.add(
            _dedup_key(
                {
                    "title": f.title,
                    "affected_component": f.affected_component,
                }
            )
        )

    seen: set[str] = set()
    unique: list[dict] = []
    for f in new_findings:
        key = _dedup_key(f)
        if key not in existing_keys and key not in seen:
            seen.add(key)
            unique.append(f)

    duplicates = len(new_findings) - len(unique)
    if duplicates:
        import logging
        logging.getLogger(__name__).info(
            "Deduplicator dropped %d duplicate findings for scan %s",
            duplicates,
            str(scan_id)[:8],
        )
    return unique
