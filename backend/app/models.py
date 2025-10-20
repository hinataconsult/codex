from __future__ import annotations

import datetime as dt
from typing import List, Optional

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Minutes(Base):
    __tablename__ = "minutes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    meeting_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    participants: Mapped[str] = mapped_column(String(1024), default="")
    purpose: Mapped[str] = mapped_column(Text, default="")
    decisions: Mapped[str] = mapped_column(Text, default="")
    action_items: Mapped[str] = mapped_column(Text, default="")
    digest: Mapped[str] = mapped_column(Text, default="")
    raw_input: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    versions: Mapped[List[MinutesVersion]] = relationship("MinutesVersion", back_populates="minutes", cascade="all, delete-orphan")
    reminders: Mapped[List[Reminder]] = relationship("Reminder", back_populates="minutes", cascade="all, delete-orphan")


class MinutesVersion(Base):
    __tablename__ = "minutes_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    minutes_id: Mapped[int] = mapped_column(ForeignKey("minutes.id", ondelete="CASCADE"))
    purpose: Mapped[str] = mapped_column(Text)
    decisions: Mapped[str] = mapped_column(Text)
    action_items: Mapped[str] = mapped_column(Text)
    digest: Mapped[str] = mapped_column(Text)
    editor: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    minutes: Mapped[Minutes] = relationship("Minutes", back_populates="versions")


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    minutes_id: Mapped[int] = mapped_column(ForeignKey("minutes.id", ondelete="CASCADE"), nullable=False)
    assignee: Mapped[str] = mapped_column(String(255), nullable=False)
    action_item: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow, nullable=False)

    minutes: Mapped[Minutes] = relationship("Minutes", back_populates="reminders")
