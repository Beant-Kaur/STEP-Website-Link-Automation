import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import json


@dataclass
class LinkRecord:
    link_id: str
    jurisdiction: str
    topic: str
    step_section: str
    step_description: str
    original_url: str
    current_url: str = ""
    final_url: str = ""
    http_status: Optional[int] = None
    technical_status: str = ""
    redirect_status: str = ""
    page_title: str = ""
    source_organisation: str = ""
    source_domain: str = ""
    source_authority_tier: str = ""
    publication_date: str = ""
    updated_date: str = ""
    effective_date: str = ""
    version: str = ""
    content_status: str = ""
    regulatory_status: str = ""
    freshness_status: str = ""
    classification: str = ""
    issue_description: str = ""
    replacement_url: str = ""
    replacement_title: str = ""
    replacement_source: str = ""
    replacement_reason: str = ""
    confidence_score: float = 0.0
    confidence_reason: str = ""
    recommended_action: str = ""
    human_review_required: bool = False
    human_review_status: str = "pending"
    last_checked_at: datetime = field(default_factory=datetime.utcnow)
    next_check_at: datetime = field(default_factory=datetime.utcnow)
    content_hash: str = ""
    previous_content_hash: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    # Section 22 Multi-Dimensional Fields
    authority_status: str = ""
    final_status: str = ""
    content_relevance_score: int = 0
    content_accuracy_score: int = 0
    freshness_score: int = 0
    relevance_status: str = ""
    replacement_verified: bool = False
    replacement_status: str = ""
    evidence: str = "[]"
    # Section 18 — Deep Semantic Analysis Fields
    intended_subject: str = ""
    original_content_summary: str = ""
    comparison_summary: str = ""
    updated_source_found: bool = False
    anchor_text: str = ""
    section_heading: str = ""
    # Section 16 & Section 24 Comprehensive Fields
    access_status: str = ""
    content_type: str = ""
    document_type: str = ""
    authenticity_status: str = ""
    authenticity_reason: str = ""
    comparability: str = ""
    comparability_confidence: float = 0.0
    regulatory_status_reason: str = ""
    replacement_required: bool = False
    replacement_authority: str = ""
    replacement_comparability: str = ""
    replacement_confidence: float = 0.0
    recheck_performed: bool = False
    recheck_reason: str = ""
    initial_confidence: float = 0.0
    final_confidence: float = 0.0
    run_id: str = ""
    implementation_status: str = "not_reviewed"


class DatabaseRepository:
    def __init__(self, db_path: str = "step_esg_links.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS link_records (
                id TEXT PRIMARY KEY,
                jurisdiction TEXT,
                topic TEXT,
                step_section TEXT,
                step_description TEXT,
                original_url TEXT NOT NULL,
                current_url TEXT,
                final_url TEXT,
                http_status INTEGER,
                technical_status TEXT,
                redirect_status TEXT,
                page_title TEXT,
                source_organisation TEXT,
                source_domain TEXT,
                source_authority_tier TEXT,
                publication_date TEXT,
                updated_date TEXT,
                effective_date TEXT,
                version TEXT,
                content_status TEXT,
                regulatory_status TEXT,
                freshness_status TEXT,
                classification TEXT,
                issue_description TEXT,
                replacement_url TEXT,
                replacement_title TEXT,
                replacement_source TEXT,
                replacement_reason TEXT,
                confidence_score REAL,
                confidence_reason TEXT,
                recommended_action TEXT,
                human_review_required INTEGER DEFAULT 0,
                human_review_status TEXT DEFAULT 'pending',
                last_checked_at TEXT,
                next_check_at TEXT,
                content_hash TEXT,
                previous_content_hash TEXT,
                created_at TEXT,
                updated_at TEXT,
                authority_status TEXT,
                final_status TEXT,
                content_relevance_score INTEGER DEFAULT 0,
                content_accuracy_score INTEGER DEFAULT 0,
                freshness_score INTEGER DEFAULT 0,
                relevance_status TEXT,
                replacement_verified INTEGER DEFAULT 0,
                replacement_status TEXT,
                evidence TEXT
            )
        """)
        # Automated Schema Migrations for existing SQLite database
        new_cols = [
            ("authority_status", "TEXT"),
            ("final_status", "TEXT"),
            ("content_relevance_score", "INTEGER DEFAULT 0"),
            ("content_accuracy_score", "INTEGER DEFAULT 0"),
            ("freshness_score", "INTEGER DEFAULT 0"),
            ("relevance_status", "TEXT"),
            ("replacement_verified", "INTEGER DEFAULT 0"),
            ("replacement_status", "TEXT"),
            ("evidence", "TEXT"),
            # Section 18 new columns
            ("intended_subject", "TEXT"),
            ("original_content_summary", "TEXT"),
            ("comparison_summary", "TEXT"),
            ("updated_source_found", "INTEGER DEFAULT 0"),
            ("anchor_text", "TEXT"),
            ("section_heading", "TEXT"),
            # Section 16 & 24 comprehensive columns
            ("access_status", "TEXT"),
            ("content_type", "TEXT"),
            ("document_type", "TEXT"),
            ("authenticity_status", "TEXT"),
            ("authenticity_reason", "TEXT"),
            ("comparability", "TEXT"),
            ("comparability_confidence", "REAL DEFAULT 0.0"),
            ("regulatory_status_reason", "TEXT"),
            ("replacement_required", "INTEGER DEFAULT 0"),
            ("replacement_authority", "TEXT"),
            ("replacement_comparability", "TEXT"),
            ("replacement_confidence", "REAL DEFAULT 0.0"),
            ("recheck_performed", "INTEGER DEFAULT 0"),
            ("recheck_reason", "TEXT"),
            ("initial_confidence", "REAL DEFAULT 0.0"),
            ("final_confidence", "REAL DEFAULT 0.0"),
            ("run_id", "TEXT"),
            ("implementation_status", "TEXT DEFAULT 'not_reviewed'"),
        ]
        for col_name, col_type in new_cols:
            try:
                cursor.execute(f"ALTER TABLE link_records ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                total_links INTEGER,
                successful_checks INTEGER,
                failed_checks INTEGER,
                ai_evaluations INTEGER,
                replacement_candidates INTEGER,
                human_review_items INTEGER,
                errors TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                link_id TEXT,
                event_type TEXT,
                old_url TEXT,
                new_url TEXT,
                date_detected TEXT,
                date_approved TEXT,
                reason TEXT,
                evidence TEXT,
                ai_confidence REAL,
                reviewer TEXT,
                approval_status TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_link(self, link_id: str, jurisdiction: str, topic: str,
                 step_section: str, step_description: str,
                 original_url: str, link_text: str = "",
                 source_position: str = "") -> LinkRecord:
        record = LinkRecord(
            link_id=link_id,
            jurisdiction=jurisdiction,
            topic=topic,
            step_section=step_section,
            step_description=step_description,
            original_url=original_url,
            current_url=original_url,
            final_url=original_url,
        )
        self.upsert_link(record)
        return record

    def upsert_link(self, record: LinkRecord) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO link_records (
                id, jurisdiction, topic, step_section, step_description,
                original_url, current_url, final_url, http_status,
                technical_status, redirect_status, page_title, source_organisation,
                source_domain, source_authority_tier, publication_date, updated_date,
                effective_date, version, content_status, regulatory_status,
                freshness_status, classification, issue_description, replacement_url,
                replacement_title, replacement_source, replacement_reason,
                confidence_score, confidence_reason, recommended_action,
                human_review_required, human_review_status, last_checked_at,
                next_check_at, content_hash, previous_content_hash,
                created_at, updated_at, authority_status, final_status,
                content_relevance_score, content_accuracy_score, freshness_score,
                relevance_status, replacement_verified, replacement_status, evidence,
                intended_subject, original_content_summary, comparison_summary,
                updated_source_found, anchor_text, section_heading,
                access_status, content_type, document_type, authenticity_status,
                authenticity_reason, comparability, comparability_confidence,
                regulatory_status_reason, replacement_required, replacement_authority,
                replacement_comparability, replacement_confidence, recheck_performed,
                recheck_reason, initial_confidence, final_confidence, run_id, implementation_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.link_id,
            record.jurisdiction,
            record.topic,
            record.step_section,
            record.step_description,
            record.original_url,
            record.current_url,
            record.final_url,
            record.http_status,
            record.technical_status,
            record.redirect_status,
            record.page_title,
            record.source_organisation,
            record.source_domain,
            record.source_authority_tier,
            record.publication_date,
            record.updated_date,
            record.effective_date,
            record.version,
            record.content_status,
            record.regulatory_status,
            record.freshness_status,
            record.classification,
            record.issue_description,
            record.replacement_url,
            record.replacement_title,
            record.replacement_source,
            record.replacement_reason,
            record.confidence_score,
            record.confidence_reason,
            record.recommended_action,
            1 if record.human_review_required else 0,
            record.human_review_status,
            record.last_checked_at.isoformat(),
            record.next_check_at.isoformat(),
            record.content_hash,
            record.previous_content_hash,
            record.created_at.isoformat(),
            record.updated_at.isoformat(),
            record.authority_status,
            record.final_status or record.classification,
            record.content_relevance_score,
            record.content_accuracy_score,
            record.freshness_score,
            record.relevance_status,
            1 if record.replacement_verified else 0,
            record.replacement_status,
            record.evidence if isinstance(record.evidence, str) else json.dumps(record.evidence),
            record.intended_subject,
            record.original_content_summary,
            record.comparison_summary,
            1 if record.updated_source_found else 0,
            record.anchor_text,
            record.section_heading,
            record.access_status,
            record.content_type,
            record.document_type,
            record.authenticity_status,
            record.authenticity_reason,
            record.comparability,
            record.comparability_confidence,
            record.regulatory_status_reason,
            1 if record.replacement_required else 0,
            record.replacement_authority,
            record.replacement_comparability,
            record.replacement_confidence,
            1 if record.recheck_performed else 0,
            record.recheck_reason,
            record.initial_confidence,
            record.final_confidence or record.confidence_score,
            record.run_id,
            record.implementation_status or "not_reviewed",
        ))
        conn.commit()
        conn.close()

    def get_all_links(self) -> list[LinkRecord]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM link_records")
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_record(row) for row in rows]

    def get_link(self, link_id: str) -> Optional[LinkRecord]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM link_records WHERE id = ?", (link_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_record(row) if row else None

    def get_latest_link_by_url(self, original_url: str, exclude_id: str = "") -> Optional[LinkRecord]:
        conn = self._get_connection()
        cursor = conn.cursor()
        if exclude_id:
            cursor.execute(
                "SELECT * FROM link_records WHERE original_url = ? AND id != ? AND content_hash != '' ORDER BY created_at DESC LIMIT 1",
                (original_url, exclude_id),
            )
        else:
            cursor.execute(
                "SELECT * FROM link_records WHERE original_url = ? AND content_hash != '' ORDER BY created_at DESC LIMIT 1",
                (original_url,),
            )
        row = cursor.fetchone()
        conn.close()
        return self._row_to_record(row) if row else None

    def _row_to_record(self, row: sqlite3.Row) -> LinkRecord:
        keys = row.keys()
        return LinkRecord(
            link_id=row["id"],
            jurisdiction=row["jurisdiction"] or "",
            topic=row["topic"] or "",
            step_section=row["step_section"] or "",
            step_description=row["step_description"] or "",
            original_url=row["original_url"],
            current_url=row["current_url"] or "",
            final_url=row["final_url"] or "",
            http_status=row["http_status"],
            technical_status=row["technical_status"] or "",
            redirect_status=row["redirect_status"] or "",
            page_title=row["page_title"] or "",
            source_organisation=row["source_organisation"] or "",
            source_domain=row["source_domain"] or "",
            source_authority_tier=row["source_authority_tier"] or "",
            publication_date=row["publication_date"] or "",
            updated_date=row["updated_date"] or "",
            effective_date=row["effective_date"] or "",
            version=row["version"] or "",
            content_status=row["content_status"] or "",
            regulatory_status=row["regulatory_status"] or "",
            freshness_status=row["freshness_status"] or "",
            classification=row["classification"] or "",
            issue_description=row["issue_description"] or "",
            replacement_url=row["replacement_url"] or "",
            replacement_title=row["replacement_title"] or "",
            replacement_source=row["replacement_source"] or "",
            replacement_reason=row["replacement_reason"] or "",
            confidence_score=row["confidence_score"] or 0.0,
            confidence_reason=row["confidence_reason"] or "",
            recommended_action=row["recommended_action"] or "",
            human_review_required=bool(row["human_review_required"]),
            human_review_status=row["human_review_status"] or "pending",
            last_checked_at=datetime.fromisoformat(row["last_checked_at"]) if row["last_checked_at"] else datetime.utcnow(),
            next_check_at=datetime.fromisoformat(row["next_check_at"]) if row["next_check_at"] else datetime.utcnow(),
            content_hash=row["content_hash"] or "",
            previous_content_hash=row["previous_content_hash"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
            authority_status=(row["authority_status"] or "") if "authority_status" in keys else "",
            final_status=(row["final_status"] or row["classification"] or "") if "final_status" in keys else (row["classification"] or ""),
            content_relevance_score=(row["content_relevance_score"] or 0) if "content_relevance_score" in keys else 0,
            content_accuracy_score=(row["content_accuracy_score"] or 0) if "content_accuracy_score" in keys else 0,
            freshness_score=(row["freshness_score"] or 0) if "freshness_score" in keys else 0,
            relevance_status=(row["relevance_status"] or "") if "relevance_status" in keys else "",
            replacement_verified=bool(row["replacement_verified"]) if "replacement_verified" in keys else False,
            replacement_status=(row["replacement_status"] or "") if "replacement_status" in keys else "",
            evidence=(row["evidence"] or "[]") if "evidence" in keys else "[]",
            # Section 18 fields
            intended_subject=(row["intended_subject"] or "") if "intended_subject" in keys else "",
            original_content_summary=(row["original_content_summary"] or "") if "original_content_summary" in keys else "",
            comparison_summary=(row["comparison_summary"] or "") if "comparison_summary" in keys else "",
            updated_source_found=bool(row["updated_source_found"]) if "updated_source_found" in keys else False,
            anchor_text=(row["anchor_text"] or "") if "anchor_text" in keys else "",
            section_heading=(row["section_heading"] or "") if "section_heading" in keys else "",
            # Section 16 & 24 comprehensive fields
            access_status=(row["access_status"] or "") if "access_status" in keys else "",
            content_type=(row["content_type"] or "") if "content_type" in keys else "",
            document_type=(row["document_type"] or "") if "document_type" in keys else "",
            authenticity_status=(row["authenticity_status"] or "") if "authenticity_status" in keys else "",
            authenticity_reason=(row["authenticity_reason"] or "") if "authenticity_reason" in keys else "",
            comparability=(row["comparability"] or "") if "comparability" in keys else "",
            comparability_confidence=float(row["comparability_confidence"] or 0.0) if "comparability_confidence" in keys else 0.0,
            regulatory_status_reason=(row["regulatory_status_reason"] or "") if "regulatory_status_reason" in keys else "",
            replacement_required=bool(row["replacement_required"]) if "replacement_required" in keys else False,
            replacement_authority=(row["replacement_authority"] or "") if "replacement_authority" in keys else "",
            replacement_comparability=(row["replacement_comparability"] or "") if "replacement_comparability" in keys else "",
            replacement_confidence=float(row["replacement_confidence"] or 0.0) if "replacement_confidence" in keys else 0.0,
            recheck_performed=bool(row["recheck_performed"]) if "recheck_performed" in keys else False,
            recheck_reason=(row["recheck_reason"] or "") if "recheck_reason" in keys else "",
            initial_confidence=float(row["initial_confidence"] or 0.0) if "initial_confidence" in keys else 0.0,
            final_confidence=float(row["final_confidence"] or row["confidence_score"] or 0.0) if "final_confidence" in keys else float(row["confidence_score"] or 0.0),
            run_id=(row["run_id"] or "") if "run_id" in keys else "",
            implementation_status=(row["implementation_status"] or "not_reviewed") if "implementation_status" in keys else "not_reviewed",
        )

    def log_pipeline_run(self, run_id: str, start_time: datetime, end_time: datetime,
                         total_links: int, successful_checks: int, failed_checks: int,
                         ai_evaluations: int, replacement_candidates: int,
                         human_review_items: int, errors: str) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pipeline_runs (
                run_id, start_time, end_time, total_links, successful_checks,
                failed_checks, ai_evaluations, replacement_candidates,
                human_review_items, errors
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            start_time.isoformat(),
            end_time.isoformat(),
            total_links,
            successful_checks,
            failed_checks,
            ai_evaluations,
            replacement_candidates,
            human_review_items,
            errors,
        ))
        conn.commit()
        conn.close()

    def log_audit(self, link_id: str, event_type: str, old_url: str, new_url: str,
                  date_detected: datetime, date_approved: Optional[datetime],
                  reason: str, evidence: str, ai_confidence: float,
                  reviewer: str, approval_status: str) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (
                run_id, link_id, event_type, old_url, new_url,
                date_detected, date_approved, reason, evidence,
                ai_confidence, reviewer, approval_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            None,
            link_id,
            event_type,
            old_url,
            new_url,
            date_detected.isoformat(),
            date_approved.isoformat() if date_approved else None,
            reason,
            evidence,
            ai_confidence,
            reviewer,
            approval_status,
            datetime.utcnow().isoformat(),
        ))
        conn.commit()
        conn.close()

    def apply_replacement(self, link_id: str, reviewer: str = "User") -> Optional[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM link_records WHERE id = ?", (link_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        replacement_url = row["replacement_url"]
        if not replacement_url:
            conn.close()
            return None
            
        old_url = row["current_url"] or row["original_url"]
        now_str = datetime.utcnow().isoformat()
        
        cursor.execute(
            "UPDATE link_records SET current_url = ?, implementation_status = 'applied', updated_at = ? WHERE id = ?",
            (replacement_url, now_str, link_id)
        )
        cursor.execute("""
            INSERT INTO audit_log (
                run_id, link_id, event_type, old_url, new_url, date_detected, date_approved, reason, evidence, ai_confidence, reviewer, approval_status, created_at
            ) VALUES (?, ?, 'applied', ?, ?, ?, ?, ?, ?, ?, ?, 'approved', ?)
        """, (
            row["run_id"] or "",
            link_id,
            old_url,
            replacement_url,
            row["last_checked_at"] or now_str,
            now_str,
            row["replacement_reason"] or "User verified and applied replacement link.",
            str(row["evidence"] or ""),
            float(row["final_confidence"] or row["confidence_score"] or 0.0),
            reviewer,
            now_str
        ))
        conn.commit()
        conn.close()
        return {
            "link_id": link_id,
            "old_url": old_url,
            "new_url": replacement_url,
            "implementation_status": "applied",
            "applied_at": now_str,
            "reviewer": reviewer
        }

    def revert_replacement(self, link_id: str, reviewer: str = "User") -> Optional[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM link_records WHERE id = ?", (link_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
            
        original_url = row["original_url"]
        current_url = row["current_url"] or original_url
        now_str = datetime.utcnow().isoformat()
        
        cursor.execute(
            "UPDATE link_records SET current_url = ?, implementation_status = 'reverted', updated_at = ? WHERE id = ?",
            (original_url, now_str, link_id)
        )
        cursor.execute("""
            INSERT INTO audit_log (
                run_id, link_id, event_type, old_url, new_url, date_detected, date_approved, reason, evidence, ai_confidence, reviewer, approval_status, created_at
            ) VALUES (?, ?, 'reverted', ?, ?, ?, ?, ?, ?, ?, ?, 'reverted', ?)
        """, (
            row["run_id"] or "",
            link_id,
            current_url,
            original_url,
            row["last_checked_at"] or now_str,
            now_str,
            "User reverted to original link.",
            str(row["evidence"] or ""),
            float(row["final_confidence"] or row["confidence_score"] or 0.0),
            reviewer,
            now_str
        ))
        conn.commit()
        conn.close()
        return {
            "link_id": link_id,
            "old_url": current_url,
            "new_url": original_url,
            "implementation_status": "reverted",
            "reverted_at": now_str,
            "reviewer": reviewer
        }

    def get_audit_history(self, link_id: str) -> list[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_log WHERE link_id = ? ORDER BY id DESC", (link_id,))
        rows = cursor.fetchall()
        conn.close()
        history = []
        for r in rows:
            history.append({
                "id": r["id"],
                "link_id": r["link_id"],
                "event_type": r["event_type"],
                "old_url": r["old_url"],
                "new_url": r["new_url"],
                "date_approved": r["date_approved"] or r["created_at"],
                "reason": r["reason"],
                "reviewer": r["reviewer"],
                "approval_status": r["approval_status"]
            })
        return history
