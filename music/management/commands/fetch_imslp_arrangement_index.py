"""Crawl IMSLP's guitar-arrangement categories into a committed CSV snapshot.

This command does the *network* half of the arrangements import; `import_imslp_arrangements`
does the *database* half by reading the CSV this writes. The split is deliberate:

- The crawl is ~4,200 page fetches at a polite delay — roughly half an hour. Doing that on
  every seed is slow, impolite, and non-reproducible (IMSLP mutates, so two runs a month
  apart would silently seed different catalogs).
- The CSV is committed, so the import is offline, fast, deterministic, reviewable in a PR
  diff, and runnable in CI/E2E. This mirrors the existing `data/imslp_guitar_data.csv`.

What a row is
-------------
A page in `Category:For guitar (arr)` is NOT a guitar piece — it is the ORIGINAL work,
hosting guitar arrangements as files. "Violin Partita No.2, BWV 1004 (Bach)" carries three
(Apke, Jacquot, Kuokkanen); the Cello Suite No.1 carries five. So one page = one row here
and one Work row later, never one per arranger.

`arrangement_count` is the admission gate: a page with no linkable guitar arrangement earns
no row. `arrangers` is recorded for review only — it is deliberately not imported, because
it is multi-valued per page and we don't filter by it.
"""

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from django.core.management.base import BaseCommand

API = 'https://imslp.org/api.php'
PAGE = 'https://imslp.org/wiki/'
UA = 'solmu-cgmd/1.0 (+https://github.com/; classical guitar catalog; contact via repo)'
DEFAULT_OUT = 'data/imslp_arrangements.csv'

# The six guitar-arrangement categories, mapped onto the catalog's existing
# InstrumentationCategory names. No new vocabulary is needed — all six already exist.
#
# A page can sit in MORE THAN ONE of these: the six category listings total 4,425 but
# resolve to 4,232 distinct pages, so ~193 works have (say) both a solo and a duo
# arrangement. Order matters below — it is the precedence used to pick the row's *primary*
# instrumentation, smallest force first, because a solo guitar arrangement is the one a
# guitarist is most likely looking for. The rest become WorkInstrumentation alternates.
CATEGORY_MAP = {
    'For guitar (arr)': 'Solo',
    'For 2 guitars (arr)': 'Duo',
    'For 3 guitars (arr)': 'Trio',
    'For 4 guitars (arr)': 'Quartet',
    'For voice, guitar (arr)': 'Guitar and Voice',
    'For guitar, piano (arr)': 'Guitar and Piano',
}
CATEGORY_PRECEDENCE = list(CATEGORY_MAP)

# "Title (Composer, Forename)" — IMSLP's page-title convention.
TITLE_RE = re.compile(r'^(.*?)\s*\(([^()]*,[^()]*)\)$')

# Arrangement section headers: "For Guitar (Apke)", "For 2 Guitars (Smith)". The category
# backlink "For guitar (arr)" matches this shape too, so it is excluded explicitly —
# without that, every page would look like it had an arrangement and the gate would pass
# everything.
ARR_RE = re.compile(r'For\s+(\d+\s+)?Guitars?\s*\(([^)<]{1,60})\)', re.I)

FIELDNAMES = [
    'imslp_title', 'composer_name', 'work_title', 'source_category',
    'instrumentation_category', 'alternate_instrumentations',
    'url', 'arrangement_count', 'arrangers',
]


class Command(BaseCommand):
    help = "Crawl IMSLP's guitar-arrangement categories into data/imslp_arrangements.csv"

    def add_arguments(self, parser):
        parser.add_argument('--out', default=DEFAULT_OUT)
        parser.add_argument('--delay', type=float, default=0.4,
                            help='Politeness delay between page fetches (seconds)')
        parser.add_argument('--limit', type=int, default=0,
                            help='Stop after N pages (0 = all). For smoke-testing.')
        parser.add_argument('--index-only', action='store_true',
                            help='Enumerate categories but skip page fetches (no gate data)')
        parser.add_argument('--resume', action='store_true',
                            help='Keep rows already in --out and only fetch the missing pages')

    # ---------- network ----------

    def _get(self, url, retries=3):
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=45) as r:
                    return r.read().decode('utf-8', 'ignore')
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return None
                if attempt == retries - 1:
                    raise
            except Exception:
                if attempt == retries - 1:
                    return None
            time.sleep(2 * (attempt + 1))
        return None

    def _members(self, category):
        """Every page in a category, via the MediaWiki API (500 at a time)."""
        out, cont = [], None
        while True:
            params = {
                'action': 'query', 'list': 'categorymembers',
                'cmtitle': 'Category:' + category, 'cmlimit': '500', 'format': 'json',
            }
            if cont:
                params['cmcontinue'] = cont
            body = self._get(API + '?' + urllib.parse.urlencode(params))
            if not body:
                break
            data = json.loads(body)
            out += [m['title'] for m in data.get('query', {}).get('categorymembers', [])]
            cont = (data.get('query-continue', {})
                        .get('categorymembers', {}).get('cmcontinue'))
            if not cont:
                break
            time.sleep(0.3)
        return out

    @staticmethod
    def page_url(title):
        """IMSLP's canonical URL form: comma percent-encoded, parentheses left literal.

        `safe='()'` is not cosmetic. The catalog's 6,572 existing imslp_url values were
        written in exactly this form — `..._(Sanz%2C_Gaspar)` — and quote()'s default
        encodes the parens to %28/%29, producing a different string for the same page.
        The importer keys on this URL, so the mismatch silently turned every retro-tag
        into a duplicate work. Match IMSLP, and match what's already stored.
        """
        return PAGE + urllib.parse.quote(title.replace(' ', '_'), safe='()')

    @staticmethod
    def parse_arrangers(html):
        """Distinct guitar arrangers named on the page, excluding the category backlink."""
        found = []
        for count, who in ARR_RE.findall(html):
            who = who.strip()
            if who.lower() == 'arr':          # the "For guitar (arr)" category link
                continue
            label = f"{count.strip()} {who}".strip() if count.strip() else who
            if label not in found:
                found.append(label)
        return found

    # ---------- main ----------

    def handle(self, *args, **opts):
        out_path, delay = opts['out'], opts['delay']

        existing = {}
        if opts['resume']:
            try:
                with open(out_path, newline='', encoding='utf-8') as fh:
                    for row in csv.DictReader(fh):
                        existing[row['imslp_title']] = row
                self.stdout.write(f'Resuming: {len(existing)} rows already in {out_path}')
            except FileNotFoundError:
                pass

        self.stdout.write('Enumerating categories via the MediaWiki API...')
        # title -> [categories]. A list, not a scalar: a page can be in several, and
        # overwriting would silently pick whichever iterated last.
        pages = {}
        total_memberships = 0
        for category in CATEGORY_MAP:
            members = self._members(category)
            total_memberships += len(members)
            for title in members:
                pages.setdefault(title, []).append(category)
            self.stdout.write(f'  {category:<26} {len(members):>5}')
            time.sleep(0.3)
        multi = sum(1 for cats in pages.values() if len(cats) > 1)
        self.stdout.write(self.style.SUCCESS(
            f'{len(pages)} distinct pages from {total_memberships} memberships '
            f'({multi} in more than one category)'))

        titles = sorted(pages)
        if opts['limit']:
            titles = titles[:opts['limit']]

        rows, skipped_unparseable, fetched = [], 0, 0
        for i, title in enumerate(titles, 1):
            cats = sorted(pages[title], key=CATEGORY_PRECEDENCE.index)
            category = cats[0]
            m = TITLE_RE.match(title)
            if not m:
                # No composer in the title -> we cannot attribute the work. Skip rather
                # than guess; guessing is how a Chaconne ends up filed under Erik Bach.
                skipped_unparseable += 1
                continue
            work_title, composer_name = m.group(1).strip(), m.group(2).strip()

            if title in existing:
                rows.append(existing[title])
                continue

            arrangers, count = [], ''
            if not opts['index_only']:
                html = self._get(self.page_url(title))
                fetched += 1
                if html:
                    arrangers = self.parse_arrangers(html)
                count = len(arrangers)
                time.sleep(delay)

            rows.append({
                'imslp_title': title,
                'composer_name': composer_name,
                'work_title': work_title,
                'source_category': category,
                'instrumentation_category': CATEGORY_MAP[category],
                # Extra realizations of the same work (solo *and* duo arrangements).
                # These become WorkInstrumentation alternates, which is precisely the
                # shape that feature already exists for.
                'alternate_instrumentations': ' | '.join(
                    CATEGORY_MAP[c] for c in cats[1:]),
                'url': self.page_url(title),
                'arrangement_count': count,
                'arrangers': ' | '.join(arrangers),
            })

            if i % 100 == 0:
                self.stdout.write(f'  {i}/{len(titles)} ({fetched} fetched)')
                self._write(out_path, rows)   # checkpoint; the crawl is ~30 min

        self._write(out_path, rows)
        with_arr = sum(1 for r in rows if str(r['arrangement_count']).isdigit()
                       and int(r['arrangement_count']) > 0)
        self.stdout.write(self.style.SUCCESS(
            f'\nWrote {len(rows)} rows -> {out_path}\n'
            f'  with >=1 guitar arrangement (would earn a row): {with_arr}\n'
            f'  skipped, unparseable title: {skipped_unparseable}'))

    @staticmethod
    def _write(path, rows):
        with open(path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
