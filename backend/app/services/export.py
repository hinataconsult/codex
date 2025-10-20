from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Iterable

from fpdf import FPDF

from ..schemas import MinutesListResponse, MinutesResponse


class MinutesPDF(FPDF):
    def header(self) -> None:
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "議事録", ln=True, align="C")
        self.ln(5)


def build_pdf(minutes: MinutesResponse) -> bytes:
    pdf = MinutesPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"タイトル: {minutes.title}", ln=True)
    pdf.cell(0, 10, f"会議日: {minutes.meeting_date}", ln=True)
    pdf.multi_cell(0, 10, f"参加者: {', '.join(minutes.participants)}")

    pdf.set_font("Helvetica", "B", 13)
    sections = {
        "会議の目的": minutes.purpose,
        "決定事項": minutes.decisions,
        "宿題": minutes.action_items,
        "議事要旨": minutes.digest,
    }
    for header, body in sections.items():
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, header, ln=True)
        pdf.set_font("Helvetica", "", 12)
        pdf.multi_cell(0, 8, body or "(未入力)")

    return bytes(pdf.output(dest="S"))


def build_csv(rows: Iterable[MinutesListResponse]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["ID", "タイトル", "会議日", "参加者", "作成日時"])
    for row in rows:
        writer.writerow([row.id, row.title, row.meeting_date.isoformat(), ", ".join(row.participants), row.created_at.isoformat()])
    return buffer.getvalue()
