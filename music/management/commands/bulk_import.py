"""
Fast bulk CSV import: bulk_create and minimal queries.

Written when the database was remote and every round-trip cost cross-region latency.
Postgres now sits in the same Docker Compose stack as the app (see AWS_DEPLOYMENT.md),
so the batching matters less than it did — but it is still the fastest way to load the
Sheerpluck/IMSLP CSVs, and it is what the existing 73k rows were loaded with.
"""

import csv
import unicodedata
from django.core.management.base import BaseCommand
from django.db import transaction
from music.models import Country, InstrumentationCategory, DataSource, Composer, Work
from music.utils import generate_title_sort_key


class Command(BaseCommand):
    help = 'Fast bulk CSV import - processes all data in memory then bulk inserts'

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for bulk operations')

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        
        self.stdout.write('Loading all data into memory...')
        
        # Read all CSV data first
        sheerpluck_rows = self.read_csv('data/sheerpluck_guitar_data.csv', 'sheerpluck')
        imslp_rows = self.read_csv('data/imslp_guitar_data.csv', 'imslp')
        all_rows = sheerpluck_rows + imslp_rows
        
        self.stdout.write(f'Loaded {len(all_rows)} total rows')
        
        # Extract unique values
        self.stdout.write('Extracting unique values...')
        countries = set()
        instrumentations = set()
        composers_dict = {}  # (name, birth, death) -> composer data
        
        for row in all_rows:
            country = row.get('Country', '').strip()
            if country:
                countries.add(country)
            
            instr = row.get('Instrumentation', '').strip()
            if instr:
                instrumentations.add(instr)
            
            name = row.get('Name', '').strip()
            birth = self.parse_year(row.get('Birth Year'))
            death = self.parse_year(row.get('Death Year'))
            if name:
                key = (name, birth, death)
                if key not in composers_dict:
                    composers_dict[key] = {
                        'name': name,
                        'birth': birth,
                        'death': death,
                        'country': country
                    }
        
        self.stdout.write(f'Found {len(countries)} countries, {len(instrumentations)} instrumentations, {len(composers_dict)} composers')
        
        # Bulk create reference data
        self.stdout.write('Creating reference data...')
        
        # Data sources
        sheerpluck_source, _ = DataSource.objects.get_or_create(
            name='Sheerpluck',
            defaults={'url': 'https://www.sheerpluck.de'}
        )
        imslp_source, _ = DataSource.objects.get_or_create(
            name='IMSLP',
            defaults={'url': 'https://imslp.org'}
        )
        
        # Countries
        country_map = {}
        existing_countries = {c.name: c for c in Country.objects.all()}
        new_countries = []
        for country_name in countries:
            if country_name not in existing_countries:
                new_countries.append(Country(name=country_name))
        
        if new_countries:
            Country.objects.bulk_create(new_countries, batch_size=batch_size, ignore_conflicts=True)
        
        # Reload to get IDs
        for country in Country.objects.filter(name__in=countries):
            country_map[country.name] = country
        
        # Instrumentations
        instr_map = {}
        existing_instr = {i.name: i for i in InstrumentationCategory.objects.all()}
        new_instr = []
        for instr_name in instrumentations:
            # Truncate to 100 chars to fit database field
            truncated_name = instr_name[:100]
            if truncated_name not in existing_instr:
                new_instr.append(InstrumentationCategory(name=truncated_name))
        
        if new_instr:
            InstrumentationCategory.objects.bulk_create(new_instr, batch_size=batch_size, ignore_conflicts=True)
        
        # Reload to get IDs
        for instr in InstrumentationCategory.objects.filter(name__in=[i[:100] for i in instrumentations]):
            instr_map[instr.name] = instr
        
        # Composers - bulk create
        self.stdout.write(f'Creating {len(composers_dict)} composers...')
        composer_objs = []
        for (name, birth, death), data in composers_dict.items():
            # Parse "Last, First" format from CSV
            if ',' in name:
                parts = name.split(',', 1)
                last_name = parts[0].strip()
                first_name = parts[1].strip() if len(parts) > 1 else ''
            else:
                # Fallback for names without comma
                last_name = name.split()[-1] if ' ' in name else name
                first_name = name.rsplit(' ', 1)[0] if ' ' in name else ''
            
            country = country_map.get(data['country'])
            
            composer_objs.append(Composer(
                full_name=name,
                last_name=last_name,
                first_name=first_name,
                name_normalized=self.normalize(name),
                birth_year=birth,
                death_year=death,
                country=country,
                data_source=sheerpluck_source
            ))
        
        # Clear existing and bulk create
        Composer.objects.all().delete()
        Composer.objects.bulk_create(composer_objs, batch_size=batch_size)
        
        # Reload composers with IDs
        composer_lookup = {}
        for composer in Composer.objects.all():
            key = (composer.full_name, composer.birth_year, composer.death_year)
            composer_lookup[key] = composer
        
        # Works - bulk create
        self.stdout.write(f'Creating works from {len(all_rows)} rows...')
        work_objs = []
        seen_works = set()  # Deduplicate
        
        for row in all_rows:
            source = sheerpluck_source if row['_source'] == 'sheerpluck' else imslp_source
            name = row.get('Name', '').strip()
            title = row.get('Work', '').strip()
            birth = self.parse_year(row.get('Birth Year'))
            death = self.parse_year(row.get('Death Year'))
            
            if not name or not title:
                continue
            
            # Deduplicate
            work_key = (name, birth, death, title)
            if work_key in seen_works:
                continue
            seen_works.add(work_key)
            
            composer_key = (name, birth, death)
            composer = composer_lookup.get(composer_key)
            if not composer:
                continue
            
            instr_name = row.get('Instrumentation', '').strip()
            instr = instr_map.get(instr_name[:100])  # Truncate to match
            
            link = row.get('Link', '').strip()
            work_objs.append(Work(
                composer=composer,
                title=title,
                title_normalized=self.normalize(title),
                title_sort_key=generate_title_sort_key(title),
                instrumentation_category=instr,
                data_source=source,
                external_id=row.get('ID', '').strip() or None,
                sheerpluck_url=link if source == sheerpluck_source else None,
                imslp_url=link if source == imslp_source else None
            ))
        
        # Clear and bulk create works
        Work.objects.all().delete()
        
        self.stdout.write(f'Bulk inserting {len(work_objs)} works...')
        total = len(work_objs)
        for i in range(0, total, batch_size):
            batch = work_objs[i:i+batch_size]
            Work.objects.bulk_create(batch, batch_size=batch_size)
            self.stdout.write(f'  Progress: {min(i+batch_size, total)}/{total}')
        
        self.stdout.write(self.style.SUCCESS(f'\nImport complete! Created {Composer.objects.count()} composers and {Work.objects.count()} works'))
    
    def read_csv(self, filepath, source):
        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['_source'] = source
                rows.append(row)
        return rows
    
    def parse_year(self, value):
        if not value:
            return None
        try:
            year = int(str(value).strip())
            return year if 1000 <= year <= 2100 else None
        except (ValueError, TypeError):
            return None
    
    def normalize(self, text):
        return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8').lower()
