from __future__ import annotations

import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class SummarySections(BaseModel):
    purpose: str = Field("", description="会議の目的")
    decisions: str = Field("", description="決定事項")
    action_items: str = Field("", description="宿題（アクションアイテム）")
    digest: str = Field("", description="議事要旨")


class SummaryRequest(BaseModel):
    title: str
    meeting_date: dt.date
    participants: List[str] = Field(default_factory=list)
    text: str
    input_mode: str = Field("free", description="free|bullet")

    @validator("input_mode")
    def validate_mode(cls, v: str) -> str:
        if v not in {"free", "bullet"}:
            raise ValueError("input_mode must be 'free' or 'bullet'")
        return v


class SummaryResponse(SummarySections):
    total_characters: int


class MinutesCreateRequest(SummarySections):
    title: str
    meeting_date: dt.date
    participants: List[str] = Field(default_factory=list)
    raw_input: str
    editor: Optional[str] = None


class MinutesResponse(SummarySections):
    id: int
    title: str
    meeting_date: dt.date
    participants: List[str]
    created_at: dt.datetime
    updated_at: dt.datetime
    raw_input: str


class MinutesListResponse(BaseModel):
    id: int
    title: str
    meeting_date: dt.date
    participants: List[str]
    created_at: dt.datetime


class MinutesVersionResponse(SummarySections):
    id: int
    created_at: dt.datetime
    editor: Optional[str]


class ReminderRequest(BaseModel):
    assignee: str
    action_item: str
    due_date: dt.date


class ReminderResponse(ReminderRequest):
    id: int
    status: str
    created_at: dt.datetime


class MinutesDetailResponse(MinutesResponse):
    versions: List[MinutesVersionResponse]
    reminders: List[ReminderResponse]


class MinutesSearchQuery(BaseModel):
    title: Optional[str] = None
    participant: Optional[str] = None
    start_date: Optional[dt.date] = None
    end_date: Optional[dt.date] = None


class DiffResponse(BaseModel):
    field: str
    previous: str
    current: str
    diff: str


class HistoryResponse(BaseModel):
    version: MinutesVersionResponse
    diffs: List[DiffResponse]
