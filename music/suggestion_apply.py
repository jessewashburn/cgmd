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

from .models import Composer, Work, WorkLink, Country
from .utils import clean_country_name

LOOSE_THRESHOLD = 0.5
LOOSE_LIMIT = 5

# Given names that routinely appear in either form across sources, folded to one
# spelling before the token compare so "Chris Gainey" resolves to an existing
# "Gainey, Christopher" instead of quietly creating a second composer.
_NICKNAME_GROUPS = (
    ('alexander', 'alex'), ('andrew', 'andy', 'drew'), ('anthony', 'tony'),
    ('benjamin', 'ben'), ('charles', 'charlie', 'chuck'),
    ('christopher', 'chris'), ('daniel', 'dan', 'danny'),
    ('david', 'dave'), ('donald', 'don'), ('edward', 'ed', 'eddie', 'ted'),
    ('francis', 'frank'), ('frederick', 'fred'), ('gregory', 'greg'),
    ('james', 'jim', 'jimmy'), ('jeffrey', 'jeff'), ('john', 'jack', 'johnny'),
    ('joseph', 'joe'), ('kenneth', 'ken'), ('lawrence', 'larry'),
    ('matthew', 'matt'), ('michael', 'mike'), ('nicholas', 'nick'),
    ('patrick', 'pat'), ('peter', 'pete'), ('philip', 'phil'),
    ('raymond', 'ray'), ('richard', 'rich', 'rick', 'dick'),
    ('robert', 'rob', 'bob', 'bobby'), ('ronald', 'ron'), ('samuel', 'sam'),
    ('stephen', 'steven', 'steve'), ('thomas', 'tom', 'tommy'),
    ('timothy', 'tim'), ('william', 'will', 'bill', 'billy'),
    ('barbara', 'barb'), ('catherine', 'katherine', 'kate', 'cathy', 'kathy'),
    ('deborah', 'debbie', 'deb'), ('elizabeth', 'liz', 'beth', 'betty'),
    ('jennifer', 'jen', 'jenny'), ('margaret', 'meg', 'peggy', 'maggie'),
    ('patricia', 'patty'), ('rebecca', 'becky'), ('susan', 'sue'),
)

# Every variant maps to the group's first (canonical) spelling.
_NICKNAME_CANON = {
    variant: group[0] for group in _NICKNAME_GROUPS for variant in group
}


class UnsupportedSuggestion(Exception):
    """The suggestion type/shape can't be auto-applied (→ 400)."""


class NeedsConfirmation(Exception):
    """Composer resolution is ambiguous; caller must confirm (→ 409)."""
    def __init__(self, payload):
        super().__init__('composer match needs confirmation')
        self.payload = payload


def _normalize(text):
    return unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode('utf-8').lower()


def _raw_tokens(text):
    return frozenset(t for t in _normalize(text).replace(',', ' ').split() if t)


def _tokens(text):
    """Name tokens with nickname variants folded onto one spelling."""
    return frozenset(_NICKNAME_CANON.get(t, t) for t in _raw_tokens(text))


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

    Exact = same token set, nicknames folded (handles "Last, First", compound
    surnames, and "Chris" vs "Christopher").
    Loose = similarity-ranked near matches (pg_trgm on Postgres, difflib elsewhere).
    """
    target_tokens = _tokens(name)
    target_norm = _normalize(name)

    exact = None
    if target_tokens:
        # Anchor the candidate scan on a *raw* token, since name_normalized stores
        # whatever spelling the source used — searching it for the folded form would
        # miss the "Chris" row we are trying to find. Prefer a token that isn't a
        # known given name, which lands on the surname and keeps the scan narrow.
        raw = _raw_tokens(name)
        anchors = [t for t in raw if t not in _NICKNAME_CANON] or list(raw)
        anchor = max(anchors, key=len)
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

    # Fold "USA"/"U.S.A."/"United States of America" onto one name and match the
    # existing row case-insensitively — get_or_create on the raw submitted string
    # spawned a duplicate Country per spelling.
    country = None
    country_name = clean_country_name((data.get('composer_country') or '').strip())
    if country_name:
        country = (Country.objects.filter(name__iexact=country_name).first()
                   or Country.objects.create(name=country_name))

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

    # instrumentation_category is derived from the detail text by Work.save().
    work = Work.objects.create(
        composer=composer,
        title=title,
        title_normalized=_normalize(title),
        composition_year=_int(data.get('composition_year')),
        instrumentation_detail=(data.get('instrumentation_detail') or '').strip(),
        is_public=True,
        needs_review=True,
    )
    return work, 'created'


def _apply_alternate_instrumentations(work, names):
    """Attach user-proposed alternate instrumentations to a work.

    Names, not ids: ids are environment-specific (a category's pk differs between dev
    and prod) and a suggestion can sit pending across a reseed. Unknown names are
    ignored rather than 400-ing — a stale vocabulary should degrade, not reject the
    whole suggestion.

    basis='suggested' marks these as human-approved (an admin clicked Apply), so the
    derivation backfill will never overwrite or delete them.
    """
    from .models import InstrumentationCategory, WorkInstrumentation
    from .utils import UNCATEGORIZED_INSTRUMENTATION, resolve_instrumentation_filter

    added = 0
    for raw in (names or []):
        # resolve_instrumentation_filter, not canonical_instrumentation: the latter
        # buckets anything unrecognised into 'Other', which is a real category, so junk
        # would land as "also playable as Other". This returns None for junk instead.
        name = resolve_instrumentation_filter((raw or '').strip())
        # ...and 'Other' is still reachable by name, but is never a meaningful thing to
        # claim a work is *also* playable as.
        if not name or name == UNCATEGORIZED_INSTRUMENTATION:
            continue
        # An "alternate" identical to the primary is a no-op, not a row.
        if work.instrumentation_category and name == work.instrumentation_category.name:
            continue
        category, _ = InstrumentationCategory.objects.get_or_create(name=name)
        _, created = WorkInstrumentation.objects.get_or_create(
            work=work, category=category, defaults={'basis': 'suggested'},
        )
        if created:
            added += 1
    return added


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
    # After work.save(), so the primary category is up to date and an alternate that
    # merely duplicates it can be recognised and skipped.
    alternates_added = _apply_alternate_instrumentations(
        work, data.get('alternate_instrumentations'))
    _mark_merged(suggestion)
    return {
        'work': {'action': 'updated', 'id': work.id, 'title': work.title},
        'fields_updated': fields_updated,
        'links_added': links_added,
        'alternates_added': alternates_added,
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
        result['alternates_added'] = _apply_alternate_instrumentations(
            work, data.get('alternate_instrumentations'))

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
