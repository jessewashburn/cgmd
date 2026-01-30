"""
Django management command to import Sheerpluck data from CSV file.

Usage:
    python manage.py import_sheerpluck [path/to/csv] [--dry-run]
"""

import csv
import unicodedata
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from music.models import (
    Country, InstrumentationCategory, DataSource,
    Composer, Work
)


class Command(BaseCommand):
    help = 'Import classical guitar music data from Sheerpluck CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            nargs='?',
            type=str,
            default='sheerpluck_data.csv',
            help='Path to the Sheerpluck CSV file'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making database changes'
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip works that already exist (by external_id)'
        )

    def __init__(self):
        super().__init__()
        self.stats = {
            'total_rows': 0,
            'composers_created': 0,
            'composers_updated': 0,
            'works_created': 0,
            'works_skipped': 0,
            'errors': 0,
        }
        self.composer_cache = {}  # Cache to avoid duplicate lookups
        self.country_cache = {}
        self.instrumentation_cache = {}

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        dry_run = options['dry_run']
        skip_existing = options['skip_existing']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        # Get or create Sheerpluck data source
        if not dry_run:
            self.data_source, created = DataSource.objects.get_or_create(
                name='Sheerpluck',
                defaults={
                    'url': 'https://www.sheerpluck.de',
                    'description': 'Sheerpluck classical guitar repertoire database'
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS('Created Sheerpluck data source'))

        # Import data
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                self.stdout.write(f'Reading CSV file: {csv_file}')
                reader = csv.DictReader(f)
                
                # Process in batches for better performance
                batch = []
                batch_size = 100
                
                for row in reader:
                    self.stats['total_rows'] += 1
                    
                    if dry_run:
                        # In dry run, just validate data
                        self._validate_row(row)
                    else:
                        batch.append(row)
                        
                        if len(batch) >= batch_size:
                            self._process_batch(batch, skip_existing)
                            batch = []
                    
                    # Progress indicator
                    if self.stats['total_rows'] % 1000 == 0:
                        self.stdout.write(f"Processed {self.stats['total_rows']} rows...")
                
                # Process remaining rows
                if batch and not dry_run:
                    self._process_batch(batch, skip_existing)

        except FileNotFoundError:
            raise CommandError(f'CSV file not found: {csv_file}')
        except Exception as e:
            raise CommandError(f'Error reading CSV: {str(e)}')

        # Print statistics
        self._print_stats(dry_run)

    def _validate_row(self, row):
        """Validate a CSV row without saving to database"""
        try:
            # Check required fields
            if not row.get('Name'):
                self.stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"Row {row.get('ID')}: Missing composer name"))
            if not row.get('Work'):
                self.stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"Row {row.get('ID')}: Missing work title"))
        except Exception as e:
            self.stats['errors'] += 1
            self.stdout.write(self.style.ERROR(f"Validation error: {str(e)}"))

    def _process_batch(self, batch, skip_existing):
        """Process a batch of rows within a transaction"""
        try:
            with transaction.atomic():
                for row in batch:
                    self._process_row(row, skip_existing)
        except Exception as e:
            self.stats['errors'] += 1
            self.stdout.write(self.style.ERROR(f"Batch processing error: {str(e)}"))

    def _process_row(self, row, skip_existing):
        """Process a single CSV row"""
        try:
            # Extract data
            external_id = row.get('ID', '').strip()
            composer_name = row.get('Name', '').strip()
            birth_year = self._parse_year(row.get('Birth Year'))
            death_year = self._parse_year(row.get('Death Year'))
            country_name = row.get('Country', '').strip()
            work_title = row.get('Work', '').strip()
            instrumentation = row.get('Instrumentation', '').strip()

            # Skip if missing essential data
            if not composer_name or not work_title:
                self.stats['errors'] += 1
                return

            # Check if work already exists
            if skip_existing and external_id:
                if Work.objects.filter(external_id=external_id, data_source=self.data_source).exists():
                    self.stats['works_skipped'] += 1
                    return

            # Get or create country
            country = None
            if country_name:
                country = self._get_or_create_country(country_name)

            # Get or create composer
            composer = self._get_or_create_composer(
                composer_name, birth_year, death_year, country
            )

            # Get or create instrumentation category
            instrumentation_category = None
            if instrumentation:
                instrumentation_category = self._get_or_create_instrumentation(instrumentation)

            # Create work
            work = Work.objects.create(
                composer=composer,
                title=work_title,
                title_normalized=self._normalize_string(work_title),
                instrumentation_category=instrumentation_category,
                instrumentation_detail=instrumentation,
                data_source=self.data_source,
                external_id=external_id,
                needs_review=True,  # Mark for review since it's auto-imported
            )
            self.stats['works_created'] += 1

        except Exception as e:
            self.stats['errors'] += 1
            self.stdout.write(self.style.ERROR(
                f"Error processing row {row.get('ID')}: {str(e)}"
            ))

    def _get_or_create_composer(self, full_name, birth_year, death_year, country):
        """Get or create a composer, with caching"""
        # Create cache key
        cache_key = f"{full_name}_{birth_year}_{death_year}"
        
        if cache_key in self.composer_cache:
            return self.composer_cache[cache_key]

        # Parse name into first and last
        name_parts = full_name.split(',', 1)
        if len(name_parts) == 2:
            last_name = name_parts[0].strip()
            first_name = name_parts[1].strip()
        else:
            # Try to split by last space
            name_parts = full_name.rsplit(' ', 1)
            if len(name_parts) == 2:
                first_name = name_parts[0].strip()
                last_name = name_parts[1].strip()
            else:
                last_name = full_name
                first_name = ''

        # Check if composer exists
        composer = Composer.objects.filter(
            full_name=full_name,
            birth_year=birth_year
        ).first()

        if composer:
            # Update if needed
            updated = False
            if not composer.death_year and death_year:
                composer.death_year = death_year
                updated = True
            if not composer.country and country:
                composer.country = country
                updated = True
            if updated:
                composer.save()
                self.stats['composers_updated'] += 1
        else:
            # Create new composer
            composer = Composer.objects.create(
                full_name=full_name,
                first_name=first_name,
                last_name=last_name,
                name_normalized=self._normalize_string(full_name),
                birth_year=birth_year,
                death_year=death_year,
                is_living=(death_year is None and birth_year and birth_year > 1900),
                country=country,
                data_source=self.data_source,
                needs_review=True,
            )
            self.stats['composers_created'] += 1

        # Cache the composer
        self.composer_cache[cache_key] = composer
        return composer

    def _get_or_create_country(self, country_name):
        """Get or create a country, with caching"""
        if country_name in self.country_cache:
            return self.country_cache[country_name]

        country, created = Country.objects.get_or_create(
            name=country_name
        )
        self.country_cache[country_name] = country
        return country

    def _get_or_create_instrumentation(self, instrumentation_name):
        """Get or create an instrumentation category, with caching"""
        if instrumentation_name in self.instrumentation_cache:
            return self.instrumentation_cache[instrumentation_name]

        category, created = InstrumentationCategory.objects.get_or_create(
            name=instrumentation_name
        )
        self.instrumentation_cache[instrumentation_name] = category
        return category

    def _parse_year(self, year_str):
        """Parse year string to integer"""
        if not year_str or not year_str.strip():
            return None
        try:
            return int(year_str.strip())
        except (ValueError, AttributeError):
            return None

    def _normalize_string(self, text):
        """Normalize string for search (lowercase, remove accents)"""
        if not text:
            return ''
        # Remove accents
        nfkd = unicodedata.normalize('NFKD', text)
        ascii_text = nfkd.encode('ASCII', 'ignore').decode('UTF-8')
        return ascii_text.lower()

    def _print_stats(self, dry_run):
        """Print import statistics"""
        self.stdout.write('\n' + '=' * 50)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETE'))
        else:
            self.stdout.write(self.style.SUCCESS('IMPORT COMPLETE'))
        self.stdout.write('=' * 50)
        self.stdout.write(f"Total rows processed: {self.stats['total_rows']}")
        self.stdout.write(f"Composers created: {self.stats['composers_created']}")
        self.stdout.write(f"Composers updated: {self.stats['composers_updated']}")
        self.stdout.write(f"Works created: {self.stats['works_created']}")
        self.stdout.write(f"Works skipped: {self.stats['works_skipped']}")
        if self.stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {self.stats['errors']}"))
        self.stdout.write('=' * 50)
