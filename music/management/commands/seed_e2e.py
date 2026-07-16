"""
Seed a small, deterministic dataset for Playwright E2E tests.

Safe by design: refuses to run against a database that already holds a large
number of works (i.e. real data) unless --force is passed.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from music.models import (
    Country, InstrumentationCategory, DataSource, Composer, Work,
)
from music.utils import CANONICAL_INSTRUMENTATION_CATEGORIES

# Instrumentation categories to seed. These must be canonical names — see the
# guard in handle() for why.
SEED_INSTRUMENTATIONS = ('Solo', 'Duo')

COMPOSERS = [
    # full_name, last_name, first_name, country, birth_year, period
    ('Francisco Tárrega', 'Tárrega', 'Francisco', 'Spain', 1852, 'Romantic'),
    ('Fernando Sor', 'Sor', 'Fernando', 'Spain', 1778, 'Classical'),
    ('Mauro Giuliani', 'Giuliani', 'Mauro', 'Italy', 1781, 'Classical'),
    ('Heitor Villa-Lobos', 'Villa-Lobos', 'Heitor', 'Brazil', 1887, 'Modern'),
    ('Agustín Barrios', 'Barrios', 'Agustín', 'Paraguay', 1885, 'Modern'),
]

NAMED_WORKS = [
    ('Recuerdos de la Alhambra', 'Francisco Tárrega'),
    ('Capricho Árabe', 'Francisco Tárrega'),
    ('Gran Vals', 'Francisco Tárrega'),
    ('Estudio No. 1', 'Fernando Sor'),
    ('Variations on a Theme by Mozart', 'Fernando Sor'),
    ('Grande Ouverture', 'Mauro Giuliani'),
    ('Bachianas Brasileiras No. 5', 'Heitor Villa-Lobos'),
    ('La Catedral', 'Agustín Barrios'),
]


class Command(BaseCommand):
    help = 'Seed a small deterministic dataset for E2E tests.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Seed even if the DB already has many works.')

    @transaction.atomic
    def handle(self, *args, **options):
        # The /instrumentations/ list endpoint curates against
        # CANONICAL_INSTRUMENTATION_CATEGORIES (name__in=...), so a category named
        # anything else is served as an empty list — the filter dropdown then renders
        # with no options and the only symptom is a Playwright click timing out on a
        # missing option. Fail loudly here instead. (Seeding 'Guitar solo'/'Guitar duo'
        # is exactly how that happened.) Checked before the reset below so a bad
        # vocabulary never costs the existing data.
        off_vocabulary = set(SEED_INSTRUMENTATIONS) - set(CANONICAL_INSTRUMENTATION_CATEGORIES)
        if off_vocabulary:
            raise CommandError(
                f'Seed instrumentation names not in CANONICAL_INSTRUMENTATION_CATEGORIES: '
                f'{sorted(off_vocabulary)}. The /instrumentations/ endpoint would serve an '
                f'empty list and the filter dropdown would have no options.'
            )

        if Work.objects.count() > 1000 and not options['force']:
            self.stderr.write(self.style.ERROR(
                'Refusing to seed: database has >1000 works (looks like real data). '
                'Use --force to override.'
            ))
            return

        # Reset (safe on a throwaway E2E DB)
        Work.objects.all().delete()
        Composer.objects.all().delete()
        InstrumentationCategory.objects.all().delete()
        Country.objects.all().delete()

        source, _ = DataSource.objects.get_or_create(name='E2E Seed')
        solo, duo = (
            InstrumentationCategory.objects.create(name=name)
            for name in SEED_INSTRUMENTATIONS
        )

        countries: dict[str, Country] = {}
        composers: dict[str, Composer] = {}
        for full, last, first, country_name, birth, period in COMPOSERS:
            country = countries.get(country_name)
            if country is None:
                country = Country.objects.create(name=country_name)
                countries[country_name] = country
            composers[full] = Composer.objects.create(
                full_name=full, last_name=last, first_name=first,
                country=country, birth_year=birth, period=period, data_source=source,
            )

        # title_sort_key is maintained by Work.save() (via generate_title_sort_key).
        for title, composer_name in NAMED_WORKS:
            Work.objects.create(
                title=title,
                composer=composers[composer_name], instrumentation_category=solo,
                is_public=True, data_source=source,
            )

        # Filler so there are 3 pages at page_size=50 (128 works total).
        composer_list = list(composers.values())
        for i in range(1, 121):
            title = f'Etude No. {i:03d}'
            Work.objects.create(
                title=title,
                composer=composer_list[i % len(composer_list)],
                instrumentation_category=(solo if i % 2 else duo),
                is_public=True, data_source=source,
            )

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {Composer.objects.count()} composers and {Work.objects.count()} works.'
        ))
