from enum import Enum


class Severity(str, Enum):
    info = "INFO"
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    critical = "CRITICAL"


# NIS2 Article 21 controls mapping
NIS2_CONTROLS: dict[str, str] = {
    "21.2.a": "Politiche di sicurezza dei sistemi informatici e delle reti",
    "21.2.b": "Gestione degli incidenti",
    "21.2.c": "Continuità operativa e gestione delle crisi",
    "21.2.d": "Sicurezza della catena di approvvigionamento",
    "21.2.e": "Sicurezza nell'acquisizione, sviluppo e manutenzione dei sistemi",
    "21.2.f": "Politiche e procedure per valutare l'efficacia delle misure di gestione del rischio",
    "21.2.g": "Pratiche di igiene informatica di base e formazione in materia di sicurezza",
    "21.2.h": "Politiche e procedure relative all'uso della crittografia",
    "21.2.i": "Sicurezza delle risorse umane, politiche di controllo degli accessi e gestione degli asset",
    "21.2.j": "Uso di soluzioni di autenticazione a più fattori",
}

# Mapping: finding category → NIS2 control IDs
FINDING_CATEGORY_TO_NIS2: dict[str, list[str]] = {
    "authentication": ["21.2.i", "21.2.j"],
    "access_control": ["21.2.i"],
    "cryptography": ["21.2.h"],
    "configuration": ["21.2.a", "21.2.g"],
    "vulnerability": ["21.2.e", "21.2.f"],
    "network_exposure": ["21.2.a"],
    "supply_chain": ["21.2.d"],
    "incident_response": ["21.2.b"],
    "data_exposure": ["21.2.h", "21.2.i"],
}
