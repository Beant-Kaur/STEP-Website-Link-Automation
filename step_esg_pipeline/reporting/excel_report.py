"""
Excel report generator for the STEP ESG Link Monitoring Pipeline.
Produces a formatted .xlsx file with all Section 23 columns for human review.
Requires: openpyxl >= 3.1.0
"""
import json
from datetime import datetime
from pathlib import Path
from typing import List

from database.models import LinkRecord

try:
    import openpyxl
    from openpyxl.styles import (
        Font, PatternFill, Alignment, Border, Side, GradientFill
    )
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


# ------------------------------------------------------------------
# Color palette (professional ESG monitoring report theme)
# ------------------------------------------------------------------
COLOR_HEADER_BG   = "1E3A5F"   # Deep navy
COLOR_HEADER_FG   = "FFFFFF"
COLOR_VALID       = "D6F5E3"   # Soft green
COLOR_OUTDATED    = "FFF3CD"   # Soft amber
COLOR_BROKEN      = "FDECEA"   # Soft red
COLOR_RESTRICTED  = "E8EAF6"   # Soft indigo
COLOR_REVIEW      = "FFF8E1"   # Soft yellow
COLOR_ALT_ROW     = "F8FAFC"   # Very light blue-grey
COLOR_CONFIDENCE_HIGH = "27AE60"
COLOR_CONFIDENCE_MED  = "F39C12"
COLOR_CONFIDENCE_LOW  = "E74C3C"


def _classification_color(classification: str) -> str:
    c = (classification or "").upper()
    if c in ("VALID_AND_CURRENT", "CURRENT_WITH_AMENDMENTS"):
        return COLOR_VALID
    if c in ("WORKING_BUT_OUTDATED", "WORKING_BUT_REGULATORY_STATUS_CHANGED",
             "WORKING_BUT_OLD_VERSION", "WORKING_BUT_NON_OFFICIAL",
             "VALID_BUT_REDIRECTED", "WRONG_DESTINATION"):
        return COLOR_OUTDATED
    if c in ("BROKEN", "BROKEN_SOFT_404"):
        return COLOR_BROKEN
    if c in ("ACCESS_RESTRICTED", "TEMPORARILY_UNAVAILABLE"):
        return COLOR_RESTRICTED
    return COLOR_REVIEW


def _confidence_label(score: float) -> str:
    if score >= 0.80:
        return f"{int(score * 100)}% HIGH"
    if score >= 0.55:
        return f"{int(score * 100)}% MEDIUM"
    return f"{int(score * 100)}% LOW"


# Section 16 Master Prompt Column Definitions: (header_label, field_extractor)
COLUMNS = [
    ("No.", lambda r, i: i),
    ("URL", lambda r, i: r.original_url or ""),
    ("Final URL", lambda r, i: r.final_url or ""),
    ("HTTP Status", lambda r, i: r.http_status or ""),
    ("Access Status", lambda r, i: r.access_status or ""),
    ("Content Type", lambda r, i: r.content_type or ""),
    ("Original Title", lambda r, i: r.page_title or ""),
    ("Issuer", lambda r, i: r.source_organisation or ""),
    ("Jurisdiction", lambda r, i: r.jurisdiction or ""),
    ("Topic", lambda r, i: r.topic or ""),
    ("Document Type", lambda r, i: r.document_type or ""),
    ("Version", lambda r, i: r.version or ""),
    ("Publication Date", lambda r, i: r.publication_date or ""),
    ("Effective Date", lambda r, i: r.effective_date or ""),
    ("Authority Status", lambda r, i: r.authority_status or ""),
    ("Authenticity Status", lambda r, i: r.authenticity_status or ""),
    ("Comparability", lambda r, i: r.comparability or ""),
    ("Comparability Confidence", lambda r, i: f"{int((r.comparability_confidence or 0.0) * 100)}%" if r.comparability_confidence else ""),
    ("Freshness Status", lambda r, i: r.freshness_status or ""),
    ("Regulatory Status", lambda r, i: r.regulatory_status or ""),
    ("Regulatory Status Reason", lambda r, i: r.regulatory_status_reason or ""),
    ("Replacement Required", lambda r, i: "YES" if r.replacement_required else "No"),
    ("Recommended Replacement", lambda r, i: r.replacement_url or ""),
    ("Replacement Authority", lambda r, i: r.replacement_authority or ""),
    ("Replacement Comparability", lambda r, i: r.replacement_comparability or ""),
    ("Replacement Confidence", lambda r, i: f"{int((r.replacement_confidence or 0.0) * 100)}%" if r.replacement_confidence else ""),
    ("Recheck Performed", lambda r, i: "YES" if r.recheck_performed else "No"),
    ("Initial Confidence", lambda r, i: f"{int((r.initial_confidence or 0.0) * 100)}%" if r.initial_confidence else ""),
    ("Final Confidence", lambda r, i: _confidence_label(r.confidence_score)),
    ("Recommended Action", lambda r, i: r.recommended_action or ""),
    ("Human Review Required", lambda r, i: "YES" if r.human_review_required else "No"),
    ("Reason", lambda r, i: r.issue_description or r.replacement_reason or ""),
    ("Evidence", lambda r, i: _first_evidence(r.evidence, 3)),
    ("Checked At", lambda r, i: r.last_checked_at.strftime("%Y-%m-%d %H:%M") if r.last_checked_at else ""),
    ("Run ID", lambda r, i: r.run_id or (r.link_id.split("_")[0] if "_" in r.link_id else "")),
]


def _first_evidence(evidence_str, n: int = 3) -> str:
    try:
        ev = json.loads(evidence_str) if isinstance(evidence_str, str) else (evidence_str or [])
    except Exception:
        ev = []
    return "\n".join(f"• {e}" for e in ev[:n])


class ExcelReport:
    @staticmethod
    def generate(records: List[LinkRecord], path: str) -> None:
        if not OPENPYXL_AVAILABLE:
            raise RuntimeError(
                "openpyxl is not installed. Run: pip install openpyxl>=3.1.0"
            )

        wb = openpyxl.Workbook()

        # ----------------------------------------------------------------
        # Sheet 1: All Links
        # ----------------------------------------------------------------
        ws = wb.active
        ws.title = "All Links"
        ExcelReport._write_sheet(ws, records, title="STEP ESG Link Validation Report")

        # ----------------------------------------------------------------
        # Sheet 2: Needs Action (non-valid links only)
        # ----------------------------------------------------------------
        action_records = [
            r for r in records
            if (r.final_status or r.classification or "").upper() not in (
                "VALID_AND_CURRENT", "CURRENT_WITH_AMENDMENTS"
            )
        ]
        ws2 = wb.create_sheet("Needs Action")
        ExcelReport._write_sheet(ws2, action_records, title="STEP ESG — Links Needing Review or Replacement")

        # ----------------------------------------------------------------
        # Sheet 3: Summary Stats
        # ----------------------------------------------------------------
        ws3 = wb.create_sheet("Summary")
        ExcelReport._write_summary(ws3, records)

        wb.save(path)

    @staticmethod
    def _write_sheet(ws, records: List[LinkRecord], title: str = "") -> None:
        # Title row
        ws.merge_cells(f"A1:{get_column_letter(len(COLUMNS))}1")
        title_cell = ws["A1"]
        title_cell.value = title
        title_cell.font = Font(name="Calibri", bold=True, size=14, color=COLOR_HEADER_FG)
        title_cell.fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
        title_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

        # Timestamp row
        ws.merge_cells(f"A2:{get_column_letter(len(COLUMNS))}2")
        ts_cell = ws["A2"]
        ts_cell.value = f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} | Total links: {len(records)}"
        ts_cell.font = Font(name="Calibri", italic=True, size=10, color="666666")
        ts_cell.alignment = Alignment(horizontal="center")

        # Column headers
        header_fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
        header_font = Font(name="Calibri", bold=True, size=10, color=COLOR_HEADER_FG)
        thin = Side(style="thin", color="CCCCCC")
        border = Border(left=thin, right=thin, bottom=thin)

        for col_idx, (col_label, _) in enumerate(COLUMNS, start=1):
            cell = ws.cell(row=3, column=col_idx, value=col_label)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border
        ws.row_dimensions[3].height = 36

        # Data rows
        normal_font = Font(name="Calibri", size=9)
        url_font = Font(name="Calibri", size=9, color="1565C0", underline="single")
        alt_fill = PatternFill("solid", fgColor=COLOR_ALT_ROW)
        center = Alignment(horizontal="center", vertical="top", wrap_text=True)
        left = Alignment(horizontal="left", vertical="top", wrap_text=True)

        for row_idx, record in enumerate(records, start=1):
            excel_row = row_idx + 3
            row_fill_color = _classification_color(record.final_status or record.classification)
            row_fill = PatternFill("solid", fgColor=row_fill_color) if row_idx % 2 == 0 else (
                PatternFill("solid", fgColor=COLOR_ALT_ROW) if row_fill_color == COLOR_VALID else PatternFill("solid", fgColor=row_fill_color)
            )
            # For VALID rows use alternating subtle fill
            if (record.final_status or record.classification or "").upper() in ("VALID_AND_CURRENT", "CURRENT_WITH_AMENDMENTS"):
                row_fill = PatternFill("solid", fgColor=COLOR_ALT_ROW if row_idx % 2 == 0 else "FFFFFF")

            for col_idx, (col_label, extractor) in enumerate(COLUMNS, start=1):
                value = extractor(record, row_idx)
                cell = ws.cell(row=excel_row, column=col_idx, value=value)
                cell.fill = row_fill
                cell.border = border
                # URL columns: add hyperlink styling
                if col_label in ("Original URL", "Recommended Replacement URL") and value and str(value).startswith("http"):
                    cell.font = url_font
                    try:
                        cell.hyperlink = str(value)
                    except Exception:
                        pass
                    cell.alignment = left
                elif col_label in ("No.", "HTTP Status", "Confidence", "Content Accuracy %",
                                   "Human Review Required", "Replacement Verified"):
                    cell.font = normal_font
                    cell.alignment = center
                else:
                    cell.font = normal_font
                    cell.alignment = left

        # Column widths (approximate)
        col_widths = [5, 18, 28, 42, 30, 28, 22, 35, 45, 22, 22, 12, 25, 10, 14, 14, 42, 32, 14, 45, 22, 14, 40, 50, 18]
        for col_idx, width in enumerate(col_widths, start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = min(width, 65)

        # Freeze header rows
        ws.freeze_panes = "A4"

        # Auto-filter on header row
        ws.auto_filter.ref = f"A3:{get_column_letter(len(COLUMNS))}3"

    @staticmethod
    def _write_summary(ws, records: List[LinkRecord]) -> None:
        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 18

        header_fill = PatternFill("solid", fgColor=COLOR_HEADER_BG)
        header_font = Font(name="Calibri", bold=True, size=13, color="FFFFFF")

        ws.merge_cells("A1:B1")
        ws["A1"].value = "STEP ESG Link Validation — Summary"
        ws["A1"].fill = header_fill
        ws["A1"].font = header_font
        ws["A1"].alignment = Alignment(horizontal="center")
        ws.row_dimensions[1].height = 28

        def count(statuses):
            return sum(
                1 for r in records
                if (r.final_status or r.classification or "").upper() in statuses
            )

        total = len(records)
        valid = count({"VALID_AND_CURRENT", "CURRENT_WITH_AMENDMENTS"})
        outdated = count({"WORKING_BUT_OUTDATED", "WORKING_BUT_REGULATORY_STATUS_CHANGED",
                          "WORKING_BUT_OLD_VERSION", "WORKING_BUT_NON_OFFICIAL"})
        broken = count({"BROKEN", "BROKEN_SOFT_404", "WRONG_DESTINATION"})
        restricted = count({"ACCESS_RESTRICTED", "TEMPORARILY_UNAVAILABLE"})
        review = sum(1 for r in records if r.human_review_required)
        replacement_rec = sum(1 for r in records if r.replacement_url)
        avg_confidence = (sum(r.confidence_score for r in records) / total * 100) if total else 0

        stats = [
            ("Total Links Analysed", total),
            ("Valid & Current", valid),
            ("Outdated / Status Changed", outdated),
            ("Broken / Dead Links", broken),
            ("Access Restricted", restricted),
            ("Replacement Recommended", replacement_rec),
            ("Needs Human Review", review),
            ("Average Confidence Score", f"{avg_confidence:.1f}%"),
            ("Report Generated (UTC)", datetime.utcnow().strftime("%Y-%m-%d %H:%M")),
        ]

        label_font = Font(name="Calibri", size=11)
        value_font = Font(name="Calibri", bold=True, size=11)
        thin = Side(style="thin", color="CCCCCC")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        for row_idx, (label, value) in enumerate(stats, start=2):
            lc = ws.cell(row=row_idx, column=1, value=label)
            vc = ws.cell(row=row_idx, column=2, value=value)
            lc.font = label_font
            vc.font = value_font
            lc.border = border
            vc.border = border
            vc.alignment = Alignment(horizontal="center")
            if row_idx % 2 == 0:
                for cell in [lc, vc]:
                    cell.fill = PatternFill("solid", fgColor=COLOR_ALT_ROW)
