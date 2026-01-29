# Database Schema Documentation

## Overview

This schema is designed for a classical guitar music database with **~67,000 works** from the Sheerpluck dataset, with optimization for search performance and data quality management.

---

## Data Analysis Summary

### Source Data (sheerpluck_data.csv)
- **Total Records**: 67,164 works
- **Fields**: 
  - ID, Name (Composer), Birth Year, Death Year, Country, Work (Title), Instrumentation
  
### Key Observations

1. **Composer Name Complexity**:
   - Some composers appear with origin descriptions: "American composer of Brazilian origin"
   - Name formats vary: "Aa, Michel van der", "Almeida, Laurindo"
   - Need to handle: Last name first, compound names, prefixes (van, de, von)

2. **Date Handling**:
   - Many missing birth/death years
   - Some composers still living (empty death year)
   - Years range from ~1400s to 2000s

3. **Country Data**:
   - Sometimes includes descriptive text
   - Need normalization to standard country names
   - ~100+ unique countries/regions

4. **Instrumentation Categories**:
   - 20+ distinct categories identified
   - Ranges from "Solo" to "Stage Work" to "Guitar with Electronics"
   - Some entries have empty instrumentation

5. **Works Per Composer**:
   - Highly variable: 1 work to 100+ works per composer
   - Example: Pedro Abreu has 30+ solo guitar works listed consecutively

---

## Schema Design Principles

### 1. **Normalization**
- Composers separated from works (1:N relationship)
- Countries in lookup table (reduces redundancy)
- Instrumentation categories standardized

### 2. **Search Optimization**
- **FULLTEXT indexes** on name and title fields for natural language search
- **B-tree indexes** on frequently filtered columns (year, country, instrumentation)
- **Composite indexes** for common query patterns (composer + public, etc.)
- **Denormalized search table** (`work_search_index`) for ultra-fast lookups

### 3. **Data Quality Management**
- `is_verified` flag for reviewed records
- `needs_review` flag for problematic data
- `admin_notes` for curator comments
- Source tracking via `data_source_id`

### 4. **Flexibility**
- Tag system for categorization beyond fixed schema
- Alias system for composer name variants
- JSON-compatible fields for complex data (movements, etc.)

---

## Core Tables

### `composers`
**Purpose**: Store composer biographical information

**Key Fields**:
- `full_name`: Display name
- `name_normalized`: Lowercase, accent-free for search matching
- `birth_year`, `death_year`: Optional dates
- `country_id`: Foreign key to countries table
- `country_description`: For complex origins like "American composer of Brazilian origin"
- `period`: Musical period (Renaissance, Baroque, Classical, Romantic, Modern, Contemporary)

**Indexes**:
- Full-text on name fields
- B-tree on birth/death years for filtering by period
- B-tree on country for geographic filtering

**Search Strategy**:
```sql
-- Fast name search
SELECT * FROM composers 
WHERE MATCH(full_name, first_name, last_name) 
AGAINST('Almeida' IN NATURAL LANGUAGE MODE);

-- Filter by period
SELECT * FROM composers 
WHERE birth_year >= 1900 AND (death_year IS NULL OR death_year >= 1950);
```

---

### `works`
**Purpose**: Store individual musical compositions

**Key Fields**:
- `composer_id`: Links to composer
- `title`: Work title
- `title_normalized`: Search-optimized version
- `opus_number`, `catalog_number`: Optional cataloging
- `composition_year`: When composed
- `instrumentation_category_id`: Type of ensemble
- `difficulty_level`: 1-10 scale (to be added by curators)
- `view_count`: Popularity tracking

**Indexes**:
- Full-text on title and description
- B-tree on composer_id (most common join)
- Composite on (composer_id, is_public) for public listings
- B-tree on instrumentation for filtering

**Search Strategy**:
```sql
-- Find works by title
SELECT w.*, c.full_name 
FROM works w
JOIN composers c ON w.composer_id = c.id
WHERE MATCH(w.title) AGAINST('Prelude' IN NATURAL LANGUAGE MODE)
AND w.is_public = TRUE;

-- Filter by instrumentation
SELECT * FROM works 
WHERE instrumentation_category_id = (
    SELECT id FROM instrumentation_categories WHERE name = 'Solo'
)
AND is_public = TRUE;
```

---

### `work_search_index`
**Purpose**: Denormalized table combining composer + work data for ultra-fast search

**Why Denormalized?**:
- Avoids JOINs in search queries (significant performance boost)
- Pre-computed search text field
- Popularity scoring built-in
- Automatically maintained via triggers

**Key Fields**:
- All frequently searched fields duplicated
- `search_text`: Combined searchable content
- `popularity_score`: Calculated from view counts, recency
- `last_viewed`: For time-based relevance

**Usage**:
```sql
-- Single-query search across all fields
CALL sp_search_works('Bach guitar solo', 20, 0);

-- Returns ranked results with relevance + popularity scoring
```

---

## Supporting Tables

### `composer_aliases`
**Purpose**: Handle name variations and spellings

**Use Cases**:
- Alternate spellings: "Tchaikovsky" vs "Tschaikowsky"
- Birth names vs stage names
- Translated names (Japanese, Chinese characters → Latin)
- Married names

### `tags`
**Purpose**: Flexible categorization beyond fixed schema

**Use Cases**:
- Musical style: "Impressionist", "Minimalist", "Atonal"
- Technical features: "Tremolo", "Harmonics", "Scordatura"
- Form: "Sonata", "Suite", "Variations"
- Mood: "Melancholic", "Energetic", "Contemplative"

**Benefits**:
- Schema remains simple
- Categories can evolve
- Community/curator-driven taxonomy

### `countries`
**Purpose**: Normalized country lookup

**Benefits**:
- Consistent naming
- Easy to add ISO codes for mapping/visualization
- Can group by region (Europe, Asia, Americas)

### `instrumentation_categories`
**Purpose**: Standardized ensemble types

**Populated from CSV analysis**:
```
Solo, Duo, Trio, Quartet, Chamber Music, Ensemble, 
Guitar Ensemble, Concerto, Orchestra, Chorus and Guitar,
Guitar with Electronics, Stage Work, etc.
```

---

## Search Implementation Strategy

### Three-Tier Search Approach

#### 1. **Basic Search** (Exact/Prefix Matching)
```sql
-- Fast, simple queries
SELECT * FROM composers 
WHERE last_name LIKE 'Bach%';

SELECT * FROM works 
WHERE title LIKE '%Prelude%';
```
**Pros**: Very fast, uses B-tree indexes  
**Cons**: No ranking, no fuzzy matching

#### 2. **Full-Text Search** (Natural Language)
```sql
-- Natural language search with relevance ranking
SELECT *, MATCH(search_text) AGAINST('romantic spanish guitar') AS score
FROM work_search_index
WHERE MATCH(search_text) AGAINST('romantic spanish guitar')
ORDER BY score DESC;
```
**Pros**: Relevance ranking, handles multiple terms, good performance  
**Cons**: Limited fuzzy matching, MySQL FULLTEXT limitations

#### 3. **Advanced Search** (Elasticsearch - Future Enhancement)
For larger scale (100k+ works) or sophisticated features:
- Fuzzy matching (typo tolerance)
- Synonyms (guitar = guitarra)
- Faceted search (drill-down filters)
- Advanced relevance tuning

---

## Index Strategy Details

### FULLTEXT Indexes
**Purpose**: Natural language search on text fields

**Tables with FULLTEXT**:
- `composers`: `(full_name, first_name, last_name)`, `(biography)`
- `composer_aliases`: `(alias_name)`
- `works`: `(title, subtitle)`, `(title, subtitle, description)`
- `work_search_index`: `(search_text)`, `(composer_full_name, work_title)`

**How MySQL FULLTEXT Works**:
- Inverted index of words → document IDs
- Ignores common words (stopwords)
- Ranks by relevance (TF-IDF based)
- Fast for multi-word queries

**Query Modes**:
```sql
-- Natural language (default)
... MATCH(...) AGAINST('query' IN NATURAL LANGUAGE MODE)

-- Boolean (exact phrases, +required, -excluded)
... MATCH(...) AGAINST('+Bach -"Well-Tempered"' IN BOOLEAN MODE)

-- With query expansion (finds related terms)
... MATCH(...) AGAINST('query' WITH QUERY EXPANSION)
```

### B-tree Indexes
**Purpose**: Exact matching, range queries, sorting

**Strategic Placement**:
- All foreign keys
- Frequently filtered columns (year, country, instrumentation)
- Fields used in ORDER BY
- Columns in WHERE clauses

**Composite Indexes**:
```sql
INDEX idx_composer_public (composer_id, is_public)
```
Optimizes common pattern: "Get public works by composer X"

### Index Maintenance
```sql
-- Monitor index usage
SELECT * FROM sys.schema_unused_indexes;

-- Rebuild indexes if fragmented
OPTIMIZE TABLE works;
```

---

## Data Import Strategy

### Phase 1: Parse & Clean CSV
```python
import pandas as pd

# Read CSV
df = pd.read_csv('sheerpluck_data.csv')

# Clean composer names
df['last_name'] = df['Name'].apply(extract_last_name)
df['first_name'] = df['Name'].apply(extract_first_name)

# Handle country descriptions
df['country_clean'] = df['Country'].apply(extract_country_name)
df['country_description'] = df['Country'].apply(extract_description)

# Normalize for search
df['name_normalized'] = df['Name'].str.lower().str.normalize('NFKD')
df['title_normalized'] = df['Work'].str.lower().str.normalize('NFKD')
```

### Phase 2: Deduplicate Composers
```python
# Group by name + birth year to find unique composers
composers = df.groupby(['Name', 'Birth Year']).first().reset_index()

# Insert into composers table
for composer in composers.itertuples():
    # INSERT INTO composers ...
```

### Phase 3: Import Works
```python
# For each work, find composer_id and insert
for work in df.itertuples():
    composer_id = get_or_create_composer(work.Name, work.BirthYear)
    instrumentation_id = get_or_create_instrumentation(work.Instrumentation)
    # INSERT INTO works ...
```

### Phase 4: Build Search Index
```sql
-- Triggers automatically populate work_search_index
-- But can manually rebuild if needed:
TRUNCATE work_search_index;
INSERT INTO work_search_index (...)
SELECT ... FROM works w JOIN composers c ...;
```

---

## Performance Considerations

### Expected Query Performance (67k records)

**Fast Queries** (< 10ms):
- Composer lookup by ID
- Works by composer ID
- Exact name/title match with index

**Medium Queries** (10-100ms):
- Full-text search on composers or works
- Filtered lists (by country, instrumentation, year)
- Sorted results with pagination

**Slower Queries** (100ms-1s):
- Complex multi-table joins without proper indexes
- Full-text search with many results + complex filters
- Aggregations (statistics, counts by category)

### Optimization Techniques

1. **Use work_search_index for search queries**
   - Avoid JOINs in hot path
   - Pre-computed relevance

2. **Pagination**
   ```sql
   -- Use LIMIT/OFFSET with index
   SELECT * FROM works 
   WHERE composer_id = 123 
   ORDER BY composition_year DESC 
   LIMIT 20 OFFSET 40;
   ```

3. **Query Result Caching (Django)**
   ```python
   from django.core.cache import cache
   
   def get_popular_works():
       cached = cache.get('popular_works')
       if not cached:
           cached = Works.objects.filter(is_public=True).order_by('-view_count')[:20]
           cache.set('popular_works', cached, 3600)  # 1 hour
       return cached
   ```

4. **Database Query Cache** (MySQL)
   ```sql
   SET GLOBAL query_cache_size = 67108864;  -- 64MB
   SET GLOBAL query_cache_type = 1;
   ```

5. **Connection Pooling**
   - Use Django's CONN_MAX_AGE setting
   - Reduces connection overhead

---

## API Design Implications

### Recommended Django REST Endpoints

```
GET  /api/composers/              # List composers (paginated)
GET  /api/composers/{id}/          # Composer detail
GET  /api/composers/{id}/works/    # Works by composer

GET  /api/works/                   # List works (paginated)
GET  /api/works/{id}/              # Work detail

GET  /api/search/?q=query          # Unified search
GET  /api/search/composers/?q=     # Composer-specific search
GET  /api/search/works/?q=         # Work-specific search

GET  /api/instrumentations/        # List categories
GET  /api/countries/               # List countries
GET  /api/tags/                    # List tags

GET  /api/stats/popular/           # Popular works
GET  /api/stats/composers/         # Composer statistics
```

### Search Endpoint Implementation
```python
# Django view using sp_search_works stored procedure
from django.db import connection

def search_works(request):
    query = request.GET.get('q', '')
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    
    with connection.cursor() as cursor:
        cursor.callproc('sp_search_works', [query, limit, offset])
        results = cursor.fetchall()
    
    # Serialize and return
    return JsonResponse({'results': results})
```

### Filtering Examples
```
/api/works/?instrumentation=Solo
/api/works/?composer__country=Spain
/api/works/?composition_year__gte=1900&composition_year__lte=1950
/api/works/?difficulty__lte=5
/api/composers/?is_living=true
```

---

## Admin Portal Features

### Django Admin Customizations

1. **Composer Admin**:
   - Inline editing of works
   - Bulk actions: Mark verified, Merge duplicates
   - Filter by country, period, verified status
   - Search by name, alias

2. **Work Admin**:
   - Auto-complete for composer selection
   - Inline instrumentation category selection
   - Bulk actions: Change category, Mark for review
   - Filter by instrumentation, year, verified status

3. **Data Quality Dashboard**:
   - Works needing review
   - Missing data reports (no year, no instrumentation)
   - Duplicate detection
   - Recent changes log

4. **Search Index Management**:
   - Manual rebuild trigger
   - Index statistics
   - Slow query log

---

## Migration Path

### Development → Production

1. **Local Development**:
   ```bash
   # Create database
   mysql -u root -p -e "CREATE DATABASE cgmd_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
   
   # Import schema
   mysql -u root -p cgmd_dev < database_schema.sql
   
   # Run Django migrations
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Import Data**:
   ```bash
   python manage.py import_sheerpluck_data sheerpluck_data.csv
   ```

3. **Verify Data**:
   ```sql
   SELECT COUNT(*) FROM composers;
   SELECT COUNT(*) FROM works;
   SELECT COUNT(*) FROM work_search_index;
   ```

4. **Production Deployment**:
   ```bash
   # On AWS Lightsail MySQL
   mysql -u admin -p -h <lightsail-endpoint> cgmd_prod < database_schema.sql
   
   # Run production import
   python manage.py import_sheerpluck_data --production sheerpluck_data.csv
   ```

---

## Monitoring & Maintenance

### Key Metrics to Track

1. **Database Size**:
   ```sql
   SELECT 
       table_name,
       ROUND((data_length + index_length) / 1024 / 1024, 2) AS size_mb
   FROM information_schema.tables
   WHERE table_schema = 'cgmd_prod';
   ```

2. **Index Usage**:
   ```sql
   SELECT * FROM sys.schema_unused_indexes 
   WHERE object_schema = 'cgmd_prod';
   ```

3. **Slow Queries**:
   ```sql
   -- Enable slow query log
   SET GLOBAL slow_query_log = 'ON';
   SET GLOBAL long_query_time = 2;  -- Log queries > 2 seconds
   ```

4. **Search Performance**:
   ```sql
   -- Test search query performance
   EXPLAIN SELECT * FROM work_search_index
   WHERE MATCH(search_text) AGAINST('Bach prelude');
   ```

### Regular Maintenance Tasks

**Daily**:
- Monitor error logs
- Check API response times

**Weekly**:
- Review new entries needing verification
- Process staff corrections

**Monthly**:
- Optimize tables: `OPTIMIZE TABLE works, composers, work_search_index;`
- Review and update tag taxonomy
- Database backup verification

**Quarterly**:
- Re-import from Sheerpluck/IMSLP (check for updates)
- Performance audit
- Index optimization review

---

## Future Enhancements

### Short-term (3-6 months)
1. User accounts and favorites
2. Advanced filtering UI (multi-select, ranges)
3. Autocomplete search suggestions
4. Related works recommendations

### Medium-term (6-12 months)
1. Elasticsearch integration for better search
2. Sheet music preview integration
3. Recording/performance links (YouTube, Spotify)
4. Community ratings and reviews

### Long-term (12+ months)
1. Mobile app (PWA or native)
2. Music theory analysis (key, form, techniques)
3. Collaborative playlists
4. API for third-party integrations

---

## Summary

This schema balances:
- **Performance**: Optimized indexes + denormalized search table
- **Flexibility**: Tag system + JSON fields for evolving requirements
- **Data Quality**: Verification flags + admin tools
- **Scalability**: Can handle 100k+ records with proper indexes
- **Maintainability**: Clear structure, documented, industry-standard patterns

**Estimated Performance** (AWS Lightsail 2GB RAM):
- Search queries: 10-50ms
- Composer listing: 5-10ms
- Work detail: < 5ms
- Can handle 100+ concurrent users with proper caching
