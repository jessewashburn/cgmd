"""
Derive and store era tags for every composer.

Usage:
    python manage.py backfill_composer_eras [--dry-run] [--verbose]
                                            [--infer-undated] [--batch-size N]

Re-running is a no-op: `sync_composer_eras` rewrites each composer's date-derived
rows to match its dates, so the command is safe to run after any import, or after
tuning the windows in music/eras.py.

Run this *after* a deploy is healthy, never from a migration — see
0014_composer_eras.py for why.

--infer-undated
    About 22% of composers have no birth year, no death year, and no living flag,
    and so get no era from arithmetic. Their only remaining signal is which source
    they came from: Sheerpluck is a contemporary classical-guitar repertoire site,
    so an undated composer from it is near-certainly recent. This flag tags those
    composers modern + 21st-century with basis='source'.

    It is a guess, applied to thousands of rows, so it's opt-in rather than default.
    It is also fully reversible and auditable:
        ComposerEra.objects.filter(basis='source').delete()
    IMSLP (public-domain scores, any era) carries no such implication and is never
    inferred from.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from music.eras import ERA_WINDOWS, eras_for_composer
from music.models import Composer, ComposerEra, sync_composer_eras

# Sources whose undated composers can be inferred, and what to infer. A source only
# belongs here if its editorial scope implies an era on its own.
SOURCE_INFERRED_ERAS = {
    'Sheerpluck': ['modern', '21st-century'],
}


class Command(BaseCommand):
    help = 'Derive era tags for all composers from their birth/death years'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would change without writing.')
        parser.add_argument('--verbose', action='store_true',
                            help='Print every composer whose eras change.')
        parser.add_argument('--infer-undated', action='store_true',
                            help="Infer eras for undated composers from their data "
                                 "source (see module docstring). Writes basis='source'.")
        parser.add_argument('--batch-size', type=int, default=1000,
                            help='Composers per slice (default 1000).')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        batch_size = options['batch_size']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no writes.\n'))

        stats = self._backfill_from_dates(dry_run, verbose, batch_size)

        if options['infer_undated']:
            stats['inferred'] = self._infer_undated(dry_run, verbose, batch_size)

        self._report(stats, dry_run)

    def _backfill_from_dates(self, dry_run, verbose, batch_size):
        stats = {'seen': 0, 'changed': 0, 'untagged': 0, 'per_era': {}}

        # order_by('pk') is mandatory for sliced iteration: without a total order,
        # Postgres may return overlapping/short slices and rows get skipped
        # (see CLAUDE.md and 0012_backfill_title_sort_key).
        queryset = Composer.objects.order_by('pk')

        for composer in queryset.iterator(chunk_size=batch_size):
            stats['seen'] += 1

            if dry_run:
                desired = set(eras_for_composer(
                    composer.birth_year, composer.death_year, bool(composer.is_living)
                ))
                current = set(
                    composer.eras.filter(basis='dates').values_list('era', flat=True)
                )
                if desired != current:
                    stats['changed'] += 1
                    if verbose:
                        self.stdout.write(
                            f"  {composer.full_name} "
                            f"({composer.birth_year or '?'}-{composer.death_year or '?'}): "
                            f"{', '.join(sorted(current)) or 'no eras'}"
                            f" -> {', '.join(sorted(desired)) or 'no eras'}"
                        )
            else:
                with transaction.atomic():
                    desired = sync_composer_eras(composer)
                if verbose:
                    self.stdout.write(
                        f"  {composer.full_name}: "
                        f"{', '.join(sorted(desired)) or 'no eras'}"
                    )

            if not desired:
                stats['untagged'] += 1
            for era in desired:
                stats['per_era'][era] = stats['per_era'].get(era, 0) + 1

        return stats

    def _infer_undated(self, dry_run, verbose, batch_size):
        """Tag undated composers from sources whose scope implies an era."""
        inferred = 0

        for source_name, era_slugs in SOURCE_INFERRED_ERAS.items():
            undated = (
                Composer.objects
                .filter(
                    birth_year__isnull=True,
                    death_year__isnull=True,
                    data_source__name=source_name,
                )
                # Never overwrite a composer who already has eras from any other
                # basis — this only fills genuine blanks.
                .exclude(eras__isnull=False)
                .order_by('pk')
            )

            for composer in undated.iterator(chunk_size=batch_size):
                if not dry_run:
                    with transaction.atomic():
                        ComposerEra.objects.bulk_create(
                            [
                                ComposerEra(composer=composer, era=slug, basis='source')
                                for slug in era_slugs
                            ],
                            ignore_conflicts=True,
                        )
                inferred += 1
                if verbose:
                    self.stdout.write(
                        f"  [{source_name}] {composer.full_name}: "
                        f"{', '.join(era_slugs)} (inferred)"
                    )

        return inferred

    def _report(self, stats, dry_run):
        self.stdout.write('')
        self.stdout.write(f"Composers processed: {stats['seen']:,}")
        self.stdout.write(f"Untagged (no dates): {stats['untagged']:,}")
        if dry_run:
            self.stdout.write(f"Would change:        {stats['changed']:,}")
        if 'inferred' in stats:
            self.stdout.write(
                f"Inferred from source: {stats['inferred']:,} composers"
                f"{' (would be)' if dry_run else ''}"
            )

        self.stdout.write('\nComposers per era (from dates):')
        for slug, label, _, _ in ERA_WINDOWS:
            self.stdout.write(f"  {label:<14} {stats['per_era'].get(slug, 0):>7,}")

        self.stdout.write(
            self.style.SUCCESS('\nDry run complete — nothing written.' if dry_run
                               else '\nEra backfill complete.')
        )
