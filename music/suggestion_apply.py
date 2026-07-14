"""
Applying user suggestions to the database.

- edit_work: write the edit-form fields + proposed links onto the linked Work.
- new_work / new_composer: resolve the composer with a smart compare (exact
  token-set match + loose similarity), and unless the admin has explicitly chosen
  how to resolve, raise NeedsConfirmation so the UI can show the matches and let
  them reuse an existing composer or deliberately create a new one. This is the
  guardrail against duplicate composers.
"""
import unicodedata
from difflib import SequenceMatcher

from django.db import connection, transaction
from django.utils import timezone

from .models import Composer, Work, WorkLink, Country, InstrumentationCategory

LOOSE_THRESHOLD = 0.5
LOOSE_LIMIT = 5


class UnsupportedSuggestion(Exception):
    """The suggestion type/shape can't be auto-applied (→ 400)."""


class NeedsConfirmation(Exception):
    """Composer resolution is ambiguous; caller must confirm (→ 409)."""
    def __init__(self, payload):
        super().__init__('composer match needs confirmation')
        self.payload = payload


def _normalize(text):
    return unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode('utf-8').lower()


def _tokens(text):
    return frozenset(t for t in _normalize(text).replace(',', ' ').split() if t)


def _title_key(text):
    return ''.join(ch for ch in _normalize(text) if ch.isalnum())


def _composer_brief(composer, score=None, match_type=None):
    brief = {
        'id': composer.id,
        'full_name': composer.full_name,
        'birth_year': composer.birth_year,
        'death_year': composer.death_year,
    }
    if score is not None:
        brief['score'] = score
    if match_type:
        brief['match_type'] = match_type
    return brief


def find_composer_matches(name):
    """Return (exact_match | None, [ (composer, score), ... ]) for a suggested name.

    Exact = same token set (handles "Last, First" and compound surnames).
    Loose = similarity-ranked near matches (pg_trgm on Postgres, difflib elsewhere).
    """
    target_tokens = _tokens(name)
    target_norm = _normalize(name)

    exact = None
    if target_tokens:
        anchor = max(target_tokens, key=len)
        for cand in Composer.objects.filter(name_normalized__icontains=anchor):
            if _tokens(cand.full_name) == target_tokens:
                exact = cand
                break

    loose = []
    if connection.vendor == 'postgresql':
        from django.contrib.postgres.search import TrigramSimilarity
        qs = (Composer.objects
              .annotate(sim=TrigramSimilarity('name_normalized', target_norm))
              .filter(sim__gt=0.3)
              .order_by('-sim'))
        for cand in qs[:LOOSE_LIMIT + 1]:
            if exact and cand.id == exact.id:
                continue
            loose.append((cand, round(cand.sim, 3)))
    else:
        scored = []
        for cand in Composer.objects.all():
            if exact and cand.id == exact.id:
                continue
            ratio = SequenceMatcher(None, target_norm, cand.name_normalized).ratio()
            if ratio >= LOOSE_THRESHOLD:
                scored.append((cand, round(ratio, 3)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        loose = scored
    return exact, loose[:LOOSE_LIMIT]


def _create_composer(data, name):
    parts = name.rsplit(' ', 1)
    first_name, last_name = (parts[0].strip(), parts[1].strip()) if len(parts) == 2 else ('', name)

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    birth_year = _int(data.get('composer_birth_year'))
    death_year = _int(data.get('composer_death_year'))

    country = None
    country_name = (data.get('composer_country') or '').strip()
    if country_name:
        country, _ = Country.objects.get_or_create(name=country_name)

    is_living = death_year is None and birth_year is not None and birth_year > 1900

    return Composer.objects.create(
        full_name=name,
        first_name=first_name,
        last_name=last_name,
        name_normalized=_normalize(name),
        birth_year=birth_year,
        death_year=death_year,
        country=country,
        is_living=is_living,
        needs_review=True,
    )


def _match_instrumentation(text):
    target = _normalize(text)
    if not target:
        return None
    for cat in InstrumentationCategory.objects.all():
        if _normalize(cat.name) == target:
            return cat
    return None


def _get_or_create_work(composer, title, data):
    key = _title_key(title)
    for existing in composer.works.all():
        if _title_key(existing.title) == key:
            return existing, 'reused'

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    instrumentation = (data.get('instrumentation_detail') or '').strip()
    work = Work.objects.create(
        composer=composer,
        title=title,
        title_normalized=_normalize(title),
        composition_year=_int(data.get('composition_year')),
        instrumentation_detail=instrumentation,
        instrumentation_category=_match_instrumentation(instrumentation),
        is_public=True,
        needs_review=True,
    )
    return work, 'created'


def _attach_links(work, links):
    added = 0
    for link in (links or []):
        url = (link.get('url') or '').strip()
        label = (link.get('label') or '').strip()
        if not url or not label:
            continue
        _, created = WorkLink.objects.get_or_create(
            work=work, url=url,
            defaults={'label': label, 'link_type': link.get('link_type') or 'other'},
        )
        if created:
            added += 1
    return added


def _mark_merged(suggestion):
    suggestion.status = 'merged'
    suggestion.reviewed_at = timezone.now()
    suggestion.save(update_fields=['status', 'reviewed_at', 'updated_at'])


def _apply_edit_work(suggestion, data):
    if not suggestion.related_work_id:
        raise UnsupportedSuggestion('Edit-work suggestion has no linked work.')
    work = suggestion.related_work
    fields_updated = []

    for field in ('title', 'instrumentation_detail'):
        value = data.get(field)
        if value not in (None, '') and getattr(work, field) != value:
            setattr(work, field, value)
            fields_updated.append(field)

    if 'composition_year' in data:
        raw = data.get('composition_year')
        try:
            year = int(raw) if raw not in (None, '') else None
        except (TypeError, ValueError):
            year = work.composition_year
        if work.composition_year != year:
            work.composition_year = year
            fields_updated.append('composition_year')

    work.save()
    links_added = _attach_links(work, data.get('links'))
    _mark_merged(suggestion)
    return {
        'work': {'action': 'updated', 'id': work.id, 'title': work.title},
        'fields_updated': fields_updated,
        'links_added': links_added,
    }


def _apply_new(suggestion, data, composer_id, create_new_composer):
    name = (data.get('composer_name') or data.get('full_name') or '').strip()
    if not name:
        raise UnsupportedSuggestion('Suggestion has no composer name to create from.')

    if composer_id:
        try:
            composer = Composer.objects.get(pk=composer_id)
        except Composer.DoesNotExist:
            raise UnsupportedSuggestion('Chosen composer no longer exists.')
        composer_action = 'reused'
    elif create_new_composer:
        composer = _create_composer(data, name)
        composer_action = 'created'
    else:
        exact, loose = find_composer_matches(name)
        if exact or loose:
            raise NeedsConfirmation({
                'needs_confirmation': True,
                'composer': {
                    'suggested': {
                        'name': name,
                        'birth_year': data.get('composer_birth_year') or None,
                    },
                    'exact_match': _composer_brief(exact, match_type='exact') if exact else None,
                    'loose_matches': [_composer_brief(c, score=s, match_type='loose') for c, s in loose],
                },
            })
        composer = _create_composer(data, name)
        composer_action = 'created'

    result = {'composer': {'action': composer_action, 'id': composer.id, 'full_name': composer.full_name}}

    if suggestion.suggestion_type == 'new_work':
        title = (data.get('work_title') or data.get('title') or '').strip()
        if not title:
            raise UnsupportedSuggestion('New-work suggestion has no work title.')
        work, work_action = _get_or_create_work(composer, title, data)
        result['work'] = {'action': work_action, 'id': work.id, 'title': work.title}
        result['links_added'] = _attach_links(work, data.get('links'))

    _mark_merged(suggestion)
    return result


@transaction.atomic
def apply_suggestion(suggestion, *, composer_id=None, create_new_composer=False):
    """Apply a suggestion. Raises NeedsConfirmation (409) or UnsupportedSuggestion (400)."""
    data = suggestion.suggested_data or {}
    stype = suggestion.suggestion_type
    if stype == 'edit_work':
        return _apply_edit_work(suggestion, data)
    if stype in ('new_work', 'new_composer'):
        return _apply_new(suggestion, data, composer_id, create_new_composer)
    raise UnsupportedSuggestion(f'Apply is not supported for suggestion type "{stype}".')
