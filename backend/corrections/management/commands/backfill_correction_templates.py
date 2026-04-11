"""
Backfill template_id / template_version_id on existing ExtractionCorrection rows
by looking up the linked ExtractionResult.

Usage:
    python manage.py backfill_correction_templates
    python manage.py backfill_correction_templates --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from corrections.models import ExtractionCorrection
from extractions.models import ExtractionResult


class Command(BaseCommand):
    help = "Backfill template_id/template_version_id on ExtractionCorrection from linked ExtractionResult."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Find corrections missing template linkage but having extraction_result_id
        qs = ExtractionCorrection.objects.filter(
            template_id__isnull=True,
            extraction_result_id__isnull=False,
        )
        total = qs.count()
        self.stdout.write(
            self.style.NOTICE(f"Found {total} corrections with null template_id")
        )

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nothing to backfill."))
            return

        # Collect target extraction_result_ids and fetch in one query
        er_ids = set(qs.values_list("extraction_result_id", flat=True))
        er_map = {
            er.id: (er.template_id, er.template_version_id)
            for er in ExtractionResult.objects.filter(id__in=er_ids).only(
                "id", "template_id", "template_version_id"
            )
        }

        updated = 0
        skipped = 0
        with transaction.atomic():
            for correction in qs.iterator():
                mapping = er_map.get(correction.extraction_result_id)
                if not mapping:
                    skipped += 1
                    continue
                template_id, template_version_id = mapping
                if not template_id:
                    skipped += 1
                    continue

                correction.template_id = template_id
                correction.template_version_id = template_version_id

                if dry_run:
                    self.stdout.write(
                        f"  would update correction {correction.id}: "
                        f"template_id={template_id}, template_version_id={template_version_id}"
                    )
                else:
                    correction.save(
                        update_fields=["template_id", "template_version_id"]
                    )
                updated += 1

            if dry_run:
                transaction.set_rollback(True)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: {updated} rows would be updated, {skipped} skipped."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backfill complete: {updated} updated, {skipped} skipped."
                )
            )
