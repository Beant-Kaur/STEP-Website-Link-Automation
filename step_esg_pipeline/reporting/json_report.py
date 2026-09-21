import json
from typing import Optional, List, Dict, Any

from database.models import LinkRecord


class JsonReport:
    @staticmethod
    def generate(records: list[LinkRecord], path: str) -> None:
        data = []
        for record in records:
            # Parse evidence from JSON string if needed
            evidence_data = []
            if record.evidence:
                try:
                    evidence_data = json.loads(record.evidence) if isinstance(record.evidence, str) else record.evidence
                except Exception:
                    evidence_data = [record.evidence]

            data.append({
                "link_id": record.link_id,
                "jurisdiction": record.jurisdiction,
                "topic": record.topic,
                "step_section": record.step_section,
                "step_description": record.step_description,
                "anchor_text": getattr(record, "anchor_text", ""),
                "section_heading": getattr(record, "section_heading", ""),
                "original_url": record.original_url,
                "current_url": record.current_url,
                "final_url": record.final_url,
                "http_status": record.http_status,
                "technical_status": record.technical_status,
                "content_status": record.content_status,
                "redirect_status": record.redirect_status,
                "page_title": record.page_title,
                "source_organisation": record.source_organisation,
                "source_domain": record.source_domain,
                "source_authority_tier": record.source_authority_tier,
                "authority_status": record.authority_status,
                "publication_date": record.publication_date,
                "version": record.version,
                # Section 18 — Deep Semantic Analysis
                "intended_subject": getattr(record, "intended_subject", ""),
                "original_content_summary": getattr(record, "original_content_summary", ""),
                "classification": record.classification,
                "run_id": record.run_id or (record.link_id.split("_")[0] if "_" in record.link_id else ""),
                "final_status": record.final_status or record.classification,
                "freshness_status": record.freshness_status,
                "regulatory_status": record.regulatory_status,
                "regulatory_status_reason": record.regulatory_status_reason,
                "access_status": record.access_status,
                "content_type": record.content_type,
                "document_type": record.document_type,
                "authenticity_status": record.authenticity_status,
                "authenticity_reason": record.authenticity_reason,
                "comparability": record.comparability,
                "comparability_confidence": record.comparability_confidence,
                "relevance_status": record.relevance_status,
                "content_relevance_score": record.content_relevance_score,
                "content_accuracy_score": record.content_accuracy_score,
                "freshness_score": record.freshness_score,
                "issue_description": record.issue_description,
                "replacement_required": bool(record.replacement_required or record.replacement_url),
                "replacement_url": record.replacement_url,
                "replacement_title": record.replacement_title,
                "replacement_authority": record.replacement_authority,
                "replacement_comparability": record.replacement_comparability,
                "replacement_confidence": record.replacement_confidence,
                "replacement_reason": record.replacement_reason,
                "replacement_verified": record.replacement_verified,
                "replacement_status": record.replacement_status,
                "updated_source_found": getattr(record, "updated_source_found", False),
                "comparison_summary": getattr(record, "comparison_summary", ""),
                "recheck_performed": record.recheck_performed,
                "recheck_reason": record.recheck_reason,
                "initial_confidence": record.initial_confidence,
                "final_confidence": record.final_confidence or record.confidence_score,
                "confidence_score": record.confidence_score,
                "confidence_reason": record.confidence_reason,
                "reason": record.issue_description or record.replacement_reason or record.confidence_reason,
                "evidence": evidence_data,
                "recommended_action": record.recommended_action,
                "human_review_required": record.human_review_required,
                "checked_at": record.last_checked_at.isoformat() if record.last_checked_at else "",
                "content_hash": record.content_hash,
                # Regulatory Discovery Engine Fields
                "pdf_url": getattr(record, "pdf_url", ""),
                "candidate_pdf_url": getattr(record, "candidate_pdf_url", ""),
                "pdf_validation_status": getattr(record, "pdf_validation_status", ""),
                "pdf_magic_signature_verified": bool(getattr(record, "pdf_magic_signature_verified", False)),
                "discovered_trail": json.loads(record.discovered_trail) if getattr(record, "discovered_trail", "") and isinstance(record.discovered_trail, str) and record.discovered_trail.startswith("[") else getattr(record, "discovered_trail", []),
                "extracted_dates_detail": json.loads(record.extracted_dates_detail) if getattr(record, "extracted_dates_detail", "") and isinstance(record.extracted_dates_detail, str) and record.extracted_dates_detail.startswith("[") else getattr(record, "extracted_dates_detail", []),
                "document_references": json.loads(record.document_references) if getattr(record, "document_references", "") and isinstance(record.document_references, str) and record.document_references.startswith("[") else getattr(record, "document_references", []),
                "version_chain": json.loads(record.version_chain) if getattr(record, "version_chain", "") and isinstance(record.version_chain, str) and record.version_chain.startswith("[") else getattr(record, "version_chain", []),
                "official_search_performed": bool(getattr(record, "official_search_performed", False)),
                # Section 3 & 16 Redesign Fields
                "section": getattr(record, "section", "ESG Legislative Landscape"),
                "country": getattr(record, "country", record.jurisdiction),
                "country_confidence": getattr(record, "country_confidence", 1.0),
                "instrument_name": getattr(record, "instrument_name", record.step_description),
                "instrument_type": getattr(record, "instrument_type", ""),
                "regulatory_topic": getattr(record, "regulatory_topic", record.topic),
                "regulated_population": getattr(record, "regulated_population", ""),
                "technical_page_title": getattr(record, "technical_page_title", ""),
                "candidate_authority": getattr(record, "candidate_authority", ""),
                "candidate_status": getattr(record, "candidate_status", "NONE_FOUND"),
                "replacement_relationship": getattr(record, "replacement_relationship", ""),
                "technical_confidence": getattr(record, "technical_confidence", 0.0),
                "authority_confidence": getattr(record, "authority_confidence", 0.0),
                "identity_confidence": getattr(record, "identity_confidence", 0.0),
                "currentness_confidence": getattr(record, "currentness_confidence", 0.0),
                "replacement_confidence": getattr(record, "replacement_confidence", 0.0),
                "overall_confidence": getattr(record, "overall_confidence", record.confidence_score),
                "final_decision": getattr(record, "final_decision", record.recommended_action),
                "why_summary": getattr(record, "why_summary", ""),
                "evidence_json": getattr(record, "evidence_json", "[]"),
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
