"""Era derivation — pure interval arithmetic, no DB.

The window numbers in music/eras.py are tuning knobs and are expected to move. These
tests pin *behaviour that must survive tuning* (multi-membership, seam inclusivity,
undated composers staying untagged) plus a handful of real composers whose
classification is the whole point of the feature.
"""
import pytest

from music import eras
from music.eras import (
    active_span,
    era_windows,
    eras_for_composer,
    implied_birth_range,
    parse_era_filter,
)


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    """Freeze 'now' so living composers and the open-ended 21st-century window
    don't make these tests drift with the calendar."""
    monkeypatch.setattr(eras, 'current_year', lambda: 2026)


# --- active_span -------------------------------------------------------------

def test_span_starts_at_creative_age_and_ends_at_death():
    assert active_span(1885, 1944) == (1905, 1944)


def test_span_of_living_composer_runs_to_now():
    assert active_span(1939, None, is_living=True) == (1959, 2026)


def test_span_without_death_assumes_a_lifespan():
    # Born 1700, no death recorded, not flagged living -> 1720..1775.
    assert active_span(1700, None) == (1720, 1775)


def test_span_without_death_never_runs_past_now():
    _, end = active_span(2000, None)
    assert end == 2026


def test_span_from_death_year_alone():
    # 41 composers have a death year but no birth year.
    assert active_span(None, 1650) == (1595, 1650)


def test_span_is_never_inverted_by_an_early_death():
    # Died at 10 (or bad data): degenerate but ordered, not (1920, 1910).
    start, end = active_span(1900, 1910)
    assert start <= end


def test_no_dates_means_no_span():
    assert active_span(None, None) is None
    assert active_span(None, None, is_living=False) is None


# --- multi-membership --------------------------------------------------------

def test_barrios_is_romantic_and_modern():
    """The stated ground truth for the feature: Agustín Barrios Mangoré,
    1885-1944, must come out Romantic *and* Modern."""
    assert eras_for_composer(1885, 1944) == ['romantic', 'modern']


@pytest.mark.parametrize('name,birth,death,living,expected', [
    ('Sor',          1778, 1839, False, ['classical', 'romantic']),
    ('Giuliani',     1781, 1829, False, ['classical', 'romantic']),
    ('Tárrega',      1852, 1909, False, ['romantic', 'modern']),
    ('Villa-Lobos',  1887, 1959, False, ['romantic', 'modern']),
    ('Britten',      1913, 1976, False, ['modern']),
    ('Takemitsu',    1930, 1996, False, ['modern']),
    ('Brouwer',      1939, None, True,  ['modern', '21st-century']),
    ('Dyens',        1955, 2016, False, ['modern', '21st-century']),
    ('Carter',       1908, 2012, False, ['modern', '21st-century']),
    # A long life across a seam is what it takes to earn three eras; only three
    # composers in the catalogue do.
    ('Albanese',     1728, 1803, False, ['baroque', 'classical', 'romantic']),
])
def test_real_composers(name, birth, death, living, expected):
    assert eras_for_composer(birth, death, living) == expected, name


def test_eras_come_back_in_chronological_order():
    assert eras_for_composer(1885, 1944) == ['romantic', 'modern']
    assert eras_for_composer(1560, 1620) == ['renaissance', 'baroque']


def test_undated_composer_gets_no_eras():
    assert eras_for_composer(None, None) == []


# --- seams -------------------------------------------------------------------

def test_seam_overlap_grants_both_eras():
    """The 20-year overlaps are the over-inclusive principle in action: a composer
    active only inside a seam belongs to both eras that share it."""
    # Active 1590-1595, inside the Renaissance/Baroque seam (1580-1600).
    assert eras_for_composer(1570, 1595) == ['renaissance', 'baroque']


def test_window_boundaries_are_inclusive():
    # A span touching a window by exactly one year still counts.
    renaissance_end = era_windows()[0][3]  # 1600
    assert 'renaissance' in eras_for_composer(renaissance_end - 20, renaissance_end)


def test_era_windows_clamps_the_open_ended_window_to_now():
    windows = {slug: (start, end) for slug, _, start, end in era_windows()}
    assert windows['21st-century'] == (2000, 2026)
    # Non-terminal windows are untouched.
    assert windows['baroque'] == (1580, 1750)


def test_windows_are_contiguous_with_no_gaps():
    """A composer active in any year from 1400 on must land in at least one era —
    a gap between windows would silently drop them."""
    windows = era_windows()
    for (_, label, _, end), (_, next_label, next_start, _) in zip(windows, windows[1:]):
        assert next_start <= end, f'gap between {label} and {next_label}'


# --- implied_birth_range (drives the UI's conflict explanation) ---------------

def test_implied_birth_range_is_the_inverse_of_the_derivation():
    lo, hi = implied_birth_range('baroque')
    # Someone born at either end of the implied range really does get the era back.
    assert 'baroque' in eras_for_composer(lo, lo + 75)
    assert 'baroque' in eras_for_composer(hi, hi + 75)


def test_implied_birth_range_brackets_a_known_composer():
    lo, hi = implied_birth_range('romantic')
    assert lo <= 1885 <= hi  # Barrios is Romantic, so his birth year must fall inside


def test_implied_birth_range_of_unknown_era_is_none():
    assert implied_birth_range('bogus') is None


# --- parse_era_filter --------------------------------------------------------

def test_parse_era_filter_reads_csv():
    assert parse_era_filter('romantic,modern') == ['romantic', 'modern']


def test_parse_era_filter_tolerates_whitespace_and_case():
    assert parse_era_filter(' Romantic , MODERN ') == ['romantic', 'modern']


def test_parse_era_filter_drops_unknown_slugs():
    assert parse_era_filter('romantic,bogus') == ['romantic']


def test_parse_era_filter_dedupes_preserving_order():
    assert parse_era_filter('modern,romantic,modern') == ['modern', 'romantic']


def test_parse_era_filter_of_empty_input():
    assert parse_era_filter('') == []
    assert parse_era_filter(None) == []
    assert parse_era_filter('bogus') == []
