"""Filter param contract — pins the exact query-param names the frontend sends."""
import pytest

from music.models import ComposerEra

from .factories import ComposerFactory, WorkFactory, CountryFactory

pytestmark = pytest.mark.django_db


def test_composer_country_name_filter(api):
    spain = CountryFactory(name='Spain')
    france = CountryFactory(name='France')
    ComposerFactory(full_name='Spanish One', last_name='Uno', country=spain)
    ComposerFactory(full_name='French One', last_name='Deux', country=france)

    res = api.get('/api/composers/', {'country_name': 'Spain'})
    names = [c['full_name'] for c in res.data['results']]
    assert 'Spanish One' in names
    assert 'French One' not in names


def test_composer_birth_year_range_filter(api):
    ComposerFactory(full_name='Old Master', last_name='Old', birth_year=1700)
    ComposerFactory(full_name='Romantic', last_name='Mid', birth_year=1850)

    res = api.get('/api/composers/', {'birth_year_min': 1800, 'birth_year_max': 1900})
    names = [c['full_name'] for c in res.data['results']]
    assert 'Romantic' in names
    assert 'Old Master' not in names


def test_works_composer_country_and_birth_year_contract(api):
    spain = CountryFactory(name='Spain')
    france = CountryFactory(name='France')
    spanish = ComposerFactory(last_name='Sp', country=spain, birth_year=1852)
    french = ComposerFactory(last_name='Fr', country=france, birth_year=1700)
    WorkFactory(title='Spanish Work', composer=spanish)
    WorkFactory(title='French Work', composer=french)

    res = api.get('/api/works/', {
        'composer_country': 'Spain',
        'composer_birth_year_min': 1800,
        'composer_birth_year_max': 1900,
    })
    titles = [w['title'] for w in res.data['results']]
    assert 'Spanish Work' in titles
    assert 'French Work' not in titles


def test_composer_eras_filter(api):
    # Era tags are materialised by the post_save signal, so these are real rows.
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)
    ComposerFactory(full_name='Dowland', last_name='D', birth_year=1563, death_year=1626)

    res = api.get('/api/composers/', {'eras': 'baroque'})
    names = [c['full_name'] for c in res.data['results']]
    assert 'Dowland' in names
    assert 'Barrios' not in names


def test_composer_eras_filter_ors_within_the_param(api):
    """Selecting two eras means either, not both — the encompassing reading."""
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)
    ComposerFactory(full_name='Dowland', last_name='D', birth_year=1563, death_year=1626)
    ComposerFactory(full_name='Brouwer', last_name='Br', birth_year=1939, is_living=True)

    res = api.get('/api/composers/', {'eras': 'baroque,21st-century'})
    names = [c['full_name'] for c in res.data['results']]
    assert 'Dowland' in names
    assert 'Brouwer' in names
    assert 'Barrios' not in names


def test_composer_eras_filter_returns_each_composer_once(api):
    """Barrios matches both selected eras; the join must not duplicate his row."""
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)

    res = api.get('/api/composers/', {'eras': 'romantic,modern'})
    names = [c['full_name'] for c in res.data['results']]
    assert names.count('Barrios') == 1


def test_composer_eras_and_birth_year_range_intersect(api):
    """The two filters compose with AND — era tags and the birth-year slider are
    different views of one axis, and this is the conflict the UI has to explain."""
    ComposerFactory(full_name='Early Romantic', last_name='E', birth_year=1800, death_year=1860)
    ComposerFactory(full_name='Late Romantic', last_name='L', birth_year=1880, death_year=1940)

    res = api.get('/api/composers/', {'eras': 'romantic', 'birth_year_min': 1870})
    names = [c['full_name'] for c in res.data['results']]
    assert 'Late Romantic' in names
    assert 'Early Romantic' not in names

    # A genuinely contradictory pair is empty, not an error.
    res = api.get('/api/composers/', {'eras': 'baroque', 'birth_year_min': 1900})
    assert res.status_code == 200
    assert res.data['count'] == 0


def test_composer_eras_unknown_slug_is_ignored(api):
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)

    res = api.get('/api/composers/', {'eras': 'romantic,bogus'})
    assert [c['full_name'] for c in res.data['results']] == ['Barrios']


def test_composer_eras_all_junk_matches_nothing(api):
    """A filter we can't parse returns no composers, not every composer — same rule
    as an unrecognised ?instrumentation= term."""
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)

    res = api.get('/api/composers/', {'eras': 'bogus'})
    assert res.data['count'] == 0


def test_composer_eras_absent_param_does_not_filter(api):
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)
    ComposerFactory(full_name='Undated', last_name='U', birth_year=None)

    res = api.get('/api/composers/')
    names = [c['full_name'] for c in res.data['results']]
    assert {'Barrios', 'Undated'} <= set(names)


def test_era_facets_count_per_era(api):
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)
    ComposerFactory(full_name='Dowland', last_name='D', birth_year=1563, death_year=1626)

    res = api.get('/api/composers/era_facets/')
    facets = {f['slug']: f['count'] for f in res.data}
    assert facets['romantic'] == 1      # Barrios
    assert facets['modern'] == 1        # Barrios
    assert facets['baroque'] == 1       # Dowland
    assert facets['renaissance'] == 1   # Dowland
    assert facets['classical'] == 0


def test_era_facets_include_labels_and_windows(api):
    res = api.get('/api/composers/era_facets/')
    baroque = next(f for f in res.data if f['slug'] == 'baroque')
    assert baroque['label'] == 'Baroque'
    assert baroque['start_year'] == 1580
    assert baroque['end_year'] == 1750


def test_era_facets_include_implied_birth_range(api):
    """Served, not computed client-side, so the age constants live in one place —
    the UI needs them for 'widen birth years to match Baroque'."""
    res = api.get('/api/composers/era_facets/')
    baroque = next(f for f in res.data if f['slug'] == 'baroque')
    assert baroque['implied_birth_min'] == 1580 - 75   # died at the window's open
    assert baroque['implied_birth_max'] == 1750 - 20   # came of age as it closed

    # And the range really does bracket a composer the era filter returns.
    composer = ComposerFactory(full_name='Baroque One', last_name='B',
                               birth_year=1600, death_year=1660)
    assert baroque['implied_birth_min'] <= composer.birth_year <= baroque['implied_birth_max']


def test_era_facets_respect_other_filters(api):
    spain = CountryFactory(name='Spain')
    france = CountryFactory(name='France')
    ComposerFactory(full_name='Spanish Romantic', last_name='S', country=spain,
                    birth_year=1885, death_year=1944)
    ComposerFactory(full_name='French Romantic', last_name='F', country=france,
                    birth_year=1885, death_year=1944)

    res = api.get('/api/composers/era_facets/', {'country_name': 'Spain'})
    facets = {f['slug']: f['count'] for f in res.data}
    assert facets['romantic'] == 1  # not 2 — the country filter applies


def test_era_facets_exclude_their_own_filter(api):
    """The classic facet bug: if the era filter applied to its own counts, picking
    Romantic would show every other era as (0) and the chips would be unusable."""
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)
    ComposerFactory(full_name='Dowland', last_name='D', birth_year=1563, death_year=1626)

    res = api.get('/api/composers/era_facets/', {'eras': 'romantic'})
    facets = {f['slug']: f['count'] for f in res.data}
    assert facets['baroque'] == 1, 'era selection wrongly narrowed its own facet counts'
    assert facets['romantic'] == 1


def test_era_facets_show_zero_for_a_conflicting_birth_range(api):
    """The count that lets the UI dim a chip instead of showing an empty table."""
    ComposerFactory(full_name='Barrios', last_name='B', birth_year=1885, death_year=1944)

    res = api.get('/api/composers/era_facets/', {'birth_year_min': 1900})
    facets = {f['slug']: f['count'] for f in res.data}
    assert facets['baroque'] == 0
    assert facets['romantic'] == 0


def test_works_composer_eras_contract(api):
    barrios = ComposerFactory(last_name='B', birth_year=1885, death_year=1944)
    dowland = ComposerFactory(last_name='D', birth_year=1563, death_year=1626)
    WorkFactory(title='Romantic Work', composer=barrios)
    WorkFactory(title='Baroque Work', composer=dowland)

    res = api.get('/api/works/', {'composer_eras': 'baroque'})
    titles = [w['title'] for w in res.data['results']]
    assert 'Baroque Work' in titles
    assert 'Romantic Work' not in titles


def test_works_composer_eras_returns_each_work_once(api):
    barrios = ComposerFactory(last_name='B', birth_year=1885, death_year=1944)
    WorkFactory(title='Romantic Work', composer=barrios)

    res = api.get('/api/works/', {'composer_eras': 'romantic,modern'})
    titles = [w['title'] for w in res.data['results']]
    assert titles.count('Romantic Work') == 1


def test_manual_era_tag_is_filterable(api):
    """An admin override participates in search exactly like a derived tag."""
    composer = ComposerFactory(full_name='Neo Baroque', last_name='N', birth_year=1950,
                               is_living=True)
    ComposerEra.objects.create(composer=composer, era='baroque', basis='manual')

    res = api.get('/api/composers/', {'eras': 'baroque'})
    assert [c['full_name'] for c in res.data['results']] == ['Neo Baroque']


def test_works_combined_year_filter_falls_back_to_composition_year(api):
    """year_min/year_max match composer birth year, falling back to composition
    year only when the composer has no birth year on record."""
    no_birth = ComposerFactory(last_name='NoDob', birth_year=None)
    born_1850 = ComposerFactory(last_name='Old', birth_year=1850)
    born_1950 = ComposerFactory(last_name='Living', birth_year=1950)

    # Included via composition-year fallback (composer birth year unknown).
    WorkFactory(title='Fallback Hit', composer=no_birth, composition_year=2006)
    # Excluded: composer born 1850 is primary; 2006 composition year is ignored.
    WorkFactory(title='Birth Year Wins', composer=born_1850, composition_year=2006)
    # Included on birth year even though composed long before the range.
    WorkFactory(title='Birth In Range', composer=born_1950, composition_year=1600)
    # Excluded: fallback composition year out of range.
    WorkFactory(title='Fallback Miss', composer=no_birth, composition_year=1600)

    res = api.get('/api/works/', {'year_min': 1900, 'year_max': 2007})
    titles = [w['title'] for w in res.data['results']]
    assert 'Fallback Hit' in titles
    assert 'Birth In Range' in titles
    assert 'Birth Year Wins' not in titles
    assert 'Fallback Miss' not in titles
