from __future__ import annotations

import datetime as dt
from typing import Iterable, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .. import models
from ..schemas import (
    DiffResponse,
    HistoryResponse,
    MinutesCreateRequest,
    MinutesDetailResponse,
    MinutesListResponse,
    MinutesResponse,
    MinutesSearchQuery,
    MinutesVersionResponse,
    ReminderRequest,
    ReminderResponse,
)
from .summary import MAX_CHARACTERS


def create_minutes(session: Session, payload: MinutesCreateRequest) -> MinutesResponse:
    minutes = models.Minutes(
        title=payload.title,
        meeting_date=payload.meeting_date,
        participants=",".join(payload.participants),
        purpose=payload.purpose,
        decisions=payload.decisions,
        action_items=payload.action_items,
        digest=payload.digest,
        raw_input=payload.raw_input,
    )
    session.add(minutes)
    session.flush()
    version = models.MinutesVersion(
        minutes_id=minutes.id,
        purpose=minutes.purpose,
        decisions=minutes.decisions,
        action_items=minutes.action_items,
        digest=minutes.digest,
        editor=payload.editor,
    )
    session.add(version)
    session.flush()
    return map_minutes(minutes)


def update_minutes(session: Session, minutes_id: int, payload: MinutesCreateRequest) -> MinutesResponse:
    minutes = session.get(models.Minutes, minutes_id)
    if not minutes:
        raise ValueError("Minutes not found")

    minutes.title = payload.title
    minutes.meeting_date = payload.meeting_date
    minutes.participants = ",".join(payload.participants)
    minutes.purpose = payload.purpose
    minutes.decisions = payload.decisions
    minutes.action_items = payload.action_items
    minutes.digest = payload.digest
    minutes.raw_input = payload.raw_input

    version = models.MinutesVersion(
        minutes_id=minutes.id,
        purpose=minutes.purpose,
        decisions=minutes.decisions,
        action_items=minutes.action_items,
        digest=minutes.digest,
        editor=payload.editor,
    )
    session.add(version)
    session.flush()
    return map_minutes(minutes)


def map_minutes(minutes: models.Minutes) -> MinutesResponse:
    return MinutesResponse(
        id=minutes.id,
        title=minutes.title,
        meeting_date=minutes.meeting_date,
        participants=list(filter(None, minutes.participants.split(","))) if minutes.participants else [],
        purpose=minutes.purpose,
        decisions=minutes.decisions,
        action_items=minutes.action_items,
        digest=minutes.digest,
        raw_input=minutes.raw_input,
        created_at=minutes.created_at,
        updated_at=minutes.updated_at,
    )


def list_minutes(session: Session, query: MinutesSearchQuery) -> List[MinutesListResponse]:
    stmt = select(models.Minutes)
    if query.title:
        stmt = stmt.where(models.Minutes.title.ilike(f"%{query.title}%"))
    if query.participant:
        stmt = stmt.where(models.Minutes.participants.ilike(f"%{query.participant}%"))
    if query.start_date:
        stmt = stmt.where(models.Minutes.meeting_date >= query.start_date)
    if query.end_date:
        stmt = stmt.where(models.Minutes.meeting_date <= query.end_date)

    stmt = stmt.order_by(models.Minutes.meeting_date.desc())
    results = session.execute(stmt).scalars().all()
    return [
        MinutesListResponse(
            id=item.id,
            title=item.title,
            meeting_date=item.meeting_date,
            participants=list(filter(None, item.participants.split(","))) if item.participants else [],
            created_at=item.created_at,
        )
        for item in results
    ]


def get_minutes_detail(session: Session, minutes_id: int) -> MinutesDetailResponse:
    minutes = session.get(models.Minutes, minutes_id)
    if not minutes:
        raise ValueError("Minutes not found")

    versions = [
        MinutesVersionResponse(
            id=version.id,
            purpose=version.purpose,
            decisions=version.decisions,
            action_items=version.action_items,
            digest=version.digest,
            editor=version.editor,
            created_at=version.created_at,
        )
        for version in sorted(minutes.versions, key=lambda v: v.created_at, reverse=True)
    ]

    reminders = [
        ReminderResponse(
            id=reminder.id,
            assignee=reminder.assignee,
            action_item=reminder.action_item,
            due_date=reminder.due_date,
            status=reminder.status,
            created_at=reminder.created_at,
        )
        for reminder in sorted(minutes.reminders, key=lambda r: r.due_date)
    ]

    return MinutesDetailResponse(
        **map_minutes(minutes).dict(),
        versions=versions,
        reminders=reminders,
    )


def record_reminder(session: Session, minutes_id: int, payload: ReminderRequest) -> ReminderResponse:
    minutes = session.get(models.Minutes, minutes_id)
    if not minutes:
        raise ValueError("Minutes not found")

    reminder = models.Reminder(
        minutes_id=minutes.id,
        assignee=payload.assignee,
        action_item=payload.action_item,
        due_date=payload.due_date,
        status="scheduled",
    )
    session.add(reminder)
    session.flush()
    return ReminderResponse(
        id=reminder.id,
        assignee=reminder.assignee,
        action_item=reminder.action_item,
        due_date=reminder.due_date,
        status=reminder.status,
        created_at=reminder.created_at,
    )


def list_history(session: Session, minutes_id: int) -> List[HistoryResponse]:
    minutes = session.get(models.Minutes, minutes_id)
    if not minutes:
        raise ValueError("Minutes not found")

    history: List[HistoryResponse] = []
    previous = None
    for version in sorted(minutes.versions, key=lambda v: v.created_at):
        current = version
        if previous:
            diffs = compute_diffs(previous, current)
        else:
            diffs = [
                DiffResponse(field=field, previous="", current=getattr(current, field), diff=getattr(current, field))
                for field in ["purpose", "decisions", "action_items", "digest"]
            ]
        history.append(
            HistoryResponse(
                version=MinutesVersionResponse(
                    id=current.id,
                    purpose=current.purpose,
                    decisions=current.decisions,
                    action_items=current.action_items,
                    digest=current.digest,
                    editor=current.editor,
                    created_at=current.created_at,
                ),
                diffs=diffs,
            )
        )
        previous = current
    return history


def compute_diffs(previous: models.MinutesVersion, current: models.MinutesVersion) -> List[DiffResponse]:
    from difflib import ndiff

    diffs: List[DiffResponse] = []
    for field in ["purpose", "decisions", "action_items", "digest"]:
        prev_value = getattr(previous, field) or ""
        curr_value = getattr(current, field) or ""
        diff_text = "\n".join(ndiff(prev_value.splitlines(), curr_value.splitlines()))
        diffs.append(
            DiffResponse(
                field=field,
                previous=prev_value,
                current=curr_value,
                diff=diff_text,
            )
        )
    return diffs


def enforce_limits(summary: MinutesCreateRequest) -> MinutesCreateRequest:
    fields = ["purpose", "decisions", "action_items", "digest"]
    for field in fields:
        value = getattr(summary, field)
        if len(value) > MAX_CHARACTERS:
            setattr(summary, field, value[:MAX_CHARACTERS])

    total = sum(len(getattr(summary, field)) for field in fields)
    if total <= MAX_CHARACTERS:
        return summary

    # reduce sections proportionally while preserving冒頭を優先
    excess = total - MAX_CHARACTERS
    while excess > 0:
        for field in fields:
            value = getattr(summary, field)
            if not value:
                continue
            setattr(summary, field, value[:-1])
            excess -= 1
            if excess <= 0:
                break
    return summary
