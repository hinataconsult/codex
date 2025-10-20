from __future__ import annotations

import datetime as dt
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import session_scope
from ..schemas import (
    HistoryResponse,
    MinutesCreateRequest,
    MinutesDetailResponse,
    MinutesListResponse,
    MinutesResponse,
    MinutesSearchQuery,
    ReminderRequest,
    ReminderResponse,
    SummaryRequest,
    SummaryResponse,
)
from ..services import export as export_service
from ..services import minutes as minutes_service
from ..services import notifications
from ..services.summary import summarize

router = APIRouter(prefix="/api", tags=["minutes"])


def get_session() -> Session:
    with session_scope() as session:
        yield session


@router.post("/minutes/generate", response_model=SummaryResponse)
def generate_summary(payload: SummaryRequest) -> SummaryResponse:
    return summarize(payload)


@router.post("/minutes", response_model=MinutesResponse)
def create_minutes(payload: MinutesCreateRequest, session: Session = Depends(get_session)) -> MinutesResponse:
    sanitized = minutes_service.enforce_limits(payload)
    return minutes_service.create_minutes(session, sanitized)


@router.put("/minutes/{minutes_id}", response_model=MinutesResponse)
def update_minutes(minutes_id: int, payload: MinutesCreateRequest, session: Session = Depends(get_session)) -> MinutesResponse:
    sanitized = minutes_service.enforce_limits(payload)
    try:
        return minutes_service.update_minutes(session, minutes_id, sanitized)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/minutes", response_model=List[MinutesListResponse])
def list_minutes(
    title: str | None = None,
    participant: str | None = None,
    start_date: dt.date | None = Query(default=None),
    end_date: dt.date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> List[MinutesListResponse]:
    query = MinutesSearchQuery(title=title, participant=participant, start_date=start_date, end_date=end_date)
    return minutes_service.list_minutes(session, query)


@router.get("/minutes/{minutes_id}", response_model=MinutesDetailResponse)
def get_minutes(minutes_id: int, session: Session = Depends(get_session)) -> MinutesDetailResponse:
    try:
        return minutes_service.get_minutes_detail(session, minutes_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/minutes/{minutes_id}/history", response_model=List[HistoryResponse])
def get_history(minutes_id: int, session: Session = Depends(get_session)) -> List[HistoryResponse]:
    try:
        return minutes_service.list_history(session, minutes_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/minutes/{minutes_id}/reminders", response_model=ReminderResponse)
def create_reminder(minutes_id: int, payload: ReminderRequest, session: Session = Depends(get_session)) -> ReminderResponse:
    try:
        reminder = minutes_service.record_reminder(session, minutes_id, payload)
        return reminder
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/minutes/{minutes_id}/notifications", response_model=ReminderResponse)
def send_reminder(minutes_id: int, payload: ReminderRequest, session: Session = Depends(get_session)) -> ReminderResponse:
    try:
        return notifications.dispatch_reminder(session, minutes_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/minutes/{minutes_id}/export/pdf")
def export_pdf(minutes_id: int, session: Session = Depends(get_session)) -> StreamingResponse:
    try:
        minutes = minutes_service.get_minutes_detail(session, minutes_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    pdf_payload = MinutesResponse(**minutes.dict(exclude={"versions", "reminders"}))
    pdf_bytes = export_service.build_pdf(pdf_payload)
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=minutes-{minutes_id}.pdf"},
    )


@router.get("/minutes/export/csv")
def export_csv(
    title: str | None = None,
    participant: str | None = None,
    start_date: dt.date | None = Query(default=None),
    end_date: dt.date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    query = MinutesSearchQuery(title=title, participant=participant, start_date=start_date, end_date=end_date)
    rows = minutes_service.list_minutes(session, query)
    csv_content = export_service.build_csv(rows)
    return StreamingResponse(
        iter([csv_content.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=minutes.csv"},
    )
