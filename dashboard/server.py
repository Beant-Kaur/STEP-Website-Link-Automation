"""
STEP ESG Compliance Dashboard Server
Lightweight, robust HTTP server serving the executive dashboard and link updating API.
"""
import argparse
import http.server
import json
import os
import sys
import urllib.parse
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from kajabi.updater import apply_link_update, load_audit_log, is_kajabi_session_available

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Any:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length)
        return json.loads(data.decode("utf-8"))

    def do_GET(self) -> None:
        clean_path = self.path.split("?")[0]

        # Redirect root to dashboard
        if clean_path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/dashboard/")
            self.end_headers()
            return

        # Serve dashboard
        if clean_path in ("/dashboard", "/dashboard/"):
            html_path = BASE_DIR / "dashboard" / "index.html"
            if html_path.exists():
                content = html_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        # Serve report data
        if clean_path in ("/api/report", "/report.json", "/dashboard/report.json"):
            report_file = BASE_DIR / "data" / "report.json"
            if report_file.exists():
                try:
                    data = json.loads(report_file.read_text(encoding="utf-8"))
                    self._send_json(data)
                    return
                except Exception as exc:
                    self._send_json({"ok": False, "error": str(exc)}, status=500)
                    return
            self.send_response(404)
            self.end_headers()
            return

        # Status endpoint
        if clean_path.startswith("/api/status"):
            report_file = BASE_DIR / "data" / "report.json"
            total = 0
            if report_file.exists():
                try:
                    recs = json.loads(report_file.read_text(encoding="utf-8"))
                    total = len(recs)
                except Exception:
                    pass
            self._send_json({
                "ok": True,
                "total_regulations": total,
                "kajabi_authenticated": is_kajabi_session_available()
            })
            return

        # Audit log endpoint
        if clean_path.startswith("/api/audit-log"):
            try:
                self._send_json({"ok": True, "logs": load_audit_log()})
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)
            return

        # Run status endpoint
        if clean_path.startswith("/api/run"):
            self._send_json({"ok": True, "agent_status": "READY", "environment": "local"})
            return

        # Fallback to default file handler
        return super().do_GET()

    def do_POST(self) -> None:
        clean_path = self.path.split("?")[0]

        if clean_path.startswith("/api/run"):
            try:
                from api.run import audit_record, load_report_data
                payload = self._read_json() if self.headers.get("Content-Length") else {}
                jurisdiction = (payload.get("jurisdiction") or "").strip()
                mode = (payload.get("mode") or "quick").strip().lower()
                target_link_id = (payload.get("link_id") or "").strip()

                all_recs = load_report_data()
                targets = []
                if target_link_id:
                    targets = [r for r in all_recs if str(r.get("link_id")) == target_link_id or str(r.get("id")) == target_link_id]
                elif jurisdiction and jurisdiction.lower() not in ("all", "full", ""):
                    targets = [r for r in all_recs if r.get("jurisdiction", "").lower() == jurisdiction.lower()]
                else:
                    targets = all_recs

                all_logs = []
                updated_records = []
                import time
                ts = time.strftime("%H:%M:%S")
                all_logs.append(f"[{ts}] === LOCAL STEP ESG AUDIT AGENT ACTIVATED ===")
                all_logs.append(f"[{ts}] Scope: {jurisdiction or 'Full Platform'} | Mode: {mode.upper()} | Targets: {len(targets)}")

                for rec in targets:
                    up_rec, logs = audit_record(rec, mode=mode)
                    all_logs.extend(logs)
                    updated_records.append(up_rec)

                # Save updated records to data/report.json if changed
                report_file = BASE_DIR / "data" / "report.json"
                if report_file.exists():
                    try:
                        curr = json.loads(report_file.read_text(encoding="utf-8"))
                        id_map = {str(r.get("link_id") or r.get("id")): r for r in updated_records}
                        for r in curr:
                            rid = str(r.get("link_id") or r.get("id"))
                            if rid in id_map:
                                r.update(id_map[rid])
                        report_file.write_text(json.dumps(curr, indent=2, ensure_ascii=False), encoding="utf-8")
                    except Exception:
                        pass

                self._send_json({
                    "ok": True,
                    "jurisdiction": jurisdiction or "All",
                    "mode": mode,
                    "audited_count": len(updated_records),
                    "logs": all_logs,
                    "records": updated_records,
                    "stats": {
                        "total": len(updated_records),
                        "confirmed_latest": sum(1 for r in updated_records if r.get("final_status") == "KEEP"),
                        "replacement_needed": sum(1 for r in updated_records if r.get("final_status") == "RECOMMEND_REPLACEMENT"),
                        "review": sum(1 for r in updated_records if r.get("final_status") == "HUMAN_REVIEW")
                    }
                })
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)
            return

        if clean_path.startswith("/api/apply"):
            try:
                payload = self._read_json()
                link_id = payload.get("link_id")
                custom_url = (payload.get("custom_url") or "").strip()
                replacement_url = (payload.get("replacement_url") or "").strip()
                new_url = custom_url or replacement_url
                reviewer = payload.get("reviewer", "Sustainability Manager")
                note = payload.get("note", "")
                is_manual = bool(payload.get("is_manual", False))
                sync_kajabi = bool(payload.get("sync_kajabi", True))

                if not link_id:
                    self._send_json({"ok": False, "error": "link_id is required"}, status=400)
                    return

                if not new_url:
                    report_file = BASE_DIR / "data" / "report.json"
                    if report_file.exists():
                        recs = json.loads(report_file.read_text(encoding="utf-8"))
                        for r in recs:
                            if str(r.get("link_id")) == str(link_id) or str(r.get("id")) == str(link_id):
                                new_url = r.get("replacement_url")
                                break

                if not new_url:
                    self._send_json({"ok": False, "error": "No replacement URL specified"}, status=400)
                    return

                result = apply_link_update(
                    link_id=link_id,
                    new_url=new_url,
                    reviewer=reviewer,
                    note=note,
                    is_manual=is_manual,
                    sync_to_kajabi=sync_kajabi
                )
                self._send_json(result)
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)
            return

        self.send_response(404)
        self.end_headers()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STEP ESG Link Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
    args = parser.parse_args(argv)

    os.chdir(str(BASE_DIR))

    server = http.server.ThreadingHTTPServer(("", args.port), DashboardHandler)
    server.daemon_threads = True

    url = f"http://localhost:{args.port}/dashboard/"
    print("=" * 60)
    print("  STEP ESG COMPLIANCE DASHBOARD SERVER")
    print("=" * 60)
    print(f"Serving dashboard at: {url}")
    print(f"Kajabi Session active: {is_kajabi_session_available()}")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
