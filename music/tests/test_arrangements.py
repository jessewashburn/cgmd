"""The arrangement flag: filtering it, suggesting it, and importing it."""
import csv

import pytest
from django.core.management import call_command

from music.models import Composer, InstrumentationCategory, Work, WorkInstrumentation
from .factories import ComposerFactory, InstrumentationCategoryFactory, WorkFactory

pytestmark = pytest.mark.django_db


# --------------------------------------------------------------------------
# Filtering
# --------------------------------------------------------------------------

def test_default_request_includes_arrangements(api):
    """No param = everything. The checkbox is on by default and sends nothing, so a
    plain /works/ must not quietly hide half the catalog."""
    composer = ComposerFactory(full_name='Filter Comp', last_name='FilterComp')
    WorkFactory(title='Zzz Original', composer=composer, is_arrangement=False)
    WorkFactory(title='Zzz Arranged', composer=composer, is_arrangement=True)

    titles = [w['title'] for w in api.get('/api/works/', {'search': 'Zzz'}).data['results']]
    assert 'Zzz Original' in titles
    assert 'Zzz Arranged' in titles


def test_is_arrangement_false_excludes_them(api):
    composer = ComposerFactory(full_name='Filter Comp2', last_name='FilterComp2')
    WorkFactory(title='Yyy Original', composer=composer, is_arrangement=False)
    WorkFactory(title='Yyy Arranged', composer=composer, is_arrangement=True)

    res = api.get('/api/works/', {'search': 'Yyy', 'is_arrangement': 'false'})
    titles = [w['title'] for w in res.data['results']]
    assert titles == ['Yyy Original']


def test_is_arrangement_true_returns_only_arrangements(api):
    """The UI never sends this, but the API supports it; keep it honest."""
    composer = ComposerFactory(full_name='Filter Comp3', last_name='FilterComp3')
    WorkFactory(title='Xxx Original', composer=composer, is_arrangement=False)
    WorkFactory(title='Xxx Arranged', composer=composer, is_arrangement=True)

    res = api.get('/api/works/', {'search': 'Xxx', 'is_arrangement': 'true'})
    assert [w['title'] for w in res.data['results']] == ['Xxx Arranged']


def test_junk_filter_value_degrades_to_no_filter(api):
    """A hand-edited ?is_arrangement=banana should not 500 or empty the page."""
    composer = ComposerFactory(full_name='Filter Comp4', last_name='FilterComp4')
    WorkFactory(title='Www Original', composer=composer, is_arrangement=False)
    WorkFactory(title='Www Arranged', composer=composer, is_arrangement=True)

    res = api.get('/api/works/', {'search': 'Www', 'is_arrangement': 'banana'})
    assert res.status_code == 200
    assert len(res.data['results']) == 2


def test_filtering_does_not_break_instrumentation_sort_or_count(api):
    """The filter is a plain WHERE on an indexed boolean precisely so it adds no join.

    A join here would duplicate rows under ORDER BY instrumentation_category__name and
    inflate the paginated count — the exact failure works-column-sort-ordering-fix exists
    for.
    """
    composer = ComposerFactory(full_name='Sort Comp', last_name='SortComp')
    solo = InstrumentationCategoryFactory(name='Solo')
    duo = InstrumentationCategoryFactory(name='Duo')
    for i, cat in enumerate([solo, duo, solo]):
        WorkFactory(title=f'Vvv Work {i}', composer=composer,
                    instrumentation_category=cat, is_arrangement=True)
        # An alternate realization: the multi-valued relation that a naive join
        # would fan out over.
        WorkInstrumentation.objects.create(
            work=Work.objects.get(title=f'Vvv Work {i}'), category=duo if cat == solo else solo,
            basis='derived')

    res = api.get('/api/works/', {
        'search': 'Vvv', 'is_arrangement': 'true',
        'ordering': 'instrumentation_category__name',
    })
    titles = [w['title'] for w in res.data['results']]
    assert res.data['count'] == 3, 'count inflated — the filter added a join'
    assert len(titles) == len(set(titles)) == 3, 'rows duplicated by the sort'


# --------------------------------------------------------------------------
# Suggestions
# --------------------------------------------------------------------------

def _edit_work_suggestion(work, **suggested):
    from music.models import UserSuggestion
    return UserSuggestion.objects.create(
        suggestion_type='edit_work', title='edit', description='',
        related_work=work, suggested_data=suggested,
    )


def test_suggested_arrangement_lands_as_suggested_not_derived():
    """Applying a suggestion must mark basis='suggested' so the IMSLP importer, which
    only rewrites 'derived' rows, can never overwrite a human's call."""
    from music.suggestion_apply import apply_suggestion

    work = WorkFactory(title='Suggest Me', is_arrangement=False)
    suggestion = _edit_work_suggestion(work, is_arrangement=True)

    result = apply_suggestion(suggestion)

    work.refresh_from_db()
    assert work.is_arrangement is True
    assert work.arrangement_basis == 'suggested'
    assert 'is_arrangement' in result['fields_updated']


def test_suggestion_path_refuses_a_rehosted_link():
    """The public write path needs its own guard.

    alternate-work-instrumentations validated only the direct path and junk arrived
    through suggestions instead. This is that test, for links.
    """
    from music.suggestion_apply import apply_suggestion

    work = WorkFactory(title='Linky Work')
    suggestion = _edit_work_suggestion(work, links=[
        {'label': 'Pirated PDF', 'url': 'https://www.scribd.com/doc/999'},
        {'label': 'Buy it', 'url': 'https://www.henle.de/en/detail/?Titel=1'},
    ])

    result = apply_suggestion(suggestion)
    assert result['links_added'] == 1
    assert result['links_rejected'] == 1

    urls = list(work.links.values_list('url', flat=True))
    assert urls == ['https://www.henle.de/en/detail/?Titel=1']
    # The type is derived from the host, not from whatever the submitter claimed.
    assert work.links.get().link_type == 'purchase'


def test_suggested_link_on_an_unlisted_host_is_kept():
    """An arranger self-hosting their edition is legitimate and will never be on an
    allowlist. Only rehosting sites are refused."""
    from music.suggestion_apply import apply_suggestion

    work = WorkFactory(title='Self Hosted')
    suggestion = _edit_work_suggestion(work, links=[
        {'label': "Arranger's own edition", 'url': 'https://some-arranger.example.com/x.pdf'},
    ])

    result = apply_suggestion(suggestion)
    assert result['links_added'] == 1
    assert result['links_rejected'] == 0
    assert work.links.get().label == "Arranger's own edition"


# --------------------------------------------------------------------------
# Import command
# --------------------------------------------------------------------------

ROWS = [
    {
        'imslp_title': 'Cello Suite No.1, BWV 1007 (Bach, Johann Sebastian)',
        'composer_name': 'Bach, Johann Sebastian',
        'work_title': 'Cello Suite No.1, BWV 1007',
        'source_category': 'For guitar (arr)',
        'instrumentation_category': 'Solo',
        'alternate_instrumentations': 'Duo',
        'url': 'https://imslp.org/wiki/Cello_Suite_No.1',
        'arrangement_count': '5',
        'arrangers': 'Dada | Gazoni | Reyne | Shorter | Tavares',
    },
    {
        'imslp_title': 'No Arrangement Here (Prat, Domingo)',
        'composer_name': 'Prat, Domingo',
        'work_title': 'No Arrangement Here',
        'source_category': 'For guitar (arr)',
        'instrumentation_category': 'Solo',
        'alternate_instrumentations': '',
        'url': 'https://imslp.org/wiki/No_Arrangement_Here',
        'arrangement_count': '0',
        'arrangers': '',
    },
]


@pytest.fixture
def arrangements_csv(tmp_path):
    path = tmp_path / 'arr.csv'
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ROWS[0]))
        writer.writeheader()
        writer.writerows(ROWS)
    return str(path)


@pytest.fixture(autouse=True)
def _categories():
    for name in ('Solo', 'Duo', 'Other'):
        InstrumentationCategory.objects.get_or_create(name=name)


def test_import_creates_work_and_skips_pages_with_no_arrangement(arrangements_csv):
    call_command('import_imslp_arrangements', csv=arrangements_csv)

    work = Work.objects.get(title='Cello Suite No.1, BWV 1007')
    assert work.is_arrangement is True
    assert work.arrangement_basis == 'derived'
    assert work.instrumentation_category.name == 'Solo'
    assert work.composer.full_name == 'Bach, Johann Sebastian'

    # The admission criterion: no linkable guitar arrangement, no row.
    assert not Work.objects.filter(title='No Arrangement Here').exists()


def test_import_is_idempotent(arrangements_csv):
    call_command('import_imslp_arrangements', csv=arrangements_csv)
    call_command('import_imslp_arrangements', csv=arrangements_csv)

    assert Work.objects.filter(title='Cello Suite No.1, BWV 1007').count() == 1
    assert Composer.objects.filter(name_normalized='bach, johann sebastian').count() == 1


def test_import_dry_run_writes_nothing(arrangements_csv):
    call_command('import_imslp_arrangements', csv=arrangements_csv, dry_run=True)
    assert not Work.objects.filter(title='Cello Suite No.1, BWV 1007').exists()


def test_import_never_matches_a_namesake(arrangements_csv):
    """The catalog really contains `Bach, Erik`. A fuzzy match would file the Cello
    Suite under him. Composer resolution is exact-normalized-name only."""
    erik = ComposerFactory(full_name='Bach, Erik', last_name='Bach',
                           name_normalized='bach, erik')

    call_command('import_imslp_arrangements', csv=arrangements_csv)

    work = Work.objects.get(title='Cello Suite No.1, BWV 1007')
    assert work.composer_id != erik.id
    assert work.composer.full_name == 'Bach, Johann Sebastian'


def test_import_matches_an_existing_work_by_imslp_url_despite_a_suffixed_title(
        arrangements_csv):
    """The existing IMSLP corpus stores titles with the composer baked in —
    'Canarios (Sanz, Gaspar)' — so title matching would miss and duplicate. Identity is
    the page URL for exactly this reason."""
    composer = ComposerFactory(full_name='Bach, Johann Sebastian', last_name='Bach',
                               name_normalized='bach, johann sebastian')
    existing = WorkFactory(
        title='Cello Suite No.1, BWV 1007 (Bach, Johann Sebastian)',
        composer=composer,
        imslp_url='https://imslp.org/wiki/Cello_Suite_No.1',
        instrumentation_category=InstrumentationCategory.objects.get(name='Other'),
        is_arrangement=False,
    )

    call_command('import_imslp_arrangements', csv=arrangements_csv)

    assert Work.objects.filter(imslp_url='https://imslp.org/wiki/Cello_Suite_No.1').count() == 1
    existing.refresh_from_db()
    assert existing.is_arrangement is True          # retro-tagged
    assert existing.instrumentation_category.name == 'Solo'   # re-bucketed out of Other


def test_untouched_rows_are_taggable(arrangements_csv):
    """A pre-existing row must be retro-taggable.

    Regression test for a real bug: `arrangement_basis` defaulted to 'manual', and the
    importer skips 'manual' rows to protect human decisions — so every one of the 73k
    existing works looked hand-decided and the retro-tag silently did nothing to any of
    them. Blank means undecided; only an actual human ruling blocks the backfill.
    """
    composer = ComposerFactory(full_name='Bach, Johann Sebastian', last_name='Bach',
                               name_normalized='bach, johann sebastian')
    work = WorkFactory(title='Cello Suite No.1, BWV 1007', composer=composer,
                       imslp_url='https://imslp.org/wiki/Cello_Suite_No.1')
    assert work.arrangement_basis == '', 'default must mean "undecided", not "manual"'

    call_command('import_imslp_arrangements', csv=arrangements_csv)

    work.refresh_from_db()
    assert work.is_arrangement is True
    assert work.arrangement_basis == 'derived'


def test_import_never_overwrites_a_human_decision(arrangements_csv):
    """basis='manual'/'suggested' survives every backfill. This is what the field is for."""
    composer = ComposerFactory(full_name='Bach, Johann Sebastian', last_name='Bach',
                               name_normalized='bach, johann sebastian')
    work = WorkFactory(
        title='Cello Suite No.1, BWV 1007', composer=composer,
        imslp_url='https://imslp.org/wiki/Cello_Suite_No.1',
        is_arrangement=False, arrangement_basis='manual',
    )

    call_command('import_imslp_arrangements', csv=arrangements_csv)

    work.refresh_from_db()
    assert work.is_arrangement is False, 'a manual decision was overwritten by the backfill'
    assert work.arrangement_basis == 'manual'


def test_import_records_extra_realizations_as_alternates(arrangements_csv):
    """A page in both 'For guitar (arr)' and 'For 2 guitars (arr)' has a solo *and* a duo
    arrangement — WorkInstrumentation is exactly that shape."""
    call_command('import_imslp_arrangements', csv=arrangements_csv)

    work = Work.objects.get(title='Cello Suite No.1, BWV 1007')
    alts = [a.category.name for a in work.alternate_instrumentations.all()]
    assert alts == ['Duo']
    assert work.instrumentation_category.name == 'Solo'  # primary unchanged
