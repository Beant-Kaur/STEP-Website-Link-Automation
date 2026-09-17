import json
from datetime import datetime
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import config
from database.models import DatabaseRepository
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.decision_engine import DecisionEngine
from ai import load_provider_from_config


class ScheduledPipeline:
    def __init__(self, repository: DatabaseRepository) -> None:
        self.repository = repository
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self._apply_schedule()

    def _build_orchestrator(self) -> PipelineOrchestrator:
        provider = load_provider_from_config(config.to_dict())
        evaluator = provider if hasattr(provider, "evaluate") else None
        return PipelineOrchestrator(self.repository, ai_evaluator=evaluator)

    def run_now(self, html: str, base_url: str = "", jurisdiction: str = "", topic: str = "", step_section: str = "", limit: int = 0) -> str:
        orchestrator = self._build_orchestrator()
        section = step_section or config.pipeline.get("step_section", "")
        return orchestrator.run(
            step_html=html,
            base_url=base_url or config.pipeline.get("base_url", ""),
            jurisdiction=jurisdiction or config.pipeline.get("jurisdiction", ""),
            topic=topic or config.pipeline.get("topic", ""),
            step_section=section,
            limit=limit or config.pipeline.get("limit", 0),
        )

    def _scheduled_job(self) -> None:
        try:
            import requests
            url = config.pipeline.get("base_url", "https://step.mykajabi.com/free-digital-content")
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            html = resp.text
            self.run_now(
                html=html,
                base_url=url,
                step_section=config.pipeline.get("step_section", "ESG Legislative Landscape"),
            )
        except Exception:
            pass

    def _apply_schedule(self) -> None:
        try:
            self.scheduler.remove_all_jobs()
        except Exception:
            pass
        schedule = config.schedule
        if not schedule.get("enabled", False):
            return
        frequency = schedule.get("frequency", "weekly")
        hour = int(schedule.get("hour", 2))
        minute = int(schedule.get("minute", 0))
        day_of_week = schedule.get("day_of_week", "mon")
        if frequency == "daily":
            trigger = CronTrigger(hour=hour, minute=minute)
        elif frequency == "weekly":
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)
        elif frequency == "monthly":
            trigger = CronTrigger(day="1", hour=hour, minute=minute)
        else:
            trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(self._scheduled_job, trigger, id="step_esg_scheduled_run", replace_existing=True)

    def update_schedule(self, schedule_cfg: dict[str, Any]) -> None:
        config.save({"schedule": schedule_cfg})
        self._apply_schedule()

    def shutdown(self) -> None:
        try:
            self.scheduler.shutdown(wait=False)
        except Exception:
            pass
