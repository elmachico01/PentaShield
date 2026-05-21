"""
AI report engine — generates Italian-language security reports via Claude.

Uses tool use for structured JSON output and prompt caching on the system prompt.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic

from backend.config import get_settings

logger = logging.getLogger(__name__)

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}

# Tool schema — forces Claude to emit a structured report dict
_REPORT_TOOL: dict[str, Any] = {
    "name": "generate_security_report",
    "description": "Genera un report di sicurezza strutturato e completo in italiano",
    "input_schema": {
        "type": "object",
        "properties": {
            "executive_summary": {
                "type": "string",
                "description": "Sommario esecutivo per il management (200-400 parole), senza gergo tecnico",
            },
            "risk_level": {
                "type": "string",
                "enum": ["CRITICO", "ALTO", "MEDIO", "BASSO", "ACCETTABILE"],
                "description": "Livello di rischio complessivo dell'organizzazione",
            },
            "findings_by_severity": {
                "type": "object",
                "properties": {
                    "CRITICAL": {"type": "integer"},
                    "HIGH": {"type": "integer"},
                    "MEDIUM": {"type": "integer"},
                    "LOW": {"type": "integer"},
                    "INFO": {"type": "integer"},
                },
                "required": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
            },
            "top_priorities": {
                "type": "array",
                "description": "Top vulnerabilità ordinate per urgenza (max 10)",
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer"},
                        "title": {"type": "string"},
                        "severity": {"type": "string"},
                        "cvss_score": {"type": "number"},
                        "affected_component": {"type": "string"},
                        "fix_suggestion": {
                            "type": "string",
                            "description": "Azione correttiva specifica e attuabile",
                        },
                        "nis2_control": {"type": "string"},
                    },
                    "required": [
                        "rank", "title", "severity",
                        "affected_component", "fix_suggestion",
                    ],
                },
            },
            "nis2_gap_analysis": {
                "type": "string",
                "description": (
                    "Analisi dettagliata delle lacune rispetto agli obblighi "
                    "NIS2 Direttiva (UE) 2022/2555, Art. 21 in italiano"
                ),
            },
            "technical_details": {
                "type": "string",
                "description": "Sezione tecnica per il team IT con dettagli sulle vulnerabilità",
            },
            "remediation_roadmap": {
                "type": "array",
                "description": "Piano di rimedio strutturato per fasi temporali",
                "items": {
                    "type": "object",
                    "properties": {
                        "timeframe": {
                            "type": "string",
                            "enum": ["immediato", "30_giorni", "90_giorni"],
                        },
                        "action": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["CRITICA", "ALTA", "MEDIA"],
                        },
                    },
                    "required": ["timeframe", "action", "priority"],
                },
            },
        },
        "required": [
            "executive_summary",
            "risk_level",
            "findings_by_severity",
            "top_priorities",
            "nis2_gap_analysis",
            "technical_details",
            "remediation_roadmap",
        ],
    },
}

# System prompt is cached — keep it stable
_SYSTEM_PROMPT = (
    "Sei un esperto di sicurezza informatica certificato (CISSP, OSCP) "
    "specializzato in penetration testing per PMI italiane e conformità NIS2.\n\n"
    "Il tuo compito è analizzare i risultati di uno scan automatico e generare "
    "un report professionale completo in italiano.\n\n"
    "Linee guida:\n"
    "- Usa esclusivamente la lingua italiana\n"
    "- Prioritarizza per impatto aziendale reale: usa CVSS score quando disponibile, "
    "altrimenti la severity nominale\n"
    "- Mappa le vulnerabilità agli articoli NIS2 Art. 21 "
    "(21.2.e=sicurezza applicativa, 21.2.h=crittografia, "
    "21.2.i=controllo accessi, 21.2.a=gestione configurazioni, "
    "21.2.g=continuità operativa)\n"
    "- Il sommario esecutivo deve essere comprensibile dal management non tecnico: "
    "evita gergo tecnico, usa metafore concrete\n"
    "- Le raccomandazioni devono essere pratiche per PMI con risorse limitate\n"
    "- Per ogni vulnerabilità critica/alta fornisci una fix suggestion concisa e attuabile\n"
    "- La roadmap: immediato = entro 72h, 30_giorni, 90_giorni"
)


def generate_report(domain: str, findings: list[dict], scan_scope: str) -> dict:
    """
    Call Claude to generate a structured Italian security report.

    Findings are sorted by severity/CVSS and capped at top 50 to manage token usage.
    Returns the tool_input dict matching the _REPORT_TOOL schema.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY non configurata")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # Sort by severity (CRITICAL first), then CVSS descending, cap at 50
    top_findings = sorted(
        findings,
        key=lambda f: (
            _SEVERITY_ORDER.get(f.get("severity", "INFO"), 4),
            -(f.get("cvss_score") or 0.0),
        ),
    )[:50]

    findings_json = json.dumps(top_findings, ensure_ascii=False, indent=2)

    user_content = (
        f"Analizza i risultati dello scan di sicurezza per **{domain}** "
        f"(scope: {scan_scope}).\n\n"
        f"Totale vulnerabilità trovate: {len(findings)}\n"
        f"Vulnerabilità analizzate (top 50 per priorità): {len(top_findings)}\n\n"
        f"```json\n{findings_json}\n```\n\n"
        "Chiama ora lo strumento `generate_security_report` con il report completo."
    )

    logger.info(
        "Calling Claude for report on %s (%d findings, %d in prompt)",
        domain,
        len(findings),
        len(top_findings),
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[_REPORT_TOOL],
        tool_choice={"type": "tool", "name": "generate_security_report"},
        messages=[{"role": "user", "content": user_content}],
    )

    logger.info(
        "Claude response: stop_reason=%s usage=%s",
        response.stop_reason,
        response.usage,
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "generate_security_report":
            return block.input  # type: ignore[return-value]

    raise RuntimeError(
        f"Claude non ha chiamato generate_security_report (stop_reason={response.stop_reason})"
    )
