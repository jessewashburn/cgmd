"""Import guitar arrangements from the committed IMSLP index CSV.

Reads `data/imslp_arrangements.csv` (written by `fetch_imslp_arrangement_index`) and does
pure database work: no network, so this is fast, deterministic, offline-testable, and safe
to re-run.

Design notes worth knowing before changing anything here
-------------------------------------------------------
**Identity is `imslp_url`, not the title.** Two reasons. First, the existing IMSLP corpus
stores titles with the composer baked in — `'Canarios (Sanz, Gaspar)'` — so matching a
parsed title against it would miss and create duplicates. Second, one page = one row, so
the page URL *is* the natural key and re-running is idempotent by construction.

**Composer resolution is never fuzzy.** The catalog contains `Bach, Erik`, `Narvaez,
José-Luis`, `Campion, François` and `Clementi, Aldo` — none of whom are the famous
namesake. A fuzzy match would file Bach's Chaconne under Erik Bach. Exact normalized name
only; anything else creates a new composer.

**A page with no linkable guitar arrangement earns no row** (`arrangement_count` == 0).
That is the admission criterion: if we can't point a user at a real arrangement, the work
does not belong in a guitar catalog.

**`arrangement_basis` protects human edits.** Re-running rewrites `derived` rows only and
never touches `suggested`/`manual`.
"""

import csv
import unicodedata

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from music.models import (
    Composer, DataSource, InstrumentationCategory, Work, WorkInstrumentation,
)
from music.utils import generate_title_sort_key

DEFAULT_CSV = 'data/imslp_arrangements.csv'


def normalize(value):
    """The catalog's canonical normalization. Must match byte-for-byte.

    Identical to `Composer.save()`, `Work.save()` and `bulk_import.normalize`. Do not
    "improve" it here in isolation: this is a *match key* against 15,087 existing composer
    rows, so any divergence silently creates duplicates rather than reusing them.

    Note `.encode('ascii', 'ignore')` **drops** characters that NFKD doesn't decompose —
    'ø', 'ß', 'æ' vanish rather than folding. That is lossy and a bit surprising, but it
    is what the existing rows were written with, and matching them is the whole job. Note
    also there is no .strip(); adding one here would break the match for any name stored
    with stray whitespace.
    """
    return (unicodedata.normalize('NFKD', value or '')
            .encode('ascii', 'ignore').decode('utf-8').lower())


class Command(BaseCommand):
    help = 'Import guitar arrangements from data/imslp_arrangements.csv'

    def add_arguments(self, parser):
        parser.add_argument('--csv', default=DEFAULT_CSV)
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would change and write nothing')
        parser.add_argument('--limit', type=int, default=0,
                            help='Process at most N rows (0 = all)')
        parser.add_argument('--offset', type=int, default=0,
                            help='Skip the first N rows — with --limit, this batches')
        parser.add_argument('--composer', default='',
                            help='Only rows whose IMSLP composer name contains this')
        parser.add_argument('--verbose', action='store_true')

    def handle(self, *args, **opts):
        path = opts['csv']
        try:
            with open(path, newline='', encoding='utf-8') as fh:
                rows = list(csv.DictReader(fh))
        except FileNotFoundError:
            raise CommandError(
                f'{path} not found. Run `manage.py fetch_imslp_arrangement_index` first '
                f'(it crawls IMSLP for ~30 min and writes the committed snapshot).')

        if opts['composer']:
            needle = normalize(opts['composer'])
            rows = [r for r in rows if needle in normalize(r['composer_name'])]

        rows = rows[opts['offset']:]
        if opts['limit']:
            rows = rows[:opts['limit']]

        self.stdout.write(f'{len(rows)} candidate rows from {path}')
        if opts['dry_run']:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be written'))

        stats = {
            'composers_created': 0, 'composers_reused': 0,
            'works_created': 0, 'works_updated': 0, 'retagged': 0,
            'rebucketed': 0, 'alternates_added': 0,
            'skipped_no_arrangement': 0, 'skipped_no_category': 0,
        }

        categories = {c.name: c for c in InstrumentationCategory.objects.all()}
        composer_cache = {}

        with transaction.atomic():
            source, _ = DataSource.objects.get_or_create(
                name='IMSLP', defaults={'url': 'https://imslp.org'})

            for row in rows:
                self._handle_row(row, stats, categories, composer_cache, source, opts)

            if opts['dry_run']:
                transaction.set_rollback(True)

        self.stdout.write('')
        for key, value in stats.items():
            self.stdout.write(f'  {key:<26} {value:>6}')
        self.stdout.write(self.style.SUCCESS('\ndry run complete (rolled back)'
                                             if opts['dry_run'] else '\nimport complete'))

    # ------------------------------------------------------------------

    def _handle_row(self, row, stats, categories, composer_cache, source, opts):
        count = row.get('arrangement_count') or '0'
        if not str(count).isdigit() or int(count) < 1:
            # No linkable guitar arrangement -> no row. The admission criterion.
            stats['skipped_no_arrangement'] += 1
            return

        category = categories.get(row['instrumentation_category'])
        if category is None:
            stats['skipped_no_category'] += 1
            return

        composer = self._resolve_composer(row['composer_name'], composer_cache, stats, opts)
        url, title = row['url'], row['work_title']

        existing = Work.objects.filter(imslp_url=url).first()
        if existing is None:
            # Fall back to (composer, normalized title) so a work added by hand before the
            # import isn't duplicated. imslp_url is the primary key for seeded rows.
            existing = Work.objects.filter(
                composer=composer, title_normalized=normalize(title)).first()

        if existing:
            self._update(existing, row, category, url, stats, opts)
            work = existing
        else:
            work = Work(
                composer=composer,
                title=title,
                title_normalized=normalize(title),
                title_sort_key=generate_title_sort_key(title),
                instrumentation_category=category,
                instrumentation_detail=row['source_category'],
                imslp_url=url,
                data_source=source,
                is_arrangement=True,
                arrangement_basis='derived',
                is_public=True,
            )
            work.save()
            stats['works_created'] += 1
            if opts['verbose']:
                self.stdout.write(f'  + {title[:60]} ({composer.full_name})')

        self._sync_alternates(work, row, categories, stats)

    def _update(self, work, row, category, url, stats, opts):
        """Retro-tag (and re-bucket) a work that is already in the catalog."""
        changed = []

        if work.arrangement_basis in ('suggested', 'manual'):
            # A human has ruled on this one. Never overwrite that from a backfill.
            pass
        elif not work.is_arrangement:
            work.is_arrangement = True
            work.arrangement_basis = 'derived'
            stats['retagged'] += 1
            changed.append('is_arrangement')

        # Re-bucket out of 'Other'. The original bulk_import parsed free-text
        # instrumentation and dumped 4,371 IMSLP works into the "we failed" bucket; the
        # arr category tells us the real answer, and we're already touching the row.
        current = work.instrumentation_category.name if work.instrumentation_category else None
        if current in (None, 'Other') and category.name != current:
            work.instrumentation_category = category
            stats['rebucketed'] += 1
            changed.append('instrumentation_category')

        if not work.imslp_url:
            work.imslp_url = url
            changed.append('imslp_url')

        if changed:
            work.save()
            stats['works_updated'] += 1
            if opts['verbose']:
                self.stdout.write(f'  ~ {work.title[:50]} ({", ".join(changed)})')

    def _sync_alternates(self, work, row, categories, stats):
        """Extra realizations: a work with both solo and duo arrangements.

        Rides WorkInstrumentation, which exists for exactly this shape. Never writes an
        alternate that duplicates the primary — that is noise in the facet and a lie in
        the UI.
        """
        names = [n.strip() for n in (row.get('alternate_instrumentations') or '').split('|')]
        for name in filter(None, names):
            category = categories.get(name)
            if category is None or category == work.instrumentation_category:
                continue
            _, created = WorkInstrumentation.objects.get_or_create(
                work=work, category=category,
                defaults={'basis': 'derived',
                          'note': 'IMSLP arrangement category'},
            )
            if created:
                stats['alternates_added'] += 1

    def _resolve_composer(self, imslp_name, cache, stats, opts):
        """Exact normalized match, or create. NEVER fuzzy — see the module docstring."""
        key = normalize(imslp_name)
        if key in cache:
            return cache[key]

        composer = Composer.objects.filter(name_normalized=key).first()
        if composer:
            stats['composers_reused'] += 1
        else:
            # IMSLP writes "Surname, Forename".
            last, _, first = imslp_name.partition(',')
            composer = Composer(
                full_name=imslp_name,
                last_name=last.strip()[:100],
                first_name=(first.strip() or None),
                name_normalized=key,
                needs_review=True,   # dates unknown; flag for a human
            )
            composer.save()
            stats['composers_created'] += 1
            if opts['verbose']:
                self.stdout.write(f'  + composer {imslp_name}')

        cache[key] = composer
        return composer
