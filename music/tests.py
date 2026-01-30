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
