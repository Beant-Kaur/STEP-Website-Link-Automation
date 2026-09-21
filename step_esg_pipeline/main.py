import argparse
import os
import sys
from pathlib import Path

from database.models import DatabaseRepository
from pipeline.decision_engine import DecisionEngine
from pipeline.orchestrator import PipelineOrchestrator
from reporting import CsvReport, JsonReport, ExcelReport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="STEP ESG Link Monitoring Pipeline")
    parser.add_argument("--html", help="Path to STEP HTML file")
    parser.add_argument("--url", help="STEP page URL to crawl")
    parser.add_argument("--sample", action="store_true", help="Use bundled sample STEP HTML for demo")
    parser.add_argument("--kajabi", action="store_true", help="Target STEP Kajabi ESG Legislative Landscape section specifically")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of links to process (0 = all)")
    parser.add_argument("--base-url", default="", help="Base URL for relative links")
    parser.add_argument("--jurisdiction", default="", help="Jurisdiction label")
    parser.add_argument("--topic", default="", help="Topic label")
    parser.add_argument("--step-section", default="", help="STEP section name")
    parser.add_argument("--db", default=os.getenv("STEP_DB_PATH", "step_esg_links.db"), help="Database path")
    parser.add_argument("--csv", help="Output CSV report path")
    parser.add_argument("--json", help="Output JSON report path")
    parser.add_argument("--xlsx", help="Output Excel (.xlsx) report path")
    args = parser.parse_args(argv)

    html = ""
    base_url = args.base_url or args.url or "https://step.mykajabi.com"
    if args.sample:
        sample_path = Path(__file__).with_name("samples") / "step_sample.html"
        html = sample_path.read_text(encoding="utf-8")
    elif args.html:
        html = Path(args.html).read_text(encoding="utf-8")
    elif args.url or args.kajabi:
        import requests
        url = args.url or "https://step.mykajabi.com/free-digital-content"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        html = resp.text
        base_url = url
    else:
        print("Provide --html, --url, --kajabi, or --sample", file=sys.stderr)
        return 2

    repository = DatabaseRepository(args.db)
    from config.settings import config
    from ai.evaluator import load_provider_from_config
    ai_provider = load_provider_from_config(config.to_dict())
    orchestrator = PipelineOrchestrator(repository, ai_evaluator=ai_provider)
    section = args.step_section or ("ESG Legislative Landscape" if args.kajabi else args.step_section)
    run_id = orchestrator.run(
        step_html=html,
        base_url=base_url,
        jurisdiction=args.jurisdiction,
        topic=args.topic,
        step_section=section,
        limit=args.limit,
    )
    print(f"Run ID: {run_id}")

    records = repository.get_all_links()
    if run_id:
        records = [r for r in records if r.link_id.startswith(run_id)]
    if args.csv:
        CsvReport.generate(records, args.csv)
        print(f"CSV report written to {args.csv}")
    if args.json:
        JsonReport.generate(records, args.json)
        print(f"JSON report written to {args.json}")
    if args.xlsx:
        ExcelReport.generate(records, args.xlsx)
        print(f"Excel report written to {args.xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
