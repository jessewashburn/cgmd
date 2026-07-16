"""Derive alternate instrumentations from the "(or ...)" text our sources already write.

Idempotent: re-running changes nothing. Only touches rows with basis='derived' — a
user suggestion or an admin's manual call survives every re-run.

Usage:
    python manage.py backfill_alternate_instrumentations [--dry-run] [--verbose] [--limit N]

Measured over the catalogue (73,112 works with detail text): 1,833 carry an
alternate, of which ~665 resolve to a genuinely different bucket and earn a row. The
other ~1,168 are trivial substitutions landing in the primary's own bucket and are
deliberately skipped — see `utils.alternate_instrumentation_names`.

See SDD: alternate-work-instrumentations.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from music.models import InstrumentationCategory, Work, WorkInstrumentation
from music.utils import alternate_instrumentation_names

BATCH_SIZE = 500


class Command(BaseCommand):
    help = 'Derive Work alternate instrumentations from "(or ...)" detail text'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would change without writing')
        parser.add_argument('--verbose', action='store_true',
                            help='Print a line for every work that gains an alternate')
        parser.add_argument('--limit', type=int, default=None,
                            help='Only consider the first N works (for a quick look)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        limit = options['limit']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no database changes will be made'))

        # .order_by('pk') is required, not cosmetic: CLAUDE.md — unordered slices skip
        # rows, and titles are not unique so any other key is unstable.
        qs = (Work.objects
              .exclude(instrumentation_detail='')
              .exclude(instrumentation_detail__isnull=True)
              .only('id', 'instrumentation_detail', 'instrumentation_category_id')
              .order_by('pk'))
        if limit:
            qs = qs[:limit]

        # Categories are a closed 33-item vocabulary; cache them rather than
        # get_or_create-ing per row across ~73k works.
        cache = {c.name: c for c in InstrumentationCategory.objects.all()}

        scanned = with_alt = rows_added = rows_removed = 0
        pairs = {}

        for work in qs.iterator(chunk_size=BATCH_SIZE):
            scanned += 1
            names = alternate_instrumentation_names(work.instrumentation_detail)
            if not names:
                continue
            with_alt += 1

            existing = {
                wi.category.name: wi
                for wi in WorkInstrumentation.objects.filter(work=work).select_related('category')
            }
            # Never overwrite a human's row, and never re-add one they removed.
            human_owned = {n for n, wi in existing.items() if wi.basis != 'derived'}
            wanted = [n for n in names if n not in human_owned]

            stale = [wi for n, wi in existing.items()
                     if wi.basis == 'derived' and n not in wanted]
            new = [n for n in wanted if n not in existing]

            if verbose and (new or stale):
                primary = work.instrumentation_category_id and work.instrumentation_category.name
                self.stdout.write(
                    f'  {work.id} {work.title[:44]!r}\n'
                    f'      {work.instrumentation_detail[:70]!r}\n'
                    f'      primary={primary} + {new}'
                    + (f'  (dropping stale {[wi.category.name for wi in stale]})' if stale else '')
                )

            for name in new:
                pairs[name] = pairs.get(name, 0) + 1

            if dry_run:
                rows_added += len(new)
                rows_removed += len(stale)
                continue

            with transaction.atomic():
                for wi in stale:
                    wi.delete()
                    rows_removed += 1
                for name in new:
                    category = cache.get(name)
                    if category is None:
                        category, _ = InstrumentationCategory.objects.get_or_create(name=name)
                        cache[name] = category
                    _, created = WorkInstrumentation.objects.get_or_create(
                        work=work, category=category, defaults={'basis': 'derived'})
                    if created:
                        rows_added += 1

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Alternate instrumentation backfill'))
        self.stdout.write(f'  Works scanned ............ {scanned}')
        self.stdout.write(f'  With a usable alternate .. {with_alt}')
        self.stdout.write(f'  Rows added ............... {rows_added}')
        self.stdout.write(f'  Stale derived removed .... {rows_removed}')
        if pairs:
            self.stdout.write('  Most common alternates:')
            for name, count in sorted(pairs.items(), key=lambda kv: -kv[1])[:10]:
                self.stdout.write(f'    {count:5}  {name}')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - nothing written'))
