import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django_apscheduler.jobstores import DjangoJobStore, register_events

from .scraper import run_due_notifiers

logger = logging.getLogger(__name__)
_scheduler = None


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_jobstore(DjangoJobStore(), "default")
    scheduler.add_job(
        run_due_notifiers,
        trigger=IntervalTrigger(minutes=30),
        id="run_due_yellowpages_notifiers",
        max_instances=1,
        replace_existing=True,
    )
    register_events(scheduler)
    scheduler.start()
    _scheduler = scheduler
    logger.info("LeadHarvester scheduler started")
    return scheduler


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("LeadHarvester scheduler stopped")
    _scheduler = None
