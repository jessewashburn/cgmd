"""Era classification for composers.

A composer is not "a Romantic". They were *active across a span of years*, and that
span *overlaps* one or more era windows — which is why membership is naturally
multi-valued (Agustín Barrios, 1885-1944, is both Romantic and Modern) without
anyone hand-maintaining a list.

Birth/death years are the only signal available: `Composer.biography` and
`Work.composition_year` are empty for every row in the catalogue, so there is no
text to classify and nothing cleverer than arithmetic to do. That is a feature —
the result is deterministic, re-runnable, and explainable to a user ("active
1905-1944, overlaps Romantic and Modern").

Everything here is pure: no imports from .models, no DB access. `ComposerEra` rows
are materialised from these functions by the `backfill_composer_eras` command and
kept fresh by a post_save signal (see models.py).
"""

from datetime import datetime
from typing import List, Optional, Tuple

# Age at which we assume a composer started writing. Deliberately early: it widens
# every span backwards, and an over-inclusive tag beats a missing one.
CREATIVE_START_AGE = 20

# Career end for a composer with a birth year but no death year who isn't flagged
# living — i.e. someone born long ago whose death we simply don't record.
ASSUMED_LIFESPAN = 75

# Era windows, as (slug, label, start_year, end_year).
#
# The 20-year overlap at each seam is the point, not sloppiness: musical eras don't
# begin on a date, and the brief is to be over- rather than under-inclusive. It is
# what makes Sor (d. 1839) both Classical and Romantic, and Tárrega (d. 1909) both
# Romantic and Modern.
#
# These numbers are tuning knobs, not architecture. Change one, re-run
# `manage.py backfill_composer_eras`, and nothing else in the system moves.
ERA_WINDOWS: List[Tuple[str, str, int, int]] = [
    ('renaissance',  'Renaissance',  1400, 1600),
    ('baroque',      'Baroque',      1580, 1750),
    ('classical',    'Classical',    1730, 1820),
    ('romantic',     'Romantic',     1800, 1910),
    ('modern',       'Modern',       1890, 2000),
    ('21st-century', '21st Century', 2000, 9999),  # open-ended; clamped to now at use
]

# Slug codes rather than display strings, following WorkLink.LINK_TYPE_CHOICES (the
# newest choices field in the repo). Composer.period's value-equals-label style is
# the thing this module replaces.
ERA_CHOICES = [(slug, label) for slug, label, _, _ in ERA_WINDOWS]

ERA_SLUGS = frozenset(slug for slug, _, _, _ in ERA_WINDOWS)

_WINDOW_BY_SLUG = {slug: (start, end) for slug, _, start, end in ERA_WINDOWS}
_LABEL_BY_SLUG = {slug: label for slug, label, _, _ in ERA_WINDOWS}
_ORDER_BY_SLUG = {slug: i for i, (slug, _, _, _) in enumerate(ERA_WINDOWS)}


def era_label(slug: str) -> str:
    """Display label for a slug, falling back to the slug itself."""
    return _LABEL_BY_SLUG.get(slug, slug)


def sort_era_slugs(slugs) -> List[str]:
    """Order slugs chronologically.

    Stored rows have no inherent order (ComposerEra rows are written from a set), so
    anything user-facing must sort explicitly or 'Modern, Romantic' shows up.
    """
    return sorted(slugs, key=lambda slug: _ORDER_BY_SLUG.get(slug, len(ERA_WINDOWS)))


def current_year() -> int:
    """Indirection so tests can freeze 'now' without patching datetime globally."""
    return datetime.now().year


def era_windows() -> List[Tuple[str, str, int, int]]:
    """ERA_WINDOWS with the open-ended final window clamped to the current year.

    Serialised by /api/eras/ and used by the UI to explain an era's date range, so
    it must report 2000-<this year> rather than the 9999 sentinel.
    """
    now = current_year()
    return [
        (slug, label, start, min(end, now))
        for slug, label, start, end in ERA_WINDOWS
    ]


def active_span(
    birth_year: Optional[int],
    death_year: Optional[int],
    is_living: bool = False,
) -> Optional[Tuple[int, int]]:
    """The years a composer was plausibly writing, or None if undeterminable.

    Returns (start, end) inclusive. None means we have no dates at all — the caller
    should leave the composer untagged rather than guess (about 22% of the
    catalogue; see the composer-era-tagging SDD).
    """
    now = current_year()

    if birth_year is not None:
        start = birth_year + CREATIVE_START_AGE
        if death_year is not None:
            end = death_year
        elif is_living:
            end = now
        else:
            end = min(birth_year + ASSUMED_LIFESPAN, now)
        # A composer who died before we assume they started (very short life, or bad
        # data) still gets a non-empty one-year span rather than an inverted one.
        return (start, max(start, end))

    if death_year is not None:
        # Death year only (41 composers): assume a normal-length career ending at death.
        return (death_year - (ASSUMED_LIFESPAN - CREATIVE_START_AGE), death_year)

    return None


def eras_for_span(span: Optional[Tuple[int, int]]) -> List[str]:
    """Era slugs whose window intersects `span`, in chronological order."""
    if span is None:
        return []
    start, end = span
    now = current_year()
    return [
        slug
        for slug, _, window_start, window_end in ERA_WINDOWS
        if start <= min(window_end, now) and end >= window_start
    ]


def eras_for_composer(
    birth_year: Optional[int],
    death_year: Optional[int],
    is_living: bool = False,
) -> List[str]:
    """Era slugs for a composer's dates. Empty when there are no dates to go on."""
    return eras_for_span(active_span(birth_year, death_year, is_living))


def implied_birth_range(era_slug: str) -> Optional[Tuple[int, int]]:
    """The birth years that could place a composer in `era_slug` — the inverse of
    the derivation above.

    Powers the UI's reconciliation affordance: era tags are *derived from* birth
    years, so an era chip and the birth-year slider are two views of one axis and
    can silently contradict each other ("Baroque" + born 1900-2000 = no rows). This
    lets the empty state say *"Baroque composers were born roughly 1505-1730"* and
    offer to widen the slider, instead of showing a blank table.

    Widest possible reading, to match the over-inclusive spirit: the earliest birth
    is someone who died at the window's start after a full life; the latest is
    someone who reached CREATIVE_START_AGE just as the window closed.
    """
    window = _WINDOW_BY_SLUG.get(era_slug)
    if window is None:
        return None
    start, end = window
    return (start - ASSUMED_LIFESPAN, min(end, current_year()) - CREATIVE_START_AGE)


def parse_era_filter(value: Optional[str]) -> List[str]:
    """Parse an ?eras=romantic,modern query param into known slugs, preserving order.

    Unknown slugs are dropped rather than raising, so a stale bookmark or a renamed
    era degrades instead of 400-ing.

    Note the caller's obligation: an all-junk value (?eras=bogus) yields [], which is
    *not* the same as the param being absent. Per `resolve_instrumentation_filter`'s
    rule — "a junk filter must return no works, not the whole uncategorised bucket" —
    a present-but-unparseable era filter must return no composers. Only an absent
    param means "no era filter". Views must test the raw param, not this list, to
    tell the two apart.
    """
    if not value:
        return []
    seen = set()
    slugs = []
    for raw in value.split(','):
        slug = raw.strip().lower()
        if slug in ERA_SLUGS and slug not in seen:
            seen.add(slug)
            slugs.append(slug)
    return slugs
