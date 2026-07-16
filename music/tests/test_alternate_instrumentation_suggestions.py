"""Users proposing alternate instrumentations through the suggestion flow.

Rides the existing edit_work / new_work pipeline rather than adding a parallel one.
The guardrail that matters: rows land as basis='suggested' only when an admin applies
the suggestion, and the derivation backfill must never overwrite them afterwards.

See SDD: alternate-work-instrumentations.
"""
import pytest

from music.models import (
    InstrumentationCategory, UserSuggestion, WorkInstrumentation,
)
from music.suggestion_apply import apply_suggestion
from .factories import WorkFactory

pytestmark = pytest.mark.django_db


def edit_suggestion(work, **data):
    return UserSuggestion.objects.create(
        suggestion_type='edit_work',
        title=f'Edit work: {work.title}',
        description='via form',
        related_work=work,
        suggested_data=data,
    )


def test_apply_attaches_suggested_alternates():
    work = WorkFactory(title='Realms', instrumentation_detail='Guitar and Tape')
    suggestion = edit_suggestion(work, alternate_instrumentations=['Quintet'])

    result = apply_suggestion(suggestion)

    assert result['alternates_added'] == 1
    row = WorkInstrumentation.objects.get(work=work)
    assert row.category.name == 'Quintet'
    assert row.basis == 'suggested'


def test_suggested_names_are_canonicalised():
    """The form sends category names; a near-miss should still land in the right
    bucket rather than being dropped."""
    work = WorkFactory(title='Realms', instrumentation_detail='Guitar and Tape')
    suggestion = edit_suggestion(work, alternate_instrumentations=['guitar (5)'])

    apply_suggestion(suggestion)

    assert WorkInstrumentation.objects.get(work=work).category.name == 'Quintet'


def test_unknown_name_is_ignored_not_rejected():
    """A stale vocabulary should degrade, not 400 the whole suggestion."""
    work = WorkFactory(title='Realms', instrumentation_detail='Guitar and Tape')
    suggestion = edit_suggestion(
        work, alternate_instrumentations=['Quintet', 'zzzznonsense'])

    result = apply_suggestion(suggestion)

    assert result['alternates_added'] == 1
    assert [r.category.name for r in WorkInstrumentation.objects.filter(work=work)] == ['Quintet']


def test_alternate_matching_the_primary_is_skipped():
    """"Also playable as Solo" on a solo work is a no-op, not a row."""
    work = WorkFactory(title='Plain', instrumentation_detail='Solo')
    assert work.instrumentation_category.name == 'Solo'
    suggestion = edit_suggestion(work, alternate_instrumentations=['Solo'])

    result = apply_suggestion(suggestion)

    assert result['alternates_added'] == 0
    assert not WorkInstrumentation.objects.filter(work=work).exists()


def test_applying_twice_is_idempotent():
    work = WorkFactory(title='Realms', instrumentation_detail='Guitar and Tape')
    apply_suggestion(edit_suggestion(work, alternate_instrumentations=['Quintet']))
    apply_suggestion(edit_suggestion(work, alternate_instrumentations=['Quintet']))

    assert WorkInstrumentation.objects.filter(work=work).count() == 1


def test_suggestion_survives_the_derivation_backfill():
    """The whole point of `basis`. A human approved this row; re-deriving from the
    detail text must not delete it just because the text doesn't imply it."""
    from music.models import sync_work_alternate_instrumentations

    work = WorkFactory(title='Realms', instrumentation_detail='Guitar and Tape')
    apply_suggestion(edit_suggestion(work, alternate_instrumentations=['Quintet']))

    sync_work_alternate_instrumentations(work)

    row = WorkInstrumentation.objects.get(work=work)
    assert row.category.name == 'Quintet'
    assert row.basis == 'suggested'


def test_edit_work_without_alternates_still_applies():
    """The field is optional; existing suggestions in flight have no such key."""
    work = WorkFactory(title='Realms', instrumentation_detail='Solo')
    suggestion = edit_suggestion(work, title='Realms Revised')

    result = apply_suggestion(suggestion)

    assert result['alternates_added'] == 0
    work.refresh_from_db()
    assert work.title == 'Realms Revised'
