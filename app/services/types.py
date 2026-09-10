"""Shared result types for due diligence modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RedFlag:
    """A single red-flag finding with evidence references."""

    severity: str  # "info" | "warning" | "critical"
    code: str
    explanation: str
    evidence_refs: List[str] = field(default_factory=list)


@dataclass
class ModuleResult:
    """Unified result envelope for any check module."""

    module: str
    ok: bool
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    source: str = ""


@dataclass
class DueDiligenceReport:
    """Aggregated run for dashboard and PDF."""

    query_name: str
    country_code: str
    company_number: Optional[str]
    modules_requested: Dict[str, bool]
    modules: Dict[str, ModuleResult]
    red_flags: List[RedFlag]
    credit_proxy_score: Optional[float]
    credit_proxy_breakdown: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    timestamp_iso: str = ""
