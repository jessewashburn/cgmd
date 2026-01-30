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
