"""Unit tests for the title sort-key generator and its maintenance on Work.save().

Regression cover for the bug where `Work.save()` populated `title_normalized` but
never `title_sort_key`, leaving the Works default (alphabetical) sort broken for any
work created/edited outside the one-off `update_sort_keys` command.
"""
import pytest

from music.utils import generate_title_sort_key
from .factories import WorkFactory

pytestmark = pytest.mark.django_db


class TestGenerateTitleSortKey:
    def test_latin_title_bucket_1_folded(self):
        assert generate_title_sort_key('Cadenza') == '1|cadenza'

    def test_accents_folded_to_ascii(self):
        # Accented and unaccented variants collapse to the same key so they sort adjacently.
        assert generate_title_sort_key('À bout portant') == generate_title_sort_key('a bout portant')
        assert generate_title_sort_key('Étude') == '1|etude'

    def test_leading_punctuation_stripped(self):
        # Leading symbols are dropped so the title sorts by its first letter/digit.
        assert generate_title_sort_key('...Adagio') == '1|adagio'
        assert generate_title_sort_key('¡Viva') == generate_title_sort_key('Viva')

    def test_numeric_leading_bucket_2_sorts_after_letters(self):
        assert generate_title_sort_key('10 Studies') == '2|10 studies'
        # Bucket 1 (letters) sorts before bucket 2 (numbers) lexicographically.
        assert generate_title_sort_key('Zebra') < generate_title_sort_key('10 Studies')

    def test_non_latin_script_bucket_3(self):
        key = generate_title_sort_key('Ιθάκη')
        assert key.startswith('3|')

    def test_symbol_only_and_empty_bucket_4_sort_last(self):
        assert generate_title_sort_key('_____') == '4|_____'
        assert generate_title_sort_key('') == '4|'
        # Bucket 4 sorts after every other bucket.
        assert generate_title_sort_key('_____') > generate_title_sort_key('Zebra')
        assert generate_title_sort_key('_____') > generate_title_sort_key('999')


class TestWorkSaveMaintainsSortKey:
    def test_created_work_has_sort_key(self):
        work = WorkFactory(title='Nocturne')
        assert work.title_sort_key == '1|nocturne'
        assert work.title_normalized == 'nocturne'

    def test_sort_key_recomputed_on_title_change(self):
        work = WorkFactory(title='Zebra')
        assert work.title_sort_key == '1|zebra'

        work.title = 'Apple'
        work.save()
        work.refresh_from_db()
        assert work.title_sort_key == '1|apple'
        assert work.title_normalized == 'apple'

    def test_no_null_sort_keys_from_factory(self):
        # The original bug: factory/ORM-created works had NULL keys.
        work = WorkFactory(title='Prelude')
        assert work.title_sort_key
