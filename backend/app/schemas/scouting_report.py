"""Pydantic schemas for scouting report API."""

from datetime import datetime

from pydantic import BaseModel


class ScoutingReportResponse(BaseModel):
    """Response schema for a scouting report."""

    id: int
    player_id: int
    report_type: str
    content: str
    model_scores_snapshot: dict | None = None
    llm_model_version: str | None = None
    generated_at: datetime
    stale: bool = False

    model_config = {"from_attributes": True}


class ScoutingReportRequest(BaseModel):
    """Request to generate a scouting report on demand."""

    report_type: str = "full"


class ScoutingReportListResponse(BaseModel):
    """Response with multiple scouting reports."""

    reports: list[ScoutingReportResponse]
    total: int
