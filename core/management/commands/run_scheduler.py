import time

from django.core.management.base import BaseCommand

from core.tasks import start_scheduler, stop_scheduler


class Command(BaseCommand):
    help = "Run the LeadHarvester APScheduler loop."

    def handle(self, *args, **options):
        scheduler = start_scheduler()
        self.stdout.write(self.style.SUCCESS("LeadHarvester scheduler is running. Press Ctrl+C to stop."))
        try:
            while scheduler.running:
                time.sleep(5)
        except KeyboardInterrupt:
            stop_scheduler()
            self.stdout.write(self.style.WARNING("LeadHarvester scheduler stopped."))
