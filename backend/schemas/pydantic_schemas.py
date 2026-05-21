import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator
import re

from backend.models.user import Plan
from backend.models.scan import ScanStatus, ScanScope


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


class ScanCreate(BaseModel):
    target: str
    scope: ScanScope = ScanScope.full
    scan_options: dict | None = None

    @field_validator("target")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower().removeprefix("http://").removeprefix("https://").split("/")[0]
        if not DOMAIN_RE.match(v):
            raise ValueError("Il target deve essere un dominio valido (es. example.com)")
        return v


class ScanOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    target: str
    status: ScanStatus
    scope: ScanScope
    scan_options: dict | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
