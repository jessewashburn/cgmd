"""
Seed the Baltimore Classical Guitar Society (BCGS) commissioned works.

Idempotently creates any missing composers/works from the BCGS commissions
program (https://www.bcgs.org/commissions/) and attaches a single bespoke
"BCGS Commission" link to each work.

Usage:
    python manage.py seed_bcgs_commissions [--dry-run] [--verbose]

Re-running is a no-op: composers are matched by normalized name, works by
composer + normalized title, and links by (work, url) uniqueness.
"""

import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from music.models import (
    InstrumentationCategory, DataSource, Composer, Work, WorkLink,
)
from music.utils import parse_composer_name

BCGS_URL = "https://www.bcgs.org/commissions/"
BCGS_LINK_LABEL = "BCGS Commission"

# Curated from https://www.bcgs.org/commissions/ (see SDD: bespoke-work-links).
# Fields: composer, birth_year (None if unknown), birth_year_approx, title,
#         instrumentation, composition_year
#
# Composers are written surname-first ("Last, First") to match how the catalogue
# stores them, so each row lands on the exact-match path in
# _get_or_create_composer() rather than the order-independent token fallback.
# Compound surnames keep both parts before the comma ("Bouche Caro, Gabriel").
COMMISSIONS = [
    ("Gainey, Christopher", 1981, True, "Chupacabra", "Guitar Duo", 2006),
    ("Frank, Gabriela Lena", 1972, False, "Inca Dances", "Guitar and String Quartet", 2008),
    ("Cmiel, Matthew", None, False, "I Wasted Time, and Now Doth Time Waste Me", "Solo Guitar", 2009),
    ("Pierce, Christopher William", 1974, False, "Three Pieces for Two Guitars", "Guitar Duo", 2010),
    ("Belkot, John", None, False, "Der duft des winters", "Solo Guitar", 2014),
    ("Bornfield, Joshua", None, False, "Murmurs", "Guitar Quartet", 2014),
    ("Lee, Scott", None, False, "To Build a House", "Solo Guitar", 2014),
    ("Nonemaker, Elizabeth", None, False, "Old Habits, Similar Patterns", "Guitar Duo", 2014),
    ("Chase, Jordan", None, False, "Nevermore", "Solo Guitar", 2018),
    ("Bouche Caro, Gabriel", None, False, "…of unnoticed charm", "Solo Guitar", 2018),
    ("Miller, Edmund Scott", None, False, "Storied", "Guitar Duo", 2018),
    ("Winnie, Samuel", None, False, "Esplanade", "Guitar Trio", 2018),
    ("McFarlane, Ronn", 1953, False, "Night Rose", "Lute and Guitar Duo", 2021),
    ("Chase, Jordan", None, False, "Between Earth and Sky", "Guitar Quartet", 2021),
    ("Pearl, Ronald", None, False, "Together Apart", "Guitar Quartet", 2021),
    ("Sanz Escallón, Antonio", None, False, "City-Fragments", "Three Guitars", 2025),
]


def normalize(text):
    """Lowercase, strip accents to ASCII (matches Composer/Work.save)."""
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()


def name_tokens(text):
    """Order-independent set of name tokens (handles 'Last, First' vs 'First Last'
    and compound surnames like 'Bouche Caro')."""
    cleaned = normalize(text).replace(',', ' ')
    return frozenset(tok for tok in cleaned.split() if tok)


def surname_key(text):
    """The surname a name explicitly commits to, or None if it leaves it ambiguous.

    'Bouche Caro, Gabriel' -> 'bouche caro'. A name with no comma ('Gabriel Bouche
    Caro') returns None: we can't tell where the surname starts, which is exactly
    what name_tokens() is for.
    """
    head, comma, _ = text.partition(',')
    return ' '.join(normalize(head).split()) if comma else None


def title_key(text):
    """Punctuation/whitespace-insensitive title key so 'X / Y' and 'X, and Y' or
    ellipsis variants still match."""
    return ''.join(ch for ch in normalize(text) if ch.isalnum())


class Command(BaseCommand):
    help = 'Seed BCGS commissioned works and attach a "BCGS Commission" link to each'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would change without writing')
        parser.add_argument('--verbose', action='store_true',
                            help='Print a line for every composer/work/link')

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbose = options['verbose']
        self.stats = {
            'composers_created': 0, 'composers_reused': 0,
            'works_created': 0, 'works_reused': 0,
            'links_added': 0, 'links_skipped': 0,
        }

        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - no database changes will be made'))

        # Cache instrumentation categories once for name matching.
        self._categories = list(InstrumentationCategory.objects.all())

        with transaction.atomic():
            source = self._get_source()
            for row in COMMISSIONS:
                self._seed_row(source, *row)
            if self.dry_run:
                transaction.set_rollback(True)

        self._report()

    # -- helpers -----------------------------------------------------------

    def _get_source(self):
        if self.dry_run:
            return DataSource.objects.filter(name='BCGS').first()
        source, _ = DataSource.objects.get_or_create(
            name='BCGS',
            defaults={
                'url': BCGS_URL,
                'description': 'Baltimore Classical Guitar Society commissioning program',
            },
        )
        return source

    def _match_category(self, instrumentation):
        """Best-effort map to an existing InstrumentationCategory (else None)."""
        target = normalize(instrumentation)
        for cat in self._categories:
            if normalize(cat.name) == target:
                return cat
        return None

    def _seed_row(self, source, composer_name, birth_year, birth_year_approx,
                  title, instrumentation, composition_year):
        composer = self._get_or_create_composer(
            composer_name, birth_year, birth_year_approx, source)
        work = self._get_or_create_work(
            composer, title, instrumentation, composition_year, source)
        self._attach_link(work)

    def _get_or_create_composer(self, full_name, birth_year, birth_year_approx, source):
        # Splits "Last, First" on the comma and "First [Middle] Last" on the last
        # space, so COMMISSIONS rows keep the surname intact even when it is
        # compound ("Sanz Escallón, Antonio" -> first "Antonio", last "Sanz Escallón").
        # full_name is stored verbatim; only the parts are derived.
        first_name, last_name, _ = parse_composer_name(full_name)

        # 1) Exact normalized full-name match takes priority.
        composer = Composer.objects.filter(name_normalized=normalize(full_name)).first()
        # 2) Otherwise, order-independent token-set match: the catalogue mixes "First
        #    Last", surname-first "Last, First", and compound surnames ("Bouche Caro,
        #    Gabriel"), all of which share the same set of name tokens.
        if composer is None:
            target = name_tokens(full_name)
            target_surname = surname_key(full_name)
            anchor = max(target, key=len)  # scan on the most distinctive token
            for cand in Composer.objects.filter(name_normalized__icontains=anchor):
                if name_tokens(cand.full_name) != target:
                    continue
                # A token set can't tell "Chase, Jordan" from "Jordan, Chase" — but
                # those are two different people (the latter is Chase Jordan, b. 1998,
                # from Sheerpluck), and each comma names its surname outright. So when
                # both sides commit to a surname and disagree, believe them. Only bridge
                # across word order when one side leaves the surname ambiguous.
                cand_surname = surname_key(cand.full_name)
                if target_surname and cand_surname and target_surname != cand_surname:
                    continue
                composer = cand
                break
        if composer:
            self.stats['composers_reused'] += 1
            # Safe enrichment: fill a missing birth year only; never overwrite one.
            if birth_year and not composer.birth_year and not self.dry_run:
                composer.birth_year = birth_year
                composer.is_living = True
                if birth_year_approx:
                    composer.needs_review = True
                composer.save(update_fields=['birth_year', 'is_living', 'needs_review'])
            if self.verbose:
                self.stdout.write(f'  composer (reuse): {composer.full_name}')
            return composer

        self.stats['composers_created'] += 1
        if self.verbose:
            year = birth_year if birth_year else '?'
            self.stdout.write(self.style.SUCCESS(
                f'  composer (create): {full_name} (b. {year})'))

        normalized = normalize(full_name)
        if self.dry_run:
            # Return an unsaved instance so downstream dry-run logic can proceed.
            return Composer(
                full_name=full_name, first_name=first_name, last_name=last_name,
                name_normalized=normalized, birth_year=birth_year, is_living=True,
            )

        return Composer.objects.create(
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            name_normalized=normalized,
            birth_year=birth_year,
            is_living=True,
            data_source=source,
            # Approximate/uncertain birth years should be reviewed by a human.
            needs_review=birth_year_approx,
        )

    def _get_or_create_work(self, composer, title, instrumentation, composition_year, source):
        title_normalized = normalize(title)

        work = None
        if composer.pk:
            # Punctuation/whitespace-insensitive match against this composer's works,
            # so "X / Y" vs "X, and Y" and ellipsis variants still reuse.
            key = title_key(title)
            for existing in composer.works.all():
                if title_key(existing.title) == key:
                    work = existing
                    break

        if work:
            self.stats['works_reused'] += 1
            if self.verbose:
                self.stdout.write(f'    work (reuse): {work.title}')
            return work

        self.stats['works_created'] += 1
        if self.verbose:
            self.stdout.write(self.style.SUCCESS(
                f'    work (create): {title} ({composition_year})'))

        category = self._match_category(instrumentation)

        if self.dry_run:
            return Work(
                composer=composer if composer.pk else None,
                title=title, title_normalized=title_normalized,
                instrumentation_detail=instrumentation,
                instrumentation_category=category,
                composition_year=composition_year,
            )

        return Work.objects.create(
            composer=composer,
            title=title,
            title_normalized=title_normalized,
            instrumentation_detail=instrumentation,
            instrumentation_category=category,
            composition_year=composition_year,
            data_source=source,
            needs_review=True,
        )

    def _attach_link(self, work):
        if self.dry_run or not work.pk:
            # Can't reliably check existence without a persisted work.
            self.stats['links_added'] += 1
            if self.verbose:
                self.stdout.write(f'      link: {BCGS_LINK_LABEL}')
            return

        _, created = WorkLink.objects.get_or_create(
            work=work,
            url=BCGS_URL,
            defaults={'label': BCGS_LINK_LABEL, 'link_type': 'commission'},
        )
        if created:
            self.stats['links_added'] += 1
        else:
            self.stats['links_skipped'] += 1
        if self.verbose:
            state = 'add' if created else 'skip'
            self.stdout.write(f'      link ({state}): {BCGS_LINK_LABEL}')

    def _report(self):
        s = self.stats
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('BCGS commissions seed summary'))
        self.stdout.write(f"  Composers: {s['composers_created']} created, "
                          f"{s['composers_reused']} reused")
        self.stdout.write(f"  Works:     {s['works_created']} created, "
                          f"{s['works_reused']} reused")
        self.stdout.write(f"  Links:     {s['links_added']} added, "
                          f"{s['links_skipped']} already present")
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - rolled back, nothing written'))
