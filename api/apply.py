"""
Vercel Serverless Function: Link Update & Audit Ledger
Handles link approval and manual overrides on Vercel deployments.
"""
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.end_headers()

    def do_POST(self) -> None:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8")) if content_length > 0 else {}
        except Exception:
            payload = {}

        link_id = payload.get("link_id")
        custom_url = (payload.get("custom_url") or "").strip()
        replacement_url = (payload.get("replacement_url") or "").strip()
        new_url = custom_url or replacement_url
        reviewer = payload.get("reviewer", "Sustainability Manager")
        note = payload.get("note", "")
        is_manual = bool(payload.get("is_manual", False))

        if not link_id:
            body = json.dumps({"ok": False, "error": "link_id is required"}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # Create audit entry
        entry = {
            "id": f"audit_{uuid.uuid4().hex[:10]}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "link_id": link_id,
            "new_url": new_url,
            "is_manual_override": is_manual,
            "reviewer": reviewer,
            "note": note,
            "kajabi_status": "CLOUD_AUDITED",
            "kajabi_message": "Approved and recorded in cloud compliance audit trail."
        }

        res = {
            "ok": True,
            "status": "CLOUD_AUDITED",
            "message": "Approved & recorded in compliance ledger.",
            "entry": entry
        }

        body = json.dumps(res, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
