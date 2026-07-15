"""Composer matching in the BCGS commissions seed.

The seed is meant to be re-run, so the risk isn't a bad first import — it's a
later run silently re-attaching works to the wrong composer. These tests cover
the name-shaped ways that can happen.
"""
import pytest
from django.core.management import call_command

from music.models import Composer, Work
from music.tests.factories import ComposerFactory

pytestmark = pytest.mark.django_db


def seed():
    call_command('seed_bcgs_commissions')


def test_matches_existing_surname_first_composer_without_duplicating():
    """The catalogue stores "Last, First"; the seed must reuse, not re-create."""
    existing = ComposerFactory(
        full_name='Gainey, Christopher', first_name='Christopher',
        last_name='Gainey', birth_year=None,
    )

    seed()

    assert Composer.objects.filter(name_normalized='gainey, christopher').count() == 1
    assert existing.works.filter(title='Chupacabra').exists()


def test_homonym_with_identical_token_set_is_not_merged():
    """"Chase, Jordan" (BCGS) and "Jordan, Chase" (Sheerpluck, b. 1998) are two
    different people whose names are mirror images. They share a token set, so
    the seed's order-independent fallback cannot tell them apart — only the
    exact normalized full_name match keeps them separate. These two were merged
    once and hand-split in prod; this test is what stops that recurring."""
    other_person = ComposerFactory(
        full_name='Jordan, Chase', first_name='Chase', last_name='Jordan',
        birth_year=1998,
    )

    seed()

    # The Sheerpluck record must not acquire the BCGS works.
    assert not other_person.works.exists()

    bcgs = Composer.objects.get(name_normalized='chase, jordan')
    assert bcgs.pk != other_person.pk
    assert set(bcgs.works.values_list('title', flat=True)) == {
        'Nevermore', 'Between Earth and Sky',
    }


def test_compound_surname_keeps_both_parts():
    """"Sanz Escallón, Antonio" must parse to last "Sanz Escallón", not "Escallón"
    — last_name drives Composer.Meta.ordering, so a bad split misfiles him."""
    seed()

    composer = Composer.objects.get(name_normalized='sanz escallon, antonio')
    assert composer.first_name == 'Antonio'
    assert composer.last_name == 'Sanz Escallón'


def test_created_composers_are_stored_surname_first():
    """Every composer the seed creates should follow the catalogue's convention."""
    seed()

    created = Composer.objects.filter(data_source__name='BCGS')
    assert created.exists()
    for composer in created:
        assert ',' in composer.full_name, f'{composer.full_name} is not surname-first'


def test_rerun_is_idempotent():
    seed()
    composers, works = Composer.objects.count(), Work.objects.count()

    seed()

    assert Composer.objects.count() == composers
    assert Work.objects.count() == works
