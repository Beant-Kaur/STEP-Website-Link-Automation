import argparse
import http.server
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE_DIR))

from config.settings import config
from database.models import DatabaseRepository
from scheduler.service import ScheduledPipeline


class ApiHandler(http.server.SimpleHTTPRequestHandler):
    scheduled_pipeline: Optional[ScheduledPipeline] = None

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
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

    def do_GET(self) -> None:  # noqa: N802
        # Redirect root to dashboard
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/dashboard/")
            self.end_headers()
            return
        if self.path.startswith("/api/config"):
            self._handle_get_config()
            return
        if self.path.startswith("/api/status"):
            self._handle_status()
            return
        if self.path.startswith("/api/history"):
            self._handle_get_history()
            return
        clean_path = self.path.split("?")[0]
        if clean_path in ("/api/report", "/report.json", "/dashboard/report.json"):
            self._handle_get_report()
            return
        if clean_path in ("/report.csv", "/dashboard/report.csv"):
            self._handle_get_file("report.csv", "text/csv; charset=utf-8")
            return
        if clean_path in ("/report.xlsx", "/dashboard/report.xlsx"):
            self._handle_get_file("report.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            return
        return super().do_GET()

    def _handle_get_file(self, filename: str, content_type: str) -> None:
        target = BASE_DIR / filename
        if target.exists():
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f"attachment; filename={filename}")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.startswith("/api/config"):
            self._handle_post_config()
            return
        if self.path.startswith("/api/run"):
            self._handle_run()
            return
        if self.path.startswith("/api/apply"):
            self._handle_apply()
            return
        if self.path.startswith("/api/revert"):
            self._handle_revert()
            return
        self.send_response(404)
        self.end_headers()

    def _handle_get_report(self) -> None:
        report_path = BASE_DIR / "report.json"
        if report_path.exists():
            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
                self._send_json(data)
                return
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=500)
                return
        self.send_response(404)
        self.end_headers()

    def _handle_get_config(self) -> None:
        self._send_json(config.to_dict())

    def _handle_post_config(self) -> None:
        try:
            payload = self._read_json()
            cfg_update: dict[str, Any] = {}
            if "pipeline" in payload:
                cfg_update["pipeline"] = payload["pipeline"]
            if "schedule" in payload:
                cfg_update["schedule"] = payload["schedule"]
            if "ai" in payload:
                cfg_update["ai"] = payload["ai"]
            config.save(cfg_update)
            if ApiHandler.scheduled_pipeline:
                ApiHandler.scheduled_pipeline.update_schedule(config.schedule)
            self._send_json({"ok": True, "config": config.to_dict()})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)

    def _handle_run(self) -> None:
        try:
            import requests as req
            payload = self._read_json() if self.headers.get("Content-Length") else {}
            url = config.pipeline.get("base_url", "https://step.mykajabi.com/free-digital-content")
            html = payload.get("html") or req.get(url, timeout=30).text
            pipeline = ApiHandler.scheduled_pipeline
            if not pipeline:
                repo = DatabaseRepository(str(BASE_DIR / "step_esg_links.db"))
                pipeline = ScheduledPipeline(repo)
                ApiHandler.scheduled_pipeline = pipeline
            run_id = pipeline.run_now(
                html=html,
                base_url=payload.get("base_url", url),
                jurisdiction=payload.get("jurisdiction", config.pipeline.get("jurisdiction", "")),
                topic=payload.get("topic", config.pipeline.get("topic", "")),
                step_section=payload.get("step_section", config.pipeline.get("step_section", "ESG Legislative Landscape")),
                limit=int(payload.get("limit", 0) or 0),
            )
            # Sync report.json and report.csv
            from reporting import CsvReport, JsonReport
            repo = pipeline.repository
            records = repo.get_all_links()
            if run_id:
                records = [r for r in records if r.link_id.startswith(run_id)]
            JsonReport.generate(records, str(BASE_DIR / "report.json"))
            CsvReport.generate(records, str(BASE_DIR / "report.csv"))
            self._send_json({"ok": True, "run_id": run_id})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _handle_status(self) -> None:
        try:
            from database.models import DatabaseRepository
            repo = DatabaseRepository(str(BASE_DIR / "step_esg_links.db"))
            rows = repo.get_all_links()
            total = len(rows)
            classifications = {}
            for row in rows:
                classifications[row.classification] = classifications.get(row.classification, 0) + 1
            self._send_json({
                "ok": True,
                "total": total,
                "classifications": classifications,
                "schedule": config.schedule,
            })
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _handle_apply(self) -> None:
        try:
            payload = self._read_json()
            link_id = payload.get("link_id")
            reviewer = payload.get("reviewer", "ESG Analyst")
            if not link_id:
                self._send_json({"ok": False, "error": "link_id is required"}, status=400)
                return

            repo = DatabaseRepository(str(BASE_DIR / "step_esg_links.db"))
            link = repo.get_link(link_id)
            if not link:
                self._send_json({"ok": False, "error": "Link not found"}, status=404)
                return

            # Safety rule: Replacement URL must exist and have been verified
            if not link.replacement_url or not link.replacement_verified:
                self._send_json({
                    "ok": False,
                    "error": "Safety rule violation: Replacement link must be verified before applying."
                }, status=400)
                return

            result = repo.apply_replacement(link_id, reviewer=reviewer)
            if not result:
                self._send_json({"ok": False, "error": "Failed to apply replacement"}, status=500)
                return

            self._sync_reports(repo)
            self._send_json({"ok": True, "result": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _handle_revert(self) -> None:
        try:
            payload = self._read_json()
            link_id = payload.get("link_id")
            reviewer = payload.get("reviewer", "ESG Analyst")
            if not link_id:
                self._send_json({"ok": False, "error": "link_id is required"}, status=400)
                return

            repo = DatabaseRepository(str(BASE_DIR / "step_esg_links.db"))
            result = repo.revert_replacement(link_id, reviewer=reviewer)
            if not result:
                self._send_json({"ok": False, "error": "Failed to revert link"}, status=500)
                return

            self._sync_reports(repo)
            self._send_json({"ok": True, "result": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _handle_get_history(self) -> None:
        try:
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            link_id = query.get("link_id", [""])[0]
            if not link_id:
                self._send_json({"ok": False, "error": "link_id is required"}, status=400)
                return
            repo = DatabaseRepository(str(BASE_DIR / "step_esg_links.db"))
            history = repo.get_audit_history(link_id)
            self._send_json({"ok": True, "history": history})
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def _sync_reports(self, repo: DatabaseRepository) -> None:
        try:
            from reporting import CsvReport, JsonReport
            records = repo.get_all_links()
            report_path = BASE_DIR / "report.json"
            if report_path.exists():
                try:
                    curr = json.loads(report_path.read_text(encoding="utf-8"))
                    if isinstance(curr, list) and curr:
                        run_id = curr[0].get("run_id")
                        if run_id:
                            matching = [r for r in records if r.link_id.startswith(run_id) or r.run_id == run_id]
                            if matching:
                                records = matching
                except Exception:
                    pass
            JsonReport.generate(records, str(BASE_DIR / "report.json"))
            CsvReport.generate(records, str(BASE_DIR / "report.csv"))
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STEP ESG Link Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--report", default="report.json", help="JSON report path")
    parser.add_argument("--open", action="store_true", help="Open browser automatically")
    args = parser.parse_args(argv)

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"Report not found: {report_path}", file=sys.stderr)
        print("Run the pipeline first: python main.py --kajabi --json report.json", file=sys.stderr)
        return 2

    os.chdir(BASE_DIR)

    repo = DatabaseRepository(str(BASE_DIR / "step_esg_links.db"))
    ApiHandler.scheduled_pipeline = ScheduledPipeline(repo)

    server = http.server.ThreadingHTTPServer(("", args.port), ApiHandler)
    server.daemon_threads = True

    url = f"http://localhost:{args.port}/dashboard/?report={args.report}"
    print(f"Serving dashboard at {url}")
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()
        ApiHandler.scheduled_pipeline.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
