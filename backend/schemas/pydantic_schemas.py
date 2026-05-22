import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, field_validator
import re

from backend.models.user import Plan
from backend.models.scan import ScanStatus, ScanScope
from backend.models.target import VerificationMethod
from backend.models.finding import Severity
from backend.models.report import ReportStatus


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La password deve avere almeno 8 caratteri")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    plan: Plan
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Scans ────────────────────────────────────────────────────────────────────

DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)


# ── Targets ──────────────────────────────────────────────────────────────────

class TargetCreate(BaseModel):
    domain: str
    verification_method: VerificationMethod = VerificationMethod.dns_txt

    @field_validator("domain")
    @classmethod
    def validate_domain_field(cls, v: str) -> str:
        v = v.strip().lower().removeprefix("http://").removeprefix("https://").split("/")[0]
        if not DOMAIN_RE.match(v):
            raise ValueError("Il dominio non è valido (es. example.com)")
        return v


class TargetOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    domain: str
    verification_method: VerificationMethod
    verification_token: str
    verified: bool
    verified_at: datetime | None
    created_at: datetime


class TargetVerifyResponse(BaseModel):
    verified: bool
    detail: str


# ── Scans ────────────────────────────────────────────────────────────────────

class ScanCreate(BaseModel):
    target_id: uuid.UUID
    scope: ScanScope = ScanScope.full
    scan_options: dict | None = None


class ScanOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    target_id: uuid.UUID
    target: str
    status: ScanStatus
    scope: ScanScope
    scan_options: dict | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


# ── Findings ─────────────────────────────────────────────────────────────────

class FindingOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    scan_id: uuid.UUID
    title: str
    description: str
    severity: Severity
    cvss_score: float | None
    affected_component: str
    proof: str | None
    fix_suggestion: str | None
    nis2_control: str | None
    source: str
    created_at: datetime


# ── NIS2 ─────────────────────────────────────────────────────────────────────

class NIS2ControlOut(BaseModel):
    description: str
    status: str
    penalty: int
    finding_count: int
    critical_findings: list[str]


class NIS2ComplianceOut(BaseModel):
    score: int
    controls: dict[str, NIS2ControlOut]
    gaps: list[str]
    partial_controls: list[str]
    total_findings: int
    uncovered_findings: int


# ── Reports ──────────────────────────────────────────────────────────────────

class ReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    scan_id: uuid.UUID
    status: ReportStatus
    ai_summary: Any | None = None
    nis2_gap_analysis: str | None
    pdf_path: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    @field_validator("ai_summary", mode="before")
    @classmethod
    def parse_ai_summary(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
