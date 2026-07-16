"""Applying suggestions: smart composer matching + new_work/new_composer/edit_work.

Exercises music.suggestion_apply directly (no HTTP/auth) for thorough coverage of
the resolution logic and its duplicate-guardrail (NeedsConfirmation).
"""
import pytest

from music.models import Composer, Country, Work, WorkLink, UserSuggestion
from music.suggestion_apply import (
    apply_suggestion, find_composer_matches, NeedsConfirmation, UnsupportedSuggestion,
)
from .factories import ComposerFactory, WorkFactory

pytestmark = pytest.mark.django_db


def _suggestion(stype, data, **kw):
    return UserSuggestion.objects.create(
        suggestion_type=stype, title='t', description='', suggested_data=data, **kw,
    )


NEW_WORK = {
    'composer_name': 'Agustin Barrios',
    'composer_birth_year': '1885',
    'work_title': 'La Catedral',
    'composition_year': '1921',
    'instrumentation_detail': 'Solo Guitar',
    'links': [{'label': 'Score', 'url': 'https://example.com/score', 'link_type': 'score'}],
}


# --- find_composer_matches --------------------------------------------------

def test_exact_match_is_order_independent():
    c = ComposerFactory(full_name='Barrios, Agustin', last_name='Barrios', name_normalized='')
    c.name_normalized = 'barrios, agustin'
    c.save()
    exact, loose = find_composer_matches('Agustin Barrios')
    assert exact is not None and exact.id == c.id
    assert loose == []


def test_loose_match_on_typo():
    c = ComposerFactory(full_name='Mauro Giuliani', last_name='Giuliani')
    c.name_normalized = 'mauro giuliani'
    c.save()
    exact, loose = find_composer_matches('Mauro Giulliani')  # extra "l"
    assert exact is None
    assert any(cand.id == c.id for cand, _ in loose)


def test_no_match():
    ComposerFactory(full_name='Fernando Sor', last_name='Sor')
    exact, loose = find_composer_matches('Zxqw Nonexistent')
    assert exact is None and loose == []


# --- new_work: create / reuse / confirm -------------------------------------

def test_new_work_no_match_creates_everything():
    s = _suggestion('new_work', NEW_WORK)
    result = apply_suggestion(s)
    assert result['composer']['action'] == 'created'
    assert result['work']['action'] == 'created'
    assert result['links_added'] == 1
    composer = Composer.objects.get(pk=result['composer']['id'])
    assert composer.birth_year == 1885
    work = Work.objects.get(pk=result['work']['id'])
    assert work.composition_year == 1921
    assert work.links.filter(url='https://example.com/score').exists()
    s.refresh_from_db()
    assert s.status == 'merged'


def test_new_work_with_existing_composer_needs_confirmation():
    existing = ComposerFactory(full_name='Barrios, Agustin', last_name='Barrios')
    existing.name_normalized = 'barrios, agustin'
    existing.save()

    s = _suggestion('new_work', NEW_WORK)
    with pytest.raises(NeedsConfirmation) as exc:
        apply_suggestion(s)
    payload = exc.value.payload
    assert payload['needs_confirmation'] is True
    assert payload['composer']['exact_match']['id'] == existing.id
    # nothing created, suggestion still pending
    assert Work.objects.filter(title='La Catedral').count() == 0
    s.refresh_from_db()
    assert s.status == 'pending'


def test_new_work_reuse_chosen_composer():
    existing = ComposerFactory(full_name='Barrios, Agustin', last_name='Barrios')
    s = _suggestion('new_work', NEW_WORK)
    result = apply_suggestion(s, composer_id=existing.id)
    assert result['composer']['action'] == 'reused'
    assert result['composer']['id'] == existing.id
    assert Work.objects.filter(composer=existing, title='La Catedral').exists()


def test_new_work_force_create_despite_match():
    ComposerFactory(full_name='Barrios, Agustin', last_name='Barrios')
    s = _suggestion('new_work', NEW_WORK)
    result = apply_suggestion(s, create_new_composer=True)
    assert result['composer']['action'] == 'created'
    assert Composer.objects.filter(name_normalized='agustin barrios').exists()


def test_new_work_reuses_existing_work_no_duplicate():
    composer = ComposerFactory(full_name='Agustin Barrios', last_name='Barrios')
    composer.name_normalized = 'agustin barrios'
    composer.save()
    WorkFactory(composer=composer, title='La Catedral')

    s = _suggestion('new_work', NEW_WORK)
    result = apply_suggestion(s, composer_id=composer.id)
    assert result['work']['action'] == 'reused'
    assert Work.objects.filter(composer=composer, title__iexact='La Catedral').count() == 1
    assert result['links_added'] == 1  # link still attached to the reused work


# --- new_composer / unsupported / edit_work ---------------------------------

def test_new_composer_creates_composer_only():
    s = _suggestion('new_composer', {'composer_name': 'Brand New Composer'})
    result = apply_suggestion(s)
    assert result['composer']['action'] == 'created'
    assert 'work' not in result


def test_new_work_missing_composer_name_unsupported():
    s = _suggestion('new_work', {'work_title': 'Orphan'})
    with pytest.raises(UnsupportedSuggestion):
        apply_suggestion(s)


def test_edit_composer_unsupported():
    s = _suggestion('edit_composer', {'full_name': 'X'})
    with pytest.raises(UnsupportedSuggestion):
        apply_suggestion(s)


def test_edit_work_updates_fields_and_links():
    work = WorkFactory(title='Old', composition_year=None)
    s = _suggestion(
        'edit_work',
        {'title': 'New', 'composition_year': 1999,
         'links': [{'label': 'Pub', 'url': 'https://pub.example'}]},
        related_work=work,
    )
    result = apply_suggestion(s)
    assert 'composition_year' in result['fields_updated']
    assert result['links_added'] == 1
    work.refresh_from_db()
    assert work.title == 'New'
    assert work.composition_year == 1999
    assert WorkLink.objects.filter(work=work, url='https://pub.example').exists()


# --- instrumentation ---------------------------------------------------------

def test_new_work_categorises_instrumentation():
    """'Solo Guitar' is not a category name; it has to be mapped to 'Solo'. The old
    exact-equality matcher returned None here and the work got a NULL category."""
    s = _suggestion('new_work', NEW_WORK)
    result = apply_suggestion(s, create_new_composer=True)
    work = Work.objects.get(pk=result['work']['id'])
    assert work.instrumentation_detail == 'Solo Guitar'
    assert work.instrumentation_category.name == 'Solo'


def test_edit_work_recategorises_instrumentation():
    """The Firelight bug: applying an edit that adds instrumentation text left the
    category NULL, so the work never appeared under ?instrumentation=Octet."""
    work = WorkFactory(title='Firelight', instrumentation_detail='')
    s = _suggestion('edit_work', {'instrumentation_detail': 'Octet'}, related_work=work)

    result = apply_suggestion(s)
    assert 'instrumentation_detail' in result['fields_updated']
    work.refresh_from_db()
    assert work.instrumentation_category.name == 'Octet'


# --- composer resolution gaps ------------------------------------------------

def test_nickname_matches_existing_composer():
    """"Chris Gainey" must resolve to "Gainey, Christopher" rather than silently
    creating a second composer for the same person."""
    existing = ComposerFactory(full_name='Gainey, Christopher', last_name='Gainey',
                               name_normalized='')
    existing.name_normalized = 'gainey, christopher'
    existing.save()

    exact, _ = find_composer_matches('Chris Gainey')
    assert exact is not None and exact.id == existing.id


def test_nickname_match_works_in_either_direction():
    existing = ComposerFactory(full_name='Li, Chris', last_name='Li', name_normalized='')
    existing.name_normalized = 'li, chris'
    existing.save()

    exact, _ = find_composer_matches('Christopher Li')
    assert exact is not None and exact.id == existing.id


def test_nickname_folding_does_not_merge_different_people():
    ComposerFactory(full_name='Christopher Parkening', last_name='Parkening')
    exact, _ = find_composer_matches('Christopher Gainey')
    assert exact is None


def test_created_composer_reuses_country_across_spellings():
    """get_or_create on the raw submitted string made a new Country per spelling."""
    usa = Country.objects.create(name='United States')
    s = _suggestion('new_composer', {'composer_name': 'Someone New',
                                     'composer_country': 'USA'})
    result = apply_suggestion(s, create_new_composer=True)

    composer = Composer.objects.get(pk=result['composer']['id'])
    assert composer.country_id == usa.id
    assert Country.objects.filter(name__iexact='usa').count() == 0


def test_nickname_resolution_surfaces_the_existing_composer():
    """"Chris Gainey" must offer the existing "Gainey, Christopher" for confirmation
    rather than being applied straight into a second composer row."""
    from music.suggestion_apply import NeedsConfirmation

    existing = ComposerFactory(full_name='Gainey, Christopher', last_name='Gainey',
                               name_normalized='')
    existing.name_normalized = 'gainey, christopher'
    existing.save()

    s = UserSuggestion.objects.create(
        suggestion_type='new_work', title='t', description='',
        suggested_data={'composer_name': 'Chris Gainey', 'work_title': 'Firelight',
                        'instrumentation_detail': 'Octet'},
    )
    with pytest.raises(NeedsConfirmation) as exc:
        apply_suggestion(s)
    assert exc.value.payload['composer']['exact_match']['id'] == existing.id
