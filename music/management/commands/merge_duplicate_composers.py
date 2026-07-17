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
AMBIGUOUS_UNDATED = 'ambiguous_undated'
NO_DATES_EITHER = 'no_dates_either'
NOTHING_TO_DO = 'nothing_to_do'

# ---------------------------------------------------------------------------
# Researched corrections (--repair only)
#
# These override what the data says, so each one carries its evidence. Anything here is a
# human's judgement, not a rule the code derived — keep it small and cited.
# ---------------------------------------------------------------------------

# name_normalized -> (birth, death, why). Every row under this name is ONE person; unify
# their dates onto these, after which the ordinary same-birth-year merge applies.
CURATED_SAME_PERSON = {
    'llobet, miguel': (
        1878, 1938,
        'Miguel Llobet Soles, b. 18 Oct 1878 Barcelona, d. 22 Feb 1938 Barcelona '
        '(Wikipedia; contemporary obituary). Our two rows share d.1938 and differ only in '
        'birth: IMSLP has 1878 (correct), Sheerpluck 1875 (wrong). 21 works were split.'
    ),
    'marucelli, enrico': (
        1877, 1907,
        'One Florentine mandolinist/composer (Valtzer Fantastico, Capriccio Zingaresco), '
        'not two. His dates are genuinely contested in the literature: most sources say '
        '1877-1907, while Tactus and Presto print 1873-1901 — our two rows ARE those two '
        'opinions. Unified on the better-attested 1877-1907.'
    ),
}

# name_normalized -> (birth_year, why). For groups with several real people plus an
# undated row, where evidence in the WORKS settles which one the undated row belongs to.
CURATED_UNDATED_BELONGS_TO = {
    'diaz, rafael': (
        1943,
        "IMSLP's undated row holds 'Letra B', 'Letra I', 'Letra X' — movements of "
        "'Abecedario para Guitarra' (alphabet for guitar), which sits on the b.1943 "
        "Spaniard's row. Its other works (Flamenco Op.9, Reflexion sobre Pablo Sarasate) "
        "are Spanish too. Not the b.1965 Chilean, who stays separate."
    ),
}


def is_empty(value):
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


# Fields that make a row the better-identified record of a person. Used only to pick the
# winner; the loser's values are unioned in either way, so this decides which id survives,
# not which data does.
IDENTITY_FIELDS = ('country_id', 'data_source_id', 'death_year', 'first_name',
                   'biography', 'external_id')


def completeness(composer):
    return sum(1 for f in IDENTITY_FIELDS if not is_empty(getattr(composer, f)))


def plan(rows):
    """(verdict, [(winner, losers), ...]) for one group of same-named composers.

    A birth year is an identity. So: bucket the rows by birth year, merge *within* each
    bucket, and never across buckets — two different birth years mean two different people
    (anelli, giuseppe: 1787-1865 and 1873-1926 are two humans).

    An undated row has no identity of its own. It can be attached to a dated one only when
    there is exactly one candidate; with several, which person it belongs to is not
    decidable from the data and guessing would misattribute the works.
    """
    buckets = defaultdict(list)
    undated = []
    for c in rows:
        (undated.append(c) if c.birth_year is None else buckets[c.birth_year].append(c))

    if undated:
        if not buckets:
            # Nothing distinguishes them — but nothing identifies them either.
            return NO_DATES_EITHER, []
        if len(buckets) > 1:
            # e.g. diaz, rafael pre-curation: b1943 and b1965 both plausible owners.
            return AMBIGUOUS_UNDATED, []
        buckets[next(iter(buckets))].extend(undated)

    merges = []
    for birth_year, bucket in buckets.items():
        if len(bucket) < 2:
            continue
        # Winner: the row that identifies the person best, then the busiest, then the
        # oldest id. Completeness matters because curation can leave two rows with the
        # same birth year — Diaz's formerly-undated IMSLP row vs the Spaniard's row that
        # carries the country and the source. Both keep their data (the loser's fields are
        # unioned in); this only decides which id survives.
        bucket.sort(key=lambda c: (c.birth_year is None, -completeness(c),
                                   -c.works.count(), c.id))
        winner, losers = bucket[0], bucket[1:]

        # Guard the beischer-matyó shape: a union yielding death <= birth is a parse error
        # surfacing, not a merge to perform.
        for loser in losers:
            death = winner.death_year if winner.death_year is not None else loser.death_year
            if death is not None and death <= birth_year:
                return IMPOSSIBLE_DATES, []
        merges.append((winner, losers))

    if not merges:
        # Every row is its own person: distinct birth years, one row each.
        return (CONFLICTING_DATES if len(buckets) > 1 else NOTHING_TO_DO), []
    return SAFE, merges


class Command(BaseCommand):
    help = 'Merge composer rows that are one human split by a missing birth year'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Actually merge. Default is a dry run.')
        parser.add_argument('--repair', action='store_true',
                            help='Also fix misparsed birth years and apply the researched '
                                 'date corrections, so those groups become mergeable')
        parser.add_argument('--report', default='',
                            help='Write every group and its verdict to this CSV')
        parser.add_argument('--verbose', action='store_true')

    # ------------------------------------------------------------------
    # Repairs (--repair)
    # ------------------------------------------------------------------

    def _repair_misparsed_birth_year(self, rows, stats):
        """Fix a birth year that the importer wrote into death_year.

        The signature is unmistakable and appears three times in prod:

            Sheerpluck: b1959, Japan, is_living=True
            IMSLP:      b-,    d1959, no country

        Same name, same year, and the other row says the person is ALIVE. A living
        composer did not die in the year he was born; the year is a birth year in the
        wrong column. Derived from the data, not from a name I recognised.
        """
        births = {c.birth_year for c in rows if c.birth_year is not None}
        repaired = 0
        for c in rows:
            if c.birth_year is None and c.death_year in births:
                living_elsewhere = any(
                    o.is_living and o.birth_year == c.death_year for o in rows if o.id != c.id)
                if not living_elsewhere:
                    continue
                c.birth_year, c.death_year = c.death_year, None
                c.is_living = True
                c.save(update_fields=['birth_year', 'death_year', 'is_living', 'updated_at'])
                stats['misparsed_birth_years_fixed'] += 1
                repaired += 1
        return repaired

    def _apply_curated(self, name, rows, stats):
        """Apply a researched correction. See the tables at the top of this module."""
        if name in CURATED_SAME_PERSON:
            birth, death, _why = CURATED_SAME_PERSON[name]
            for c in rows:
                if c.birth_year != birth or c.death_year != death:
                    c.birth_year, c.death_year = birth, death
                    c.save(update_fields=['birth_year', 'death_year', 'updated_at'])
                    stats['curated_dates_applied'] += 1
            return True

        if name in CURATED_UNDATED_BELONGS_TO:
            birth, _why = CURATED_UNDATED_BELONGS_TO[name]
            if not any(c.birth_year == birth for c in rows):
                return False   # the anchor row is gone; do nothing rather than invent one
            for c in rows:
                if c.birth_year is None:
                    c.birth_year = birth
                    c.save(update_fields=['birth_year', 'updated_at'])
                    stats['curated_dates_applied'] += 1
            return True
        return False

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
                before = ' | '.join(
                    f'{c.id}:b{c.birth_year or "-"}/d{c.death_year or "-"}'
                    f'({c.works.count()}w)' for c in rows)

                repaired = ''
                if opts['repair']:
                    if self._repair_misparsed_birth_year(rows, stats):
                        repaired = 'misparsed_birth_year'
                    if self._apply_curated(name, rows, stats):
                        repaired = (repaired + '+curated').lstrip('+')

                verdict, merges = plan(rows)
                stats[verdict] += 1

                report_rows.append({
                    'name_normalized': name,
                    'verdict': verdict,
                    'repaired': repaired,
                    'rows': before,
                    'merges': ' ; '.join(
                        f'{w.id}<-{[l.id for l in ls]}' for w, ls in merges),
                })

                if verdict != SAFE:
                    if opts['verbose']:
                        self.stdout.write(f'  skip [{verdict}] {name}')
                    continue

                for winner, losers in merges:
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
        for key in (SAFE, CONFLICTING_DATES, IMPOSSIBLE_DATES, AMBIGUOUS_UNDATED,
                    NO_DATES_EITHER, NOTHING_TO_DO,
                    'misparsed_birth_years_fixed', 'curated_dates_applied',
                    'works_moved', 'aliases_moved', 'suggestions_repointed',
                    'fields_filled', 'composers_deleted'):
            self.stdout.write(f'  {key:<28} {stats[key]:>5}')
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
