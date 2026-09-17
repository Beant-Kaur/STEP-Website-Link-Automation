import csv
import json
from typing import Optional

from database.models import DatabaseRepository, LinkRecord


class CsvReport:
    @staticmethod
    def generate(records: list[LinkRecord], path: str) -> None:
        fieldnames = [
            "link_id", "run_id", "url", "final_url", "http_status", "access_status",
            "content_type", "original_title", "issuer", "jurisdiction", "topic",
            "document_type", "version", "publication_date", "effective_date",
            "authority_status", "authenticity_status", "comparability", "comparability_confidence",
            "freshness_status", "regulatory_status", "regulatory_status_reason",
            "replacement_required", "recommended_replacement", "replacement_authority",
            "replacement_comparability", "replacement_confidence", "recheck_performed",
            "initial_confidence", "final_confidence", "recommended_action",
            "human_review_required", "reason", "evidence", "checked_at"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow({
                    "link_id": record.link_id,
                    "run_id": record.run_id or (record.link_id.split("_")[0] if "_" in record.link_id else ""),
                    "url": record.original_url,
                    "final_url": record.final_url,
                    "http_status": record.http_status or "",
                    "access_status": record.access_status,
                    "content_type": record.content_type,
                    "original_title": record.page_title,
                    "issuer": record.source_organisation,
                    "jurisdiction": record.jurisdiction,
                    "topic": record.topic,
                    "document_type": record.document_type,
                    "version": record.version,
                    "publication_date": record.publication_date,
                    "effective_date": record.effective_date,
                    "authority_status": record.authority_status,
                    "authenticity_status": record.authenticity_status,
                    "comparability": record.comparability,
                    "comparability_confidence": record.comparability_confidence,
                    "freshness_status": record.freshness_status,
                    "regulatory_status": record.regulatory_status,
                    "regulatory_status_reason": record.regulatory_status_reason,
                    "replacement_required": "YES" if record.replacement_required else "NO",
                    "recommended_replacement": record.replacement_url,
                    "replacement_authority": record.replacement_authority,
                    "replacement_comparability": record.replacement_comparability,
                    "replacement_confidence": record.replacement_confidence,
                    "recheck_performed": "YES" if record.recheck_performed else "NO",
                    "initial_confidence": record.initial_confidence,
                    "final_confidence": record.final_confidence or record.confidence_score,
                    "recommended_action": record.recommended_action,
                    "human_review_required": "YES" if record.human_review_required else "NO",
                    "reason": record.issue_description or record.replacement_reason,
                    "evidence": record.evidence,
                    "checked_at": record.last_checked_at.isoformat() if record.last_checked_at else "",
                })


class JsonReport:
    @staticmethod
    def generate(records: list[LinkRecord], path: str) -> None:
        data = []
        for record in records:
            data.append({
                "link_id": record.link_id,
                "jurisdiction": record.jurisdiction,
                "topic": record.topic,
                "step_section": record.step_section,
                "step_description": record.step_description,
                "original_url": record.original_url,
                "current_url": record.current_url,
                "final_url": record.final_url,
                "http_status": record.http_status,
                "technical_status": record.technical_status,
                "redirect_status": record.redirect_status,
                "page_title": record.page_title,
                "source_organisation": record.source_organisation,
                "source_domain": record.source_domain,
                "source_authority_tier": record.source_authority_tier,
                "publication_date": record.publication_date,
                "version": record.version,
                "classification": record.classification,
                "freshness_status": record.freshness_status,
                "replacement_url": record.replacement_url,
                "confidence_score": record.confidence_score,
                "recommended_action": record.recommended_action,
                "human_review_required": record.human_review_required,
                "human_review_status": record.human_review_status,
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
