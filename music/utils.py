"""
Data cleaning and validation utilities for the Classical Guitar Music Database.
"""

import re
import unicodedata
from typing import Optional, Tuple


def normalize_name(name: str) -> str:
    """
    Normalize a name for search and comparison.
    Removes accents, converts to lowercase.
    """
    if not name:
        return ''
    # Normalize unicode (decompose accented characters)
    nfkd = unicodedata.normalize('NFKD', name)
    # Remove non-ASCII characters (accents)
    ascii_text = nfkd.encode('ASCII', 'ignore').decode('UTF-8')
    # Convert to lowercase
    return ascii_text.lower().strip()


def parse_composer_name(full_name: str) -> Tuple[str, str, str]:
    """
    Parse a composer's full name into first, last, and normalized form.
    
    Handles formats like:
    - "Last, First" (Sheerpluck format)
    - "First Last"
    - "First Middle Last"
    
    Returns: (first_name, last_name, full_name)
    """
    if not full_name:
        return ('', '', '')
    
    full_name = full_name.strip()
    
    # Handle "Last, First" format
    if ',' in full_name:
        parts = full_name.split(',', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ''
        # Reconstruct as "First Last"
        reconstructed = f"{first_name} {last_name}".strip()
        return (first_name, last_name, reconstructed)
    
    # Handle "First Last" or "First Middle Last" format
    name_parts = full_name.rsplit(' ', 1)
    if len(name_parts) == 2:
        first_name = name_parts[0].strip()
        last_name = name_parts[1].strip()
        return (first_name, last_name, full_name)
    
    # Single name (e.g., "Sting", "Prince")
    return ('', full_name, full_name)


def clean_year(year_value: any) -> Optional[int]:
    """
    Clean and validate a year value.
    Returns None if invalid, otherwise returns integer year.
    """
    if year_value is None or year_value == '':
        return None
    
    try:
        # Convert to string and clean
        year_str = str(year_value).strip()
        
        # Handle "ca. 1500" or "c. 1500"
        year_str = re.sub(r'^(ca?\.?\s*)', '', year_str, flags=re.IGNORECASE)
        
        # Handle "1500?" or "1500*"
        year_str = re.sub(r'[?*]$', '', year_str)
        
        # Extract first 4-digit number
        match = re.search(r'\d{4}', year_str)
        if match:
            year = int(match.group())
            # Validate year range (reasonable historical range)
            if 1000 <= year <= 2100:
                return year
        
        return None
    except (ValueError, AttributeError):
        return None


def clean_title(title: str) -> str:
    """
    Clean a work title by removing extra whitespace and normalizing.
    """
    if not title:
        return ''
    
    # Remove extra whitespace
    title = ' '.join(title.split())
    
    # Remove leading/trailing punctuation (except parentheses)
    title = title.strip(' .,;:')
    
    return title


def deduplicate_composer_key(full_name: str, birth_year: Optional[int]) -> str:
    """
    Generate a deduplication key for a composer.
    Used to check if a composer already exists in the database.
    """
    normalized = normalize_name(full_name)
    year_str = str(birth_year) if birth_year else 'unknown'
    return f"{normalized}_{year_str}"


def is_living_composer(birth_year: Optional[int], death_year: Optional[int]) -> bool:
    """
    Determine if a composer is likely still living based on birth/death years.
    """
    from datetime import datetime
    
    if death_year:
        return False
    
    if not birth_year:
        return False
    
    # If born after 1900 and no death year, likely living
    # (unless they're over 100 years old)
    current_year = datetime.now().year
    age = current_year - birth_year
    
    return birth_year > 1900 and age < 100


def parse_opus_number(opus_str: str) -> Optional[str]:
    """
    Parse and normalize opus number from various formats.
    Examples: "Op. 12", "op.12", "Opus 12", "BWV 1004"
    """
    if not opus_str:
        return None
    
    opus_str = opus_str.strip()
    
    # Normalize "Op." or "Opus" prefix
    opus_str = re.sub(r'^(op\.?|opus)\s*', 'Op. ', opus_str, flags=re.IGNORECASE)
    
    return opus_str if opus_str else None


def clean_instrumentation(instrumentation: str) -> str:
    """
    Clean and normalize instrumentation string.
    """
    if not instrumentation:
        return ''
    
    # Remove extra whitespace
    instrumentation = ' '.join(instrumentation.split())
    
    # Capitalize first letter of each word
    instrumentation = instrumentation.title()
    
    return instrumentation


def extract_duration_minutes(duration_str: str) -> Optional[int]:
    """
    Extract duration in minutes from various string formats.
    Examples: "10 min", "10'", "10:00", "10-12 minutes"
    """
    if not duration_str:
        return None
    
    duration_str = str(duration_str).strip().lower()
    
    # Match "X min" or "X minutes"
    match = re.search(r'(\d+)\s*(min|minutes?)', duration_str)
    if match:
        return int(match.group(1))
    
    # Match "X'" (minutes notation)
    match = re.search(r"(\d+)'", duration_str)
    if match:
        return int(match.group(1))
    
    # Match "MM:SS" format
    match = re.search(r'(\d+):(\d+)', duration_str)
    if match:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        return minutes + (1 if seconds >= 30 else 0)  # Round up if >= 30 seconds
    
    # Match "X-Y minutes" (take average)
    match = re.search(r'(\d+)\s*-\s*(\d+)', duration_str)
    if match:
        min_duration = int(match.group(1))
        max_duration = int(match.group(2))
        return (min_duration + max_duration) // 2
    
    return None


def validate_url(url: str) -> bool:
    """
    Validate if a string is a valid URL.
    """
    if not url:
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url))


def clean_country_name(country: str) -> str:
    """
    Clean and normalize country names.
    Handle common variations and misspellings.
    """
    if not country:
        return ''
    
    country = country.strip()
    
    # Country name mappings for common variations
    country_mappings = {
        'USA': 'United States',
        'U.S.A.': 'United States',
        'United States of America': 'United States',
        'UK': 'United Kingdom',
        'U.K.': 'United Kingdom',
        'Great Britain': 'United Kingdom',
        'The Netherlands': 'Netherlands',
        'Holland': 'Netherlands',
    }
    
    return country_mappings.get(country, country)


def split_movements(movements_str: str) -> list:
    """
    Split a movements string into a list.
    Handles various delimiters: semicolon, newline, numbered lists.
    """
    if not movements_str:
        return []
    
    # Split by semicolon or newline
    movements = re.split(r'[;\n]', movements_str)
    
    # Clean each movement
    movements = [m.strip() for m in movements if m.strip()]
    
    # Remove numbering (1., I., etc.)
    movements = [re.sub(r'^\d+\.?\s*|^[IVX]+\.?\s*', '', m) for m in movements]
    
    return movements


def generate_title_sort_key(title: str) -> str:
    """
    Generate a sort key for intelligent alphabetical sorting of work titles.
    
    Sort buckets (prefixes):
      1) Latin-letter titles      -> "1|<folded>"
      2) Numeric-leading titles   -> "2|<folded>"
      3) Other-letter titles      -> "3|<folded>"
      4) Symbol-only / empty      -> "4|<original-casefold>"
    
    Examples:
    - "Cadenza" -> 1|cadenza
    - À bout portant -> 1|a bout portant
    - 10 Studies -> 2|10 studies
    - Ιθάκη (Greek) -> 3|ιθάκη
    - _____ -> 4|_____
    """
    # Small, targeted expansions that stdlib normalization won't turn into ASCII sequences
    EXTENDED_LATIN_MAP = str.maketrans({
        'Æ': 'AE', 'æ': 'ae',
        'Œ': 'OE', 'œ': 'oe',
        'Ø': 'O',  'ø': 'o',
        'Ð': 'D',  'ð': 'd',
        'Þ': 'TH', 'þ': 'th',
        'ẞ': 'ss', 'ß': 'ss',
        'Ł': 'L',  'ł': 'l',
        'Đ': 'D',  'đ': 'd',
    })
    
    def strip_leading_junk(s: str) -> str:
        """Remove leading chars that are not letters/digits using Unicode categories."""
        if not s:
            return ''
        
        s = unicodedata.normalize('NFKC', s)
        
        i = 0
        while i < len(s):
            ch = s[i]
            cat = unicodedata.category(ch)
            # Keep if letter or number
            if cat[0] in ('L', 'N'):
                break
            # Otherwise drop punctuation, symbols, marks, separators, format chars
            i += 1
        
        return s[i:].strip()
    
    def remove_combining_marks(s: str) -> str:
        """Remove diacritics by decomposing and dropping combining marks."""
        decomp = unicodedata.normalize('NFKD', s)
        return ''.join(c for c in decomp if unicodedata.category(c) != 'Mn')
    
    def is_latin_letter(ch: str) -> bool:
        """Detect Latin script by Unicode name."""
        try:
            return unicodedata.category(ch).startswith('L') and 'LATIN' in unicodedata.name(ch)
        except ValueError:
            return False
    
    if not title:
        return "4|"
    
    original = unicodedata.normalize('NFKC', title).casefold()
    core = strip_leading_junk(title)
    
    if not core:
        return f"4|{original}"
    
    # Expand ligatures etc.
    core = core.translate(EXTENDED_LATIN_MAP)
    
    first = core[0]
    
    # Bucket decision
    if first.isdigit():
        # Keep digits but casefold everything else
        return f"2|{unicodedata.normalize('NFKC', core).casefold()}"
    
    if is_latin_letter(first):
        # For Latin titles: remove diacritics so É ~ E
        folded = remove_combining_marks(core)
        folded = unicodedata.normalize('NFKC', folded).casefold()
        return f"1|{folded}"
    
    # Other scripts: keep them, but normalize + casefold
    return f"3|{unicodedata.normalize('NFKC', core).casefold()}"


# --- Instrumentation categorisation -----------------------------------------
#
# `Work.instrumentation_category` is a *derived* bucket: nothing in the UI sets it
# directly, it is always inferred from the free-text `Work.instrumentation_detail`.
# This module owns that mapping so the API filter, suggestion-apply, the sheerpluck
# importer and the cleanup command share one implementation — they each used to
# carry their own copy (or their own substring hack) and drifted apart.

UNCATEGORIZED_INSTRUMENTATION = 'Other'

# The complete set of buckets `canonical_instrumentation` can return, in the order
# the filter dropdown shows them. Nothing outside this tuple may become a category.
CANONICAL_INSTRUMENTATION_CATEGORIES = (
    'Solo',
    'Duo',
    'Trio',
    'Quartet',
    'Quintet',
    'Sextet',
    'Septet',
    'Octet',
    'Guitar and Orchestra',
    'Guitar and Voice',
    'Guitar and Flute',
    'Guitar and Violin',
    'Guitar and Viola',
    'Guitar and Cello',
    'Guitar and Piano',
    'Guitar and Clarinet',
    'Guitar and Saxophone',
    'Guitar and Harp',
    'Guitar and Percussion',
    'Guitar and Mandolin',
    'Guitar and Trumpet',
    'Guitar and Oboe',
    'Guitar and Recorder',
    'Electric Guitar',
    'Bass Guitar',
    'Plucked Instruments',
    'Chamber Music',
    'Guitar with Electronics',
    'Ensemble',
    'Stage Work',
    'Dance/Ballet',
    'Installation/Sound Environment',
    UNCATEGORIZED_INSTRUMENTATION,
)

_CANONICAL_BY_NORM = {
    normalize_name(name): name for name in CANONICAL_INSTRUMENTATION_CATEGORIES
}

_ENSEMBLE_BY_PLAYER_COUNT = {
    1: 'Solo', 2: 'Duo', 3: 'Trio', 4: 'Quartet',
    5: 'Quintet', 6: 'Sextet', 7: 'Septet', 8: 'Octet',
}

_NUMBER_WORDS = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8,
}

# Whole-string shorthands the rule pass can't infer. Keys are `normalize_name`d.
INSTRUMENTATION_ALIASES = {
    'guitar': 'Solo',
    'classical guitar': 'Solo',
    'acoustic guitar': 'Solo',
    'unaccompanied guitar': 'Solo',
    'guitar alone': 'Solo',
    'duet': 'Duo',
    'guitar duet': 'Duo',
    'concerto': 'Guitar and Orchestra',
    'guitar concerto': 'Guitar and Orchestra',
    'orchestra': 'Guitar and Orchestra',
    'lute': 'Plucked Instruments',
    'vihuela': 'Plucked Instruments',
    'theorbo': 'Plucked Instruments',
    'tape': 'Guitar with Electronics',
    'fixed media': 'Guitar with Electronics',
    'live electronics': 'Guitar with Electronics',
    'opera': 'Stage Work',
    'ballet': 'Dance/Ballet',
}

# Foreign spellings and common misspellings, repaired before the rule pass. Applied
# with word boundaries so surrounding text and casing survive ("Stage Work:" etc).
INSTRUMENTATION_SPELLING_FIXES = {
    'octett': 'octet', 'octette': 'octet', 'ottetto': 'octet',
    'septett': 'septet', 'septette': 'septet', 'settimino': 'septet',
    'sextett': 'sextet', 'sextette': 'sextet', 'sestetto': 'sextet',
    'quintett': 'quintet', 'quintette': 'quintet', 'quintetto': 'quintet',
    'quartett': 'quartet', 'quartette': 'quartet', 'quartetto': 'quartet',
    'quatuor': 'quartet',
    'terzetto': 'trio',
    'guitarra': 'guitar', 'guitare': 'guitar', 'gitarre': 'guitar',
    'chitarra': 'guitar', 'gitaar': 'guitar', 'guitarre': 'guitar',
    'guiter': 'guitar', 'guitat': 'guitar', 'gutiar': 'guitar',
    'violoncelo': 'violoncello', 'violincello': 'violoncello',
    'violine': 'violin', 'violon': 'violin', 'geige': 'violin',
    'orchester': 'orchestra', 'orchestre': 'orchestra',
    'orquesta': 'orchestra', 'orkest': 'orchestra', 'orchestera': 'orchestra',
    'floete': 'flute', 'flauto': 'flute', 'flauta': 'flute',
    'klarinette': 'clarinet', 'clarinette': 'clarinet', 'clarinete': 'clarinet',
    'saxofon': 'saxophone', 'saxophon': 'saxophone', 'saxaphone': 'saxophone',
    'pianoforte': 'piano', 'klavier': 'piano',
    'harfe': 'harp', 'arpa': 'harp',
    'stimme': 'voice', 'voix': 'voice', 'canto': 'voice',
    'schlagzeug': 'percussion', 'percussione': 'percussion',
    'percusion': 'percussion',
    'mandoline': 'mandolin',
    'ensamble': 'ensemble',
    'electronic': 'electronics', 'electronica': 'electronics',
    'elektronik': 'electronics',
}

_SPELLING_FIX_RE = re.compile(
    r'\b(' + '|'.join(
        sorted(map(re.escape, INSTRUMENTATION_SPELLING_FIXES), key=len, reverse=True)
    ) + r')\b',
    re.IGNORECASE,
)


def _normalize_instrumentation(text: str) -> str:
    """Lowercase, de-accent and collapse whitespace for equality/alias lookups."""
    return ' '.join(normalize_name(text).split())


def _repair_instrumentation_spelling(text: str) -> str:
    return _SPELLING_FIX_RE.sub(
        lambda m: INSTRUMENTATION_SPELLING_FIXES[m.group(0).lower()], text
    )


# A count may be separated from "guitars" by qualifiers ("2 acoustic guitars"), so
# allow a couple of words in between. The noun must be plural in that case, since
# the count is what makes it plural.
_QUALIFIER = r'(?:[a-z-]+\s+){0,2}'


def _ensemble_by_player_count(normalized: str) -> Optional[str]:
    """Map "8 guitars" / "2 acoustic guitars" / "eight guitars" / "guitar (8)"."""
    for pattern in (rf'\b(\d+)\s+{_QUALIFIER}guitars\b',
                    r'\b(\d+)\s*guitars?\b',
                    r'\bguitars?\s*\((\d+)\)'):
        match = re.search(pattern, normalized)
        if match:
            return _ENSEMBLE_BY_PLAYER_COUNT.get(int(match.group(1)))
    match = re.search(
        r'\b(' + '|'.join(_NUMBER_WORDS) + rf')\s+{_QUALIFIER}guitars\b', normalized
    )
    if match:
        return _ENSEMBLE_BY_PLAYER_COUNT.get(_NUMBER_WORDS[match.group(1)])
    return None


def _fuzzy_canonical(normalized: str) -> Optional[str]:
    """Last-resort near-match against known names, for unlisted misspellings.

    Only short strings are considered: a long detail line ("flute, guitar, cello")
    is a composite the rule pass already understands, and fuzzily snapping it to a
    single bucket would be worse than falling through to 'Other'.

    Text carrying a digit is never fuzzed either. The digit is almost always a
    player count, and edit distance ignores it: "2 acoustic guitars" is one cheap
    edit from the "acoustic guitar" alias, which silently turned a duo into a solo.
    """
    if len(normalized) > 24 or any(ch.isdigit() for ch in normalized):
        return None
    from difflib import get_close_matches

    pool = list(_CANONICAL_BY_NORM) + list(INSTRUMENTATION_ALIASES)
    match = get_close_matches(normalized, pool, n=1, cutoff=0.85)
    if not match:
        return None
    return _CANONICAL_BY_NORM.get(match[0]) or INSTRUMENTATION_ALIASES.get(match[0])


def _categorize_by_rules(raw: str) -> str:
    """Map a raw instrumentation string to a canonical bucket by rule.

    Order matters throughout: explicit genre prefixes beat instrument detection,
    voice beats ensemble-size, and named instrument pairings beat the generic
    comma count. Callers should prefer `canonical_instrumentation`, which layers
    exact/alias/spelling/fuzzy handling on top of this.
    """
    if not raw:
        return UNCATEGORIZED_INSTRUMENTATION

    raw_lower = raw.lower()

    # Explicit genre markers always override instrument detection.
    if raw.startswith('Stage Work:') or raw.startswith('Opera:'):
        return 'Stage Work'
    if raw.startswith('Dance/Ballet:'):
        return 'Dance/Ballet'
    if raw.startswith('Installation/Sound Environment:'):
        return 'Installation/Sound Environment'

    # Noted now, but only applied after the specific-instrument checks below.
    has_chamber_music_prefix = raw.startswith('Chamber Music:')
    has_ensemble_prefix = raw.startswith('Ensemble:')
    has_concerto_prefix = raw.startswith('Concerto:')

    if 'orchestra' in raw_lower or 'symphon' in raw_lower or 'philharmonic' in raw_lower:
        return 'Guitar and Orchestra'
    if 'concerto' in raw_lower and 'guitar' in raw_lower and not has_concerto_prefix:
        return 'Guitar and Orchestra'

    # Commas approximate the number of players.
    comma_count = raw.count(',')

    if comma_count >= 5:
        return 'Chamber Music' if 'chamber' in raw_lower else 'Ensemble'

    if comma_count == 0 and ('solo' in raw_lower or raw.startswith('Solo:')):
        if 'electric' in raw_lower and 'guitar' in raw_lower:
            return 'Electric Guitar'
        if 'bass' in raw_lower and 'guitar' in raw_lower:
            return 'Bass Guitar'
        return 'Solo'

    voice_terms = ['voice', 'soprano', 'mezzo-soprano', 'mezzo', 'contralto',
                   'countertenor', 'chorus', 'choir', 'vocal', 'song', 'singer', 'vocals']
    if any(word in raw_lower for word in voice_terms):
        return 'Guitar and Voice'

    # alto/tenor/baritone/bass name a voice part *unless* an instrument follows
    # them ("alto flute", "bass clarinet").
    instrument_types = [
        'flute', 'piccolo', 'fife',
        'sax', 'saxophone',
        'clarinet', 'basset',
        'oboe', 'cor anglais', 'english horn',
        'bassoon', 'contrabassoon',
        'recorder', 'flageolet',
        'trumpet', 'cornet', 'flugelhorn',
        'horn', 'french horn',
        'trombone', 'euphonium', 'tuba',
        'guitar', 'ukulele', 'banjo', 'mandolin',
        'violin', 'viola', 'viol', 'cello', 'violoncello',
        'drum', 'timpani', 'percussion',
        'shawm', 'crumhorn', 'dulcian',
        'double bass', 'contrabass', 'string bass', 'upright bass',
    ]
    for voice_term in ['alto', 'tenor', 'baritone', 'bass']:
        if f' {voice_term}' in raw_lower or raw_lower.startswith(voice_term):
            if voice_term == 'bass' and any(
                s in raw_lower for s in ('double bass', 'doublebass', 'contrabass')
            ):
                continue
            if not any(
                f'{voice_term}{sep}{inst}' in raw_lower
                for inst in instrument_types
                for sep in (' ', '-', '')
            ):
                return 'Guitar and Voice'

    if any(word in raw_lower for word in ['electronics', 'tape', 'fixed media',
                                          'live electronics', 'sampler',
                                          'synthesizer', 'computer']):
        return 'Guitar with Electronics'

    # Named pairings, checked before the generic ensemble sizes below.
    if comma_count == 1:
        for keywords, category in (
            (('piano', 'harpsichord'), 'Guitar and Piano'),
            (('flute',), 'Guitar and Flute'),
            (('violin',), 'Guitar and Violin'),
            (('viola',), 'Guitar and Viola'),
            (('cello', 'violoncello'), 'Guitar and Cello'),
            (('clarinet',), 'Guitar and Clarinet'),
            (('saxophone',), 'Guitar and Saxophone'),
            (('harp',), 'Guitar and Harp'),
            (('percussion', 'marimba'), 'Guitar and Percussion'),
            (('trumpet', 'horn', 'trombone'), 'Guitar and Trumpet'),
            (('oboe', 'bassoon'), 'Guitar and Oboe'),
            (('recorder',), 'Guitar and Recorder'),
            (('mandolin',), 'Guitar and Mandolin'),
        ):
            if any(word in raw_lower for word in keywords):
                return category

    if 'duo' in raw_lower or 'guitar (2)' in raw_lower or comma_count == 1:
        return 'Duo'
    if 'trio' in raw_lower or 'guitar (3)' in raw_lower or comma_count == 2:
        return 'Trio'
    if 'quartet' in raw_lower or 'guitar (4)' in raw_lower or comma_count == 3:
        return 'Quartet'
    if 'quintet' in raw_lower or 'guitar (5)' in raw_lower:
        return 'Quintet'
    if 'sextet' in raw_lower or 'guitar (6)' in raw_lower:
        return 'Sextet'
    if 'septet' in raw_lower or 'guitar (7)' in raw_lower:
        return 'Septet'
    if 'octet' in raw_lower or 'guitar (8)' in raw_lower:
        return 'Octet'

    # "lute" checked apart from the rest so it can't match inside "flute".
    plucked_words = ['mandolin', 'banjo', 'theorbo', 'vihuela', 'cittern',
                     'balalaika', 'sitar', 'koto']
    if any(word in raw_lower for word in plucked_words):
        return 'Plucked Instruments'
    if ' lute' in raw_lower or raw_lower.startswith('lute') or ',lute' in raw_lower:
        return 'Plucked Instruments'

    if has_concerto_prefix:
        return 'Guitar and Orchestra'
    if has_chamber_music_prefix:
        return 'Chamber Music'
    if has_ensemble_prefix:
        return 'Ensemble'

    return UNCATEGORIZED_INSTRUMENTATION


def canonical_instrumentation(text: str) -> Optional[str]:
    """Map free-text instrumentation to one of CANONICAL_INSTRUMENTATION_CATEGORIES.

    Returns None for blank input (the work simply has no instrumentation text) and
    'Other' for text that resolves to nothing recognisable.
    """
    if not text or not text.strip():
        return None

    normalized = _normalize_instrumentation(text)
    if not normalized:
        return None

    # Already a category name ("Octet", "Guitar and Piano"). Checked first because
    # the rule pass reads names like "Guitar and Piano" as an uncomma'd string and
    # would fall through to 'Other'.
    if normalized in _CANONICAL_BY_NORM:
        return _CANONICAL_BY_NORM[normalized]

    if normalized in INSTRUMENTATION_ALIASES:
        return INSTRUMENTATION_ALIASES[normalized]

    # Repair before the rules, not after them: "Klavier, guitar" otherwise reaches
    # the generic comma count and reads as a bare Duo instead of Guitar and Piano.
    # The repair is word-boundary'd and case-preserving, so a string with nothing
    # to fix is passed through untouched and behaves exactly as it always has.
    repaired = _repair_instrumentation_spelling(text)
    if repaired != text:
        repaired_norm = _normalize_instrumentation(repaired)
        if repaired_norm in _CANONICAL_BY_NORM:
            return _CANONICAL_BY_NORM[repaired_norm]
        if repaired_norm in INSTRUMENTATION_ALIASES:
            return INSTRUMENTATION_ALIASES[repaired_norm]

    # Rules read the original casing: their genre prefixes are case-sensitive.
    category = _categorize_by_rules(repaired)
    if category != UNCATEGORIZED_INSTRUMENTATION:
        return category

    by_count = _ensemble_by_player_count(_normalize_instrumentation(repaired))
    if by_count:
        return by_count

    return _fuzzy_canonical(normalized) or UNCATEGORIZED_INSTRUMENTATION


# --- alternate realizations --------------------------------------------------
#
# A detail string can describe more than one way to play the work:
#
#     "guitar, violin (or flute)"        -> play it with a violin, or with a flute
#     "Guitar and Tape (or 5 Guitars)"   -> play it against tape, or as a quintet
#
# The "(or ...)" is not noise and not prose: it is the *alternate realization*,
# already authored by our sources on ~1,800 works. Reading the whole string at once
# lets the alternate outrank the primary — "guitar, violin (or flute)" resolved to
# Guitar and Flute — so split the realizations apart and resolve each on its own.

# "(or flute)" / "( or 2 mandolins )". Bounded to one parenthetical group.
_ALTERNATE_RE = re.compile(r'\(\s*or\b(?P<alt>[^)]*)\)', re.IGNORECASE)

# The instrument the alternate replaces, plus the parenthetical itself:
# "violin (or flute)" -> the alternate realization says "flute". At most two words
# of head, so "bass guitar (or double bass)" swaps the whole instrument name and
# "guitar, violin (or flute)" doesn't swallow the comma'd sibling.
_SUBSTITUTION_RE = re.compile(
    r'(?P<head>[\w\-]+(?:\s+[\w\-]+)?)\s*\(\s*or\s+(?P<alt>[^)]*?)\s*\)',
    re.IGNORECASE,
)

# An alternate realization that drops the guitar entirely is not guitar repertoire
# ("soprano - guitar (or piano)" played the alternate way is a piano song) and must
# not earn a category in a guitar catalogue.
_GUITAR_TERMS = ('guitar', 'guitarra', 'guitare', 'gitarre', 'chitarra', 'lute',
                 'vihuela', 'theorbo', 'bandurria')


def _collapse(text: str) -> str:
    return ' '.join((text or '').split())


def split_realizations(detail: str):
    """Split a detail string into (primary_text, [alternate_text, ...]).

    The primary drops every "(or ...)"; each alternate substitutes its content for
    the instrument it follows, leaving the rest of the scoring intact:

        "guitar, violin (or flute)" -> ("guitar, violin", ["guitar, flute"])

    No parenthetical means no alternates, and the primary is the string unchanged —
    so the ~71k works without one are untouched by this code path.
    """
    if not detail or not detail.strip():
        return ('', [])
    if not _ALTERNATE_RE.search(detail):
        return (_collapse(detail), [])

    primary = _collapse(_ALTERNATE_RE.sub('', detail))
    alternate = _collapse(_SUBSTITUTION_RE.sub(lambda m: m.group('alt'), detail))
    # A substitution that changed nothing (the parenthetical had no instrument in
    # front of it) leaves the alternate identical to the input; drop it rather than
    # re-resolve the blob we are trying to get away from.
    alternates = [alternate] if alternate and alternate != _collapse(detail) else []
    return (primary, alternates)


def primary_instrumentation(detail: str):
    """The category for how the work is *notated* — alternates excluded."""
    primary, _ = split_realizations(detail)
    return canonical_instrumentation(primary)


def alternate_instrumentation_names(detail: str):
    """Canonical category names for the work's *other* playable realizations.

    Deliberately conservative — an alternate earns a row only if it is
    (a) resolvable, (b) a *different* bucket than the primary, (c) not the 'Other'
    catch-all, and (d) still guitar repertoire. Two-thirds of real alternates are
    trivial substitutions that resolve to the primary's own bucket and are dropped
    here; without (d), "soprano - guitar (or piano)" would file a piano song.
    """
    primary_name = primary_instrumentation(detail)
    _, alternates = split_realizations(detail)

    names = []
    for alt_text in alternates:
        if not any(term in alt_text.lower() for term in _GUITAR_TERMS):
            continue
        name = canonical_instrumentation(alt_text)
        if not name or name == UNCATEGORIZED_INSTRUMENTATION or name == primary_name:
            continue
        if name not in names:
            names.append(name)
    return names


def resolve_instrumentation_category(text: str):
    """The InstrumentationCategory `text` belongs in, creating it if needed.

    Resolves the *primary* realization: a parenthetical alternate describes another
    way to play the work, not what it is. None for blank text, so a work with no
    instrumentation keeps a NULL category rather than being swept into 'Other'.
    """
    from .models import InstrumentationCategory

    name = primary_instrumentation(text)
    if not name:
        return None
    category, _ = InstrumentationCategory.objects.get_or_create(name=name)
    return category


def resolve_instrumentation_filter(term: str) -> Optional[str]:
    """Canonical category name for an ?instrumentation= term, else None.

    Unlike `canonical_instrumentation`, an unrecognised term gives None instead of
    the 'Other' catch-all — a junk filter must return no works, not the whole
    uncategorised bucket. 'Other' is only returned when explicitly asked for.
    """
    if not term or not term.strip():
        return None
    name = canonical_instrumentation(term)
    if name != UNCATEGORIZED_INSTRUMENTATION:
        return name
    if _normalize_instrumentation(term) == normalize_name(UNCATEGORIZED_INSTRUMENTATION):
        return UNCATEGORIZED_INSTRUMENTATION
    return None
