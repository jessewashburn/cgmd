"""Merge composer rows that are the same human split in two.

Why they exist
--------------
`bulk_import` keys composers on `(name, birth, death)` (bulk_import.py:55). The feeds
disagree about dates — Sheerpluck often knows a birth year, IMSLP often doesn't — so one
person lands as two rows and their works are split between them. 65 names on prod.

This also disables duplicate-work detection for those people: `find_duplicate_candidates`
only compares works *within a single composer*, so works parked under two rows for the same
human never appear in the same candidate list.

What is safe to merge, and what is emphatically not
---------------------------------------------------
Only one shape is safe: **exactly two rows, exactly one of which has a birth year.** A
missing birth year is not evidence of a different person.

Two different birth years IS such evidence, and the catalog really contains those:

    anelli, giuseppe   b1787/d1865 (6w) | b1873/d1926 (1w)   <- two different humans
    gibson, john       b1951/d2016 (1w) | b1960     (2w)     <- two different humans

Merging those would fuse two people into one. They are reported for a human, never merged.

A third shape is a data error rather than an identity question:

    beischer-matyo, tamas   b1972/d-  |  b-/d1972

His birth year was parsed into `death_year` on one row. The rows are the same person, but
unioning the fields would record him as born and dead in the same year. Any merge that
produces impossible dates is refused and reported.

Usage
-----
    manage.py merge_duplicate_composers                 # dry run, prints the plan
    manage.py merge_duplicate_composers --report x.csv  # dry run + full CSV for review
    manage.py merge_duplicate_composers --apply         # after reviewing the CSV
"""

import csv
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from music.models import Composer, ComposerAlias, UserSuggestion, Work

# Copied from loser to winner only where the winner's value is empty.
UNION_FIELDS = (
    'first_name', 'last_name', 'birth_year', 'death_year', 'country',
    'country_description', 'biography', 'period', 'imslp_url', 'wikipedia_url',
    'external_id', 'data_source', 'admin_notes',
)

SAFE = 'safe'
CONFLICTING_DATES = 'conflicting_dates'
IMPOSSIBLE_DATES = 'impossible_dates'
TOO_MANY_ROWS = 'too_many_rows'
NO_DATES_EITHER = 'no_dates_either'


def is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def classify(rows):
    """(verdict, winner, losers) for one group of same-named composers."""
    dated = [c for c in rows if c.birth_year is not None]
    undated = [c for c in rows if c.birth_year is None]

    if len(rows) > 2:
        # e.g. diaz, rafael: b- (17w) | b1943 (15w) | b1965 (1w). Which row the undated
        # works belong to is not decidable from the data.
        return TOO_MANY_ROWS, None, []
    if len(dated) > 1:
        birth_years = {c.birth_year for c in dated}
        if len(birth_years) > 1:
            return CONFLICTING_DATES, None, []
        # Same birth year on both — genuinely the same person.
        dated.sort(key=lambda c: (-c.works.count(), c.id))
        return SAFE, dated[0], dated[1:]
    if not dated:
        # Neither has a date; nothing distinguishes them, but nothing identifies them
        # either. Left for a human rather than merged on a name alone.
        return NO_DATES_EITHER, None, []

    winner = dated[0]
    losers = undated
    # Guard the beischer-matyó shape: a union that yields death <= birth is a parse error
    # surfacing, not a merge.
    for loser in losers:
        death = winner.death_year if winner.death_year is not None else loser.death_year
        if death is not None and winner.birth_year is not None and death <= winner.birth_year:
            return IMPOSSIBLE_DATES, None, []
    return SAFE, winner, losers


class Command(BaseCommand):
    help = 'Merge composer rows that are one human split by a missing birth year'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Actually merge. Default is a dry run.')
        parser.add_argument('--report', default='',
                            help='Write every group and its verdict to this CSV')
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **opts):
        apply = opts['apply']

        groups = defaultdict(list)
        dupe_names = (Composer.objects.values('name_normalized')
                      .annotate(n=Count('id')).filter(n__gt=1)
                      .values_list('name_normalized', flat=True))
        for c in Composer.objects.filter(name_normalized__in=list(dupe_names)):
            groups[c.name_normalized].append(c)

        self.stdout.write(f'{len(groups)} duplicated composer names')
        if not apply:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be written'))

        stats = defaultdict(int)
        report_rows = []

        with transaction.atomic():
            for name, rows in sorted(groups.items()):
                rows.sort(key=lambda c: c.id)
                verdict, winner, losers = classify(rows)
                stats[verdict] += 1

                report_rows.append({
                    'name_normalized': name,
                    'verdict': verdict,
                    'rows': ' | '.join(
                        f'{c.id}:b{c.birth_year or "-"}/d{c.death_year or "-"}'
                        f'({c.works.count()}w)' for c in rows),
                    'winner_id': winner.id if winner else '',
                    'loser_ids': ','.join(str(c.id) for c in losers),
                })

                if verdict != SAFE:
                    if opts['verbose']:
                        self.stdout.write(f'  skip [{verdict}] {name}')
                    continue

                moved = self._merge(winner, losers, stats)
                if opts['verbose']:
                    self.stdout.write(
                        f'  merge {name}: {[c.id for c in losers]} -> {winner.id} '
                        f'({moved} works moved)')

            if not apply:
                transaction.set_rollback(True)

        if opts['report']:
            with open(opts['report'], 'w', newline='', encoding='utf-8') as fh:
                w = csv.DictWriter(fh, fieldnames=list(report_rows[0]))
                w.writeheader()
                w.writerows(report_rows)
            self.stdout.write(f"report -> {opts['report']}")

        self.stdout.write('')
        for key in (SAFE, CONFLICTING_DATES, IMPOSSIBLE_DATES, TOO_MANY_ROWS,
                    NO_DATES_EITHER, 'works_moved', 'aliases_moved',
                    'suggestions_repointed', 'fields_filled', 'composers_deleted'):
            self.stdout.write(f'  {key:<24} {stats[key]:>5}')
        self.stdout.write(self.style.SUCCESS(
            '\ndry run complete (rolled back)' if not apply else '\nmerge complete'))

    def _merge(self, winner, losers, stats):
        moved_total = 0
        for loser in losers:
            # Works MUST move before the delete: Work.composer is CASCADE, so deleting a
            # loser with works still attached deletes the works.
            moved = Work.objects.filter(composer=loser).update(composer=winner)
            moved_total += moved
            stats['works_moved'] += moved

            # SET_NULL would silently detach a pending suggestion from its composer.
            stats['suggestions_repointed'] += UserSuggestion.objects.filter(
                related_composer=loser).update(related_composer=winner)

            existing = set(winner.aliases.values_list('alias_name', flat=True))
            for alias in loser.aliases.all():
                if alias.alias_name not in existing:
                    ComposerAlias.objects.create(
                        composer=winner, alias_name=alias.alias_name,
                        alias_type=alias.alias_type)
                    stats['aliases_moved'] += 1

            for field in UNION_FIELDS:
                if is_empty(getattr(winner, field)) and not is_empty(getattr(loser, field)):
                    setattr(winner, field, getattr(loser, field))
                    stats['fields_filled'] += 1

            if winner.is_living is None and loser.is_living is not None:
                winner.is_living = loser.is_living

            loser.delete()
            stats['composers_deleted'] += 1

        # Saving re-runs the ComposerEra post_save signal, so eras follow the merged dates.
        winner.save()
        return moved_total
