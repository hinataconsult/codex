from __future__ import annotations

import datetime as dt
from typing import List

from sqlalchemy.orm import Session

from .. import models
from ..schemas import ReminderRequest, ReminderResponse


class NotificationLog:
    """A lightweight notification ledger to simulate email/chat delivery."""

    def __init__(self) -> None:
        self.entries: List[str] = []

    def record(self, message: str) -> None:
        timestamp = dt.datetime.utcnow().isoformat()
        self.entries.append(f"[{timestamp}] {message}")


notification_log = NotificationLog()


def dispatch_reminder(session: Session, minutes_id: int, reminder: ReminderRequest) -> ReminderResponse:
    minutes = session.get(models.Minutes, minutes_id)
    if not minutes:
        raise ValueError("Minutes not found")

    entry = models.Reminder(
        minutes_id=minutes_id,
        assignee=reminder.assignee,
        action_item=reminder.action_item,
        due_date=reminder.due_date,
        status="sent",
    )
    session.add(entry)
    session.flush()

    notification_log.record(
        f"Reminder sent to {entry.assignee} for '{entry.action_item}' due {entry.due_date.isoformat()}"
    )

    return ReminderResponse(
        id=entry.id,
        assignee=entry.assignee,
        action_item=entry.action_item,
        due_date=entry.due_date,
        status=entry.status,
        created_at=entry.created_at,
    )
