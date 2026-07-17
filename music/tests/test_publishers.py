"""The score-link source rules: what's admissible, and what CTA it earns.

Two separate rules, and the tests are split accordingly — conflating them is the mistake
this module exists to prevent:
  - admission is `is_blocked` (rehosting sites only)
  - naming is `resolve_link` (an allowlist, which does NOT gate admission)
"""
import pytest

from music.publishers import cta_for, is_allowed, is_blocked, resolve_link


@pytest.mark.parametrize('url, expected_source', [
    ('https://imslp.org/wiki/Violin_Partita_No.2', 'IMSLP'),
    ('https://s9.imslp.org/files/x/score.pdf', 'IMSLP'),          # subdomain
    ('https://IMSLP.org/wiki/X', 'IMSLP'),                        # case
    ('https://www.mutopiaproject.org/x', 'Mutopia Project'),
    ('https://gallica.bnf.fr/ark:/12148/xyz', 'Gallica (BnF)'),
])
def test_free_sources_earn_view_score(url, expected_source):
    link_type, source = resolve_link(url)
    assert link_type == 'score'
    assert source == expected_source
    assert cta_for(link_type) == 'View Score'


@pytest.mark.parametrize('url, expected_source', [
    ('https://www.henle.de/en/detail/?Titel=123', 'G. Henle Verlag'),
    ('https://www.baerenreiter.com/x', 'Bärenreiter'),
    ('https://www.schott-music.com/x', 'Schott Music'),
    ('https://www.prestomusic.com/x', 'Presto Music'),
])
def test_paid_sources_earn_buy_score(url, expected_source):
    link_type, source = resolve_link(url)
    assert link_type == 'purchase'
    assert source == expected_source
    assert cta_for(link_type) == 'Buy Score'


def test_sheerpluck_keeps_its_own_cta():
    """66,673 works carry a SheerPluck link and it hosts no arrangements — it must not
    get swept into the generic score naming."""
    assert resolve_link('https://www.sheerpluck.de/work/123') == ('sheerpluck', 'SheerPluck')
    assert cta_for('sheerpluck') == 'View on SheerPluck'


@pytest.mark.parametrize('url', [
    'https://www.scribd.com/doc/123',
    'https://pdfcoffee.com/x',
    'https://cdn.scribd.com/x.pdf',   # subdomain
])
def test_rehosting_sites_are_refused(url):
    assert is_blocked(url)
    assert not is_allowed(url)
    assert resolve_link(url) is None


def test_unrecognised_host_is_allowed_but_earns_no_cta():
    """The allowlist names links; it does not gate them.

    Default-deny was tried and reverted: it rejects an arranger hosting their own edition
    (unbounded hosts, and one of the most legitimate sources there is) and the BCGS
    commission links already in the catalog.
    """
    url = 'https://some-arranger.example.com/my-edition.pdf'
    assert not is_blocked(url)
    assert is_allowed(url)
    assert resolve_link(url) is None                       # no derived CTA...
    assert cta_for('other', 'My Edition') == 'My Edition'  # ...keeps its author's label


def test_lookalike_host_does_not_match():
    """`notimslp.org` endswith `imslp.org`. A naive suffix check would trust it."""
    assert resolve_link('https://notimslp.org/fake') is None


@pytest.mark.parametrize('url', ['', None, 'zzzznonsense', 'not a url at all'])
def test_unparseable_urls_are_blocked_not_crashed(url):
    """If we can't tell what host it points at, we can't vouch for it."""
    assert is_blocked(url)
    assert resolve_link(url) is None
