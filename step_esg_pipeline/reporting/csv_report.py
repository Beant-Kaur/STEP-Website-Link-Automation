import csv
import json
from typing import List

from database.models import LinkRecord


class CsvReport:
    @staticmethod
    def generate(records: List[LinkRecord], path: str) -> None:
        fieldnames = [
            "link_id", "section", "country", "country_confidence", "instrument_name", "instrument_type",
            "regulatory_topic", "regulated_population", "original_url", "final_url", "http_status",
            "technical_status", "technical_page_title", "authority", "authority_status",
            "regulatory_status", "regulatory_status_reason", "candidate_url", "candidate_title",
            "candidate_authority", "candidate_status", "replacement_relationship",
            "technical_confidence", "authority_confidence", "identity_confidence",
            "currentness_confidence", "replacement_confidence", "overall_confidence",
            "final_decision", "recommended_action", "human_review_required", "why_summary",
            "pdf_url", "candidate_pdf_url", "pdf_validation_status", "evidence", "checked_at", "run_id"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow({
                    "link_id": record.link_id,
                    "section": record.section or "ESG Legislative Landscape",
                    "country": record.country or record.jurisdiction,
                    "country_confidence": record.country_confidence,
                    "instrument_name": record.instrument_name or record.step_description,
                    "instrument_type": record.instrument_type,
                    "regulatory_topic": record.regulatory_topic or record.topic,
                    "regulated_population": record.regulated_population,
                    "original_url": record.original_url,
                    "final_url": record.final_url,
                    "http_status": record.http_status or "",
                    "technical_status": record.technical_status,
                    "technical_page_title": record.technical_page_title,
                    "authority": record.authority or record.source_organisation,
                    "authority_status": record.authority_status,
                    "regulatory_status": record.regulatory_status,
                    "regulatory_status_reason": record.regulatory_status_reason,
                    "candidate_url": record.replacement_url,
                    "candidate_title": record.replacement_title,
                    "candidate_authority": record.candidate_authority or record.replacement_authority,
                    "candidate_status": record.candidate_status,
                    "replacement_relationship": record.replacement_relationship or record.replacement_comparability,
                    "technical_confidence": record.technical_confidence,
                    "authority_confidence": record.authority_confidence,
                    "identity_confidence": record.identity_confidence,
                    "currentness_confidence": record.currentness_confidence,
                    "replacement_confidence": record.replacement_confidence,
                    "overall_confidence": record.overall_confidence or record.confidence_score,
                    "final_decision": record.final_decision or record.recommended_action,
                    "recommended_action": record.recommended_action,
                    "human_review_required": "YES" if record.human_review_required else "NO",
                    "why_summary": record.why_summary,
                    "pdf_url": record.pdf_url,
                    "candidate_pdf_url": record.candidate_pdf_url,
                    "pdf_validation_status": record.pdf_validation_status,
                    "evidence": record.evidence,
                    "checked_at": record.last_checked_at.isoformat() if record.last_checked_at else "",
                    "run_id": record.run_id,
                })
