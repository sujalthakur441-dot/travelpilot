"""
Pydantic models for TravelPilot.

These define the shape of the Live Itinerary State that every agent
reads from and writes to (see the data model in the spec doc).
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


CrowdLevel = Literal["Low", "Medium", "High"]
DisruptionType = Literal["crowd_spike", "cancelled", "closed", "weather"]


class TripRequest(BaseModel):
    destination: str = Field(..., examples=["Goa"])
    days: int = Field(..., ge=1, le=14)
    budget_total: float = Field(..., gt=0)
    interests: list[str] = Field(default_factory=list, examples=[["beach", "temple", "market"]])
    crowd_tolerance: Literal["low", "medium", "high"] = "medium"


class Alternative(BaseModel):
    poi_id: str
    name: str
    reason: str
    crowd_level: CrowdLevel
    cost: float


class ActivitySlot(BaseModel):
    slot_id: str
    time: str
    poi_id: str
    name: str
    category: str
    crowd_level: CrowdLevel
    cost: float
    status: Literal["confirmed", "swapped"] = "confirmed"
    alternatives: list[Alternative] = Field(default_factory=list)
    swap_reason: Optional[str] = None


class DayPlan(BaseModel):
    date_label: str
    slots: list[ActivitySlot]


class Budget(BaseModel):
    total: float
    spent: float = 0.0


class BackupLogEntry(BaseModel):
    slot_id: str
    original: str
    swapped_to: str
    reason: str
    timestamp: str


class TripState(BaseModel):
    trip_id: str
    destination: str
    crowd_tolerance: str
    budget: Budget
    days: list[DayPlan]
    backup_log: list[BackupLogEntry] = Field(default_factory=list)
    agent_log: list[str] = Field(default_factory=list)


class DisruptionRequest(BaseModel):
    slot_id: str
    disruption_type: DisruptionType


class AskRequest(BaseModel):
    question: str
