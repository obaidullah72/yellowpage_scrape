"""
Load curated Yellow Pages–style categories and US/CA location strings into the database.

Examples::

    python manage.py seed_yellowpages_catalog
    python manage.py seed_yellowpages_catalog --country ca
    python manage.py seed_yellowpages_catalog --only categories
    python manage.py seed_yellowpages_catalog --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.data.category_names import category_names
from core.data.geo_seed_data import iter_ca_geo_strings, iter_us_geo_strings
from core.models import YellowPagesCategory, YellowPagesLocation


def _region_from_geo(geo: str) -> str:
    parts = [p.strip() for p in geo.rsplit(",", 1)]
    if len(parts) == 2:
        return parts[1]
    return ""


class Command(BaseCommand):
    help = "Seed YellowPagesCategory and YellowPagesLocation rows (US + Canada curated catalog)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            choices=("us", "ca", "all"),
            default="all",
            help="Which country locations to seed (default: all).",
        )
        parser.add_argument(
            "--only",
            choices=("categories", "locations", "all"),
            default="all",
            help="Seed only categories, only locations, or both.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print counts without writing to the database.",
        )

    def handle(self, *args, **options):
        country = options["country"]
        only = options["only"]
        dry = options["dry_run"]

        cat_count = loc_count = 0

        if only in ("categories", "all"):
            names = category_names()
            cat_count = len(names)
            if dry:
                self.stdout.write(f"Would upsert {cat_count} categories.")
            else:
                with transaction.atomic():
                    YellowPagesCategory.objects.bulk_create(
                        [YellowPagesCategory(name=n) for n in names],
                        ignore_conflicts=True,
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Category catalog loaded ({cat_count} unique names; existing rows unchanged)."
                    )
                )

        if only in ("locations", "all"):
            locs = []
            if country in ("us", "all"):
                for geo in iter_us_geo_strings():
                    locs.append(
                        YellowPagesLocation(
                            country=YellowPagesLocation.Country.US,
                            geo_search=geo,
                            region_code=_region_from_geo(geo),
                        )
                    )
            if country in ("ca", "all"):
                for geo in iter_ca_geo_strings():
                    locs.append(
                        YellowPagesLocation(
                            country=YellowPagesLocation.Country.CA,
                            geo_search=geo,
                            region_code=_region_from_geo(geo),
                        )
                    )
            loc_count = len(locs)
            if dry:
                self.stdout.write(f"Would upsert {loc_count} locations.")
            else:
                with transaction.atomic():
                    YellowPagesLocation.objects.bulk_create(locs, ignore_conflicts=True)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Location catalog loaded ({loc_count} rows; existing rows unchanged)."
                    )
                )

        if dry and only == "all":
            self.stdout.write(
                self.style.WARNING("Dry run: no database changes. Run without --dry-run to apply.")
            )
