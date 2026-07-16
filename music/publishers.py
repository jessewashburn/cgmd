"""Score-link sources: what's admissible, and the CTA each source earns.

Two *separate* rules. Conflating them is the mistake to avoid:

1. **Admission — the blocklist (`is_blocked`).** Sites that rehost other people's PDFs
   (Scribd, PDFCoffee, …) are refused everywhere. This is the hard rule.

   It is deliberately NOT "reject anything not on the allowlist". Default-deny was tried
   and reverted: it would reject **arranger self-hosting** — a composer or arranger
   putting their own edition on their own site, which is one of the *most* legitimate
   sources there is and lives on an unbounded set of hosts — and it would also refuse the
   BCGS commission links already in the catalog. An unknown host is not evidence of a bad
   host.

2. **Naming — the allowlist (`resolve_link`).** The call-to-action is *derived from the
   host*, never authored, which is what stops a hundred bespoke labels accumulating
   ("Get it from Henle", "Bärenreiter shop", "PDF here"). A recognised free source earns
   "View Score", a paid one "Buy Score". An unrecognised (but unblocked) host earns no
   CTA of its own and keeps whatever label its author gave it.

Call `is_blocked()` from *every* write path — model clean(), admin, and the suggestion
apply path. That last one is not optional: `alternate-work-instrumentations` shipped a
resolver that validated only the direct write path, and junk arrived through suggestions
instead. There is a test pinning the suggestion path specifically.
"""

from urllib.parse import urlparse

# Free-to-view sources. IMSLP and the national libraries host public-domain scans; the
# rest are open-licence typesetting projects.
FREE_SOURCES = {
    'imslp.org': 'IMSLP',
    'petrucci.mus.auth.gr': 'IMSLP',          # long-standing IMSLP mirror
    'mutopiaproject.org': 'Mutopia Project',
    'musopen.org': 'Musopen',
    'gallica.bnf.fr': 'Gallica (BnF)',
    'bdh.bne.es': 'Biblioteca Digital Hispánica',
    'bdh-rd.bne.es': 'Biblioteca Digital Hispánica',
    'digitale-sammlungen.de': 'Münchener DigitalisierungsZentrum',
    'mdz-nbn-resolving.de': 'Münchener DigitalisierungsZentrum',
    'kb.dk': 'Danish Royal Library',
    'rism.online': 'RISM',
    'opac.rism.info': 'RISM',
    'loc.gov': 'Library of Congress',
}

# Paid sources: publishers and the retailers that carry them.
PAID_SOURCES = {
    'boosey.com': 'Boosey & Hawkes',
    'baerenreiter.com': 'Bärenreiter',
    'henle.de': 'G. Henle Verlag',
    'schott-music.com': 'Schott Music',
    'universaledition.com': 'Universal Edition',
    'editionpeters.com': 'Edition Peters',
    'edition-peters.com': 'Edition Peters',
    'ricordi.com': 'Ricordi',
    'durand-salabert-eschig.com': 'Durand-Salabert-Eschig',
    'chesternovello.com': 'Chester Music',
    'halleonard.com': 'Hal Leonard',
    'doblinger-musikverlag.at': 'Doblinger',
    'breitkopf.com': 'Breitkopf & Härtel',
    'global.oup.com': 'Oxford University Press',
    'fabermusic.com': 'Faber Music',
    'editionsorphee.com': 'Editions Orphée',
    'productionsdoz.com': "Les Productions d'OZ",
    'chanterelle.com': 'Chanterelle',
    'gspguitar.com': 'Guitar Solo Publications',
    'melbay.com': 'Mel Bay',
    'bergmanneditions.com': 'Bergmann Edition',
    'wernerguitareditions.com': 'Werner Guitar Editions',
    'tuscanypublications.com': 'Tuscany Publications',
    'berben.it': 'Berben',
    'esz.it': 'Edizioni Suvini Zerboni',
    'unionmusicalediciones.es': 'Unión Musical Ediciones',
    'boileau-music.com': 'Editorial de Música Boileau',
    'prestomusic.com': 'Presto Music',
    'sheetmusicplus.com': 'Sheet Music Plus',
    'musicroom.com': 'Musicroom',
    'stretta-music.com': 'Stretta Music',
    'jwpepper.com': 'JW Pepper',
    'classicalvocalreprints.com': 'Classical Vocal Reprints',
    'tfront.com': 'Theodore Front Musical Literature',
}

# Not score sources, but they own their own CTA and must not be mistaken for one.
SPECIAL_SOURCES = {
    'sheerpluck.de': ('sheerpluck', 'SheerPluck'),
    'sheerpluck.org': ('sheerpluck', 'SheerPluck'),
    'youtube.com': ('youtube', 'YouTube'),
    'youtu.be': ('youtube', 'YouTube'),
}

# Rehosting aggregators — refused everywhere. This is the admission rule; everything not
# listed here is allowed in, and simply may not earn a derived CTA.
BLOCKED_SOURCES = {
    'scribd.com', 'pdfcoffee.com', 'vdocuments.net', 'dokumen.pub',
    'idoc.pub', 'coursehero.com', 'studylib.net', '4shared.com',
}

# Derived CTA per link type. `label` on a WorkLink is not consulted for these.
LINK_TYPE_CTA = {
    'score': 'View Score',
    'purchase': 'Buy Score',
    'imslp': 'View Score',
    'sheerpluck': 'View on SheerPluck',
    'youtube': 'Watch on YouTube',
}


def _host(url):
    try:
        netloc = urlparse(url).netloc.lower()
    except (ValueError, AttributeError):
        return None
    if not netloc:
        return None
    if '@' in netloc:          # strip any userinfo
        netloc = netloc.rsplit('@', 1)[1]
    netloc = netloc.split(':')[0]
    return netloc[4:] if netloc.startswith('www.') else netloc


def _matches(host, key):
    """`imslp.org` and `s9.imslp.org` are both IMSLP, but `notimslp.org` is not — which
    is why this is not a naive endswith."""
    return host == key or host.endswith('.' + key)


def _lookup(host, table):
    """Exact or subdomain match against a {host: value} table."""
    if host in table:
        return table[host]
    for key, value in table.items():
        if _matches(host, key):
            return value
    return None


def is_blocked(url):
    """True for a rehosting site we refuse to link to. The admission rule.

    A URL we can't parse at all counts as blocked: if we can't tell what host it points
    at, we can't vouch for it.
    """
    host = _host(url)
    if not host:
        return True
    return any(_matches(host, blocked) for blocked in BLOCKED_SOURCES)


def resolve_link(url):
    """Map a URL to (link_type, source_name), or None if the host isn't a known source.

    None means "no derived CTA" — NOT "reject". Admission is `is_blocked`'s job. An
    arranger hosting their own edition is a perfectly good link that will never be on any
    allowlist; it just keeps its author's label instead of earning "View Score".

    Never invent a fallback bucket here. `alternate-work-instrumentations` shipped a
    resolver that bucketed junk into a real category ('Other'), which let "zzzznonsense"
    render as a real value.
    """
    host = _host(url)
    if not host or is_blocked(url):
        return None

    special = _lookup(host, SPECIAL_SOURCES)
    if special:
        return special

    free = _lookup(host, FREE_SOURCES)
    if free:
        return 'score', free

    paid = _lookup(host, PAID_SOURCES)
    if paid:
        return 'purchase', paid

    return None


def is_allowed(url):
    """True when the URL may be stored at all (i.e. it isn't a blocked rehosting site)."""
    return not is_blocked(url)


def cta_for(link_type, fallback=''):
    """The display verb for a link type; `fallback` (the stored label) for the rest."""
    return LINK_TYPE_CTA.get(link_type, fallback)
