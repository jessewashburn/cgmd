"""
Tests for data import and cleaning utilities.
"""

from django.test import TestCase
from music.utils import (
    normalize_name, parse_composer_name, clean_year,
    clean_title, is_living_composer, clean_country_name,
    split_movements
)


class DataCleaningTests(TestCase):
    """Test data cleaning utilities"""

    def test_normalize_name(self):
        """Test name normalization"""
        self.assertEqual(normalize_name('Albéniz'), 'albeniz')
        self.assertEqual(normalize_name('François'), 'francois')
        self.assertEqual(normalize_name('MOZART'), 'mozart')
        self.assertEqual(normalize_name(''), '')

    def test_parse_composer_name(self):
        """Test composer name parsing"""
        # "Last, First" format
        first, last, full = parse_composer_name('Mozart, Wolfgang Amadeus')
        self.assertEqual(last, 'Mozart')
        self.assertEqual(first, 'Wolfgang Amadeus')
        self.assertEqual(full, 'Wolfgang Amadeus Mozart')

        # "First Last" format
        first, last, full = parse_composer_name('John Williams')
        self.assertEqual(first, 'John')
        self.assertEqual(last, 'Williams')
        self.assertEqual(full, 'John Williams')

        # Single name
        first, last, full = parse_composer_name('Sting')
        self.assertEqual(first, '')
        self.assertEqual(last, 'Sting')
        self.assertEqual(full, 'Sting')

    def test_clean_year(self):
        """Test year cleaning"""
        self.assertEqual(clean_year('1685'), 1685)
        self.assertEqual(clean_year('ca. 1500'), 1500)
        self.assertEqual(clean_year('1750?'), 1750)
        self.assertEqual(clean_year(''), None)
        self.assertEqual(clean_year(None), None)
        self.assertEqual(clean_year('invalid'), None)

    def test_clean_title(self):
        """Test title cleaning"""
        self.assertEqual(clean_title('  Symphony  No. 5  '), 'Symphony No. 5')
        self.assertEqual(clean_title('Concerto,'), 'Concerto')
        self.assertEqual(clean_title(''), '')

    def test_is_living_composer(self):
        """Test living composer determination"""
        self.assertTrue(is_living_composer(1970, None))
        self.assertFalse(is_living_composer(1970, 2020))
        self.assertFalse(is_living_composer(1900, None))  # Too old
        self.assertFalse(is_living_composer(None, None))

    def test_clean_country_name(self):
        """Test country name cleaning"""
        self.assertEqual(clean_country_name('USA'), 'United States')
        self.assertEqual(clean_country_name('UK'), 'United Kingdom')
        self.assertEqual(clean_country_name('The Netherlands'), 'Netherlands')
        self.assertEqual(clean_country_name('France'), 'France')

    def test_split_movements(self):
        """Test movement splitting"""
        movements = split_movements('1. Allegro; 2. Andante; 3. Presto')
        self.assertEqual(len(movements), 3)
        self.assertEqual(movements[0], 'Allegro')
        self.assertEqual(movements[1], 'Andante')
        self.assertEqual(movements[2], 'Presto')

        movements = split_movements('I. Fast\nII. Slow\nIII. Fast')
        self.assertEqual(len(movements), 3)
        self.assertEqual(movements[0], 'Fast')


class APITests(TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        """Create test data"""
        from .models import Country, Composer, Work, InstrumentationCategory, DataSource
        
        # Create test data
        self.country = Country.objects.create(name='Test Country', iso_code='TC')
        self.data_source = DataSource.objects.create(name='Test Source')
        self.instrumentation = InstrumentationCategory.objects.create(name='Solo')
        
        self.composer = Composer.objects.create(
            full_name='Test Composer',
            first_name='Test',
            last_name='Composer',
            name_normalized='test composer',
            birth_year=1900,
            country=self.country,
            data_source=self.data_source
        )
        
        self.work = Work.objects.create(
            composer=self.composer,
            title='Test Work',
            title_normalized='test work',
            composition_year=1950,
            instrumentation_category=self.instrumentation,
            difficulty_level=5,
            is_public=True,
            data_source=self.data_source
        )
    
    def test_composers_list(self):
        """Test composers list endpoint"""
        from rest_framework.test import APIClient
        client = APIClient()
        
        response = client.get('/api/composers/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
    
    def test_works_list(self):
        """Test works list endpoint"""
        from rest_framework.test import APIClient
        client = APIClient()
        
        response = client.get('/api/works/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
    
    def test_composer_detail(self):
        """Test composer detail endpoint"""
        from rest_framework.test import APIClient
        client = APIClient()
        
        response = client.get(f'/api/composers/{self.composer.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['full_name'], 'Test Composer')
    
    def test_work_search(self):
        """Test work search endpoint"""
        from rest_framework.test import APIClient
        client = APIClient()
        
        response = client.get('/api/works/search/?q=test')
        self.assertEqual(response.status_code, 200)
