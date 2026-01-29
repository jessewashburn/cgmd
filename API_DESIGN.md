# Classical Guitar Database - API Design

**Version**: 1.0  
**Base URL**: `https://api.baltimoreклассicalguitar.org/v1`  
**Protocol**: HTTPS only  
**Format**: JSON  

---

## Table of Contents
1. [API Versioning](#api-versioning)
2. [Authentication](#authentication)
3. [Pagination](#pagination)
4. [Filtering & Search](#filtering--search)
5. [Response Format](#response-format)
6. [Error Handling](#error-handling)
7. [Endpoints](#endpoints)
8. [Rate Limiting](#rate-limiting)
9. [CORS Policy](#cors-policy)

---

## API Versioning

### Strategy: URL Path Versioning

**Format**: `/v{major}/resource`

**Example**: `/v1/composers`, `/v2/composers`

### Versioning Policy

- **Major version** (v1, v2): Breaking changes
  - Changed response structure
  - Removed fields
  - Changed endpoint paths
  - Changed authentication methods

- **Minor updates**: Non-breaking changes (no version bump needed)
  - New optional fields
  - New endpoints
  - New query parameters
  - Performance improvements

### Version Support
- Current version: **v1**
- Support window: 12 months after new major version release
- Deprecation notice: 6 months before sunset
- Legacy endpoints return deprecation headers:
  ```
  X-API-Deprecated: true
  X-API-Sunset: 2027-01-01
  X-API-Migration-Guide: https://api.example.org/docs/migration/v1-to-v2
  ```

---

## Authentication

### Public API (Read-Only)
- **No authentication required** for public endpoints
- Rate limiting applies (see [Rate Limiting](#rate-limiting))

### Admin API (Write Operations)
- **Token-based authentication** (Django REST Framework tokens)
- Required for: creating, updating, deleting records
- Header: `Authorization: Token {api_token}`

### Future: API Keys (For Partners)
- Optional API keys for higher rate limits
- Header: `X-API-Key: {api_key}`

---

## Pagination

### Strategy: Offset-based Pagination

**Default page size**: 20 items  
**Maximum page size**: 100 items

### Request Parameters
```
?limit=20         # Number of items per page (max 100)
?offset=0         # Starting position
```

### Response Format
```json
{
  "count": 67164,
  "next": "https://api.example.org/v1/works/?limit=20&offset=20",
  "previous": null,
  "results": [...]
}
```

### Example Usage
```bash
# Page 1 (items 1-20)
GET /v1/works/?limit=20&offset=0

# Page 2 (items 21-40)
GET /v1/works/?limit=20&offset=20

# Page 3 (items 41-60)
GET /v1/works/?limit=20&offset=40
```

### Alternative: Cursor Pagination (Future Enhancement)
For very large datasets or real-time feeds:
```json
{
  "next": "https://api.example.org/v1/works/?cursor=cD00Mg==",
  "previous": "https://api.example.org/v1/works/?cursor=cD0xNQ==",
  "results": [...]
}
```

---

## Filtering & Search

### General Filtering

**Pattern**: `?field__lookup=value`

#### Supported Lookups

| Lookup | Description | Example |
|--------|-------------|---------|
| `exact` | Exact match (default) | `?country=Spain` |
| `iexact` | Case-insensitive exact | `?country__iexact=spain` |
| `contains` | Contains substring | `?title__contains=Prelude` |
| `icontains` | Case-insensitive contains | `?title__icontains=prelude` |
| `startswith` | Starts with | `?last_name__startswith=Bach` |
| `in` | In list | `?id__in=1,2,3,4,5` |
| `gt` / `gte` | Greater than (or equal) | `?birth_year__gte=1900` |
| `lt` / `lte` | Less than (or equal) | `?composition_year__lt=1850` |
| `isnull` | Is null/empty | `?death_year__isnull=true` |

#### Combining Filters
Multiple filters use AND logic:
```
/v1/composers/?country=Spain&birth_year__gte=1900&is_living=true
```

Returns: Spanish composers born 1900 or later who are still living

### Full-Text Search

**Endpoint**: `/v1/search/`

**Parameter**: `?q={query}`

**Behavior**:
- Searches across composer names, work titles, descriptions
- Returns ranked results by relevance
- Uses MySQL FULLTEXT search with InnoDB

**Example**:
```bash
GET /v1/search/?q=Bach+guitar+prelude
```

**Response**:
```json
{
  "query": "Bach guitar prelude",
  "count": 42,
  "results": [
    {
      "type": "work",
      "id": 1234,
      "title": "Prelude in D minor, BWV 999",
      "composer": {
        "id": 56,
        "name": "Bach, Johann Sebastian"
      },
      "relevance_score": 8.5,
      "url": "/v1/works/1234/"
    },
    ...
  ]
}
```

### Search-Specific Endpoints

#### Composer Search
```bash
GET /v1/search/composers/?q=Albeniz
```

#### Work Search
```bash
GET /v1/search/works/?q=sonata
```

### Advanced Filtering Examples

#### Works by Spanish composers from the 20th century
```bash
GET /v1/works/?composer__country=Spain&composition_year__gte=1900&composition_year__lt=2000
```

#### Solo guitar works for beginners
```bash
GET /v1/works/?instrumentation=Solo&difficulty_level__lte=3
```

#### Living composers from Latin America
```bash
GET /v1/composers/?is_living=true&country__in=Argentina,Brazil,Mexico,Chile
```

#### Works with video recordings
```bash
GET /v1/works/?youtube_url__isnull=false
```

---

## Response Format

### Success Response Structure

#### Single Resource
```json
{
  "id": 123,
  "field1": "value1",
  "field2": "value2",
  ...
}
```

#### List of Resources
```json
{
  "count": 1000,
  "next": "https://api.example.org/v1/resource/?offset=20",
  "previous": null,
  "results": [
    {
      "id": 1,
      "field": "value"
    },
    ...
  ]
}
```

### Standard Headers
```
Content-Type: application/json; charset=utf-8
X-API-Version: 1.0
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1643723400
```

### HATEOAS Links (Future Enhancement)
```json
{
  "id": 123,
  "title": "Prelude",
  "_links": {
    "self": "/v1/works/123/",
    "composer": "/v1/composers/45/",
    "similar": "/v1/works/123/similar/"
  }
}
```

---

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "not_found",
    "message": "Composer with id 99999 not found",
    "details": {},
    "timestamp": "2026-01-29T14:30:00Z"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid parameters, validation errors |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Maintenance mode |

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `invalid_request` | 400 | Malformed request |
| `validation_error` | 400 | Field validation failed |
| `not_found` | 404 | Resource not found |
| `rate_limit_exceeded` | 429 | Too many requests |
| `unauthorized` | 401 | Authentication required |
| `forbidden` | 403 | Insufficient permissions |
| `internal_error` | 500 | Server error |

### Validation Error Example
```json
{
  "error": {
    "code": "validation_error",
    "message": "Validation failed",
    "details": {
      "birth_year": ["Must be between 1000 and 2100"],
      "country": ["This field is required"]
    },
    "timestamp": "2026-01-29T14:30:00Z"
  }
}
```

---

## Endpoints

### Base URL
```
https://api.baltimoreклассicalguitar.org/v1
```

---

## 1. Composers

### List Composers
**GET** `/v1/composers/`

Returns paginated list of composers.

**Query Parameters**:
- `limit` (int): Items per page (default: 20, max: 100)
- `offset` (int): Offset for pagination (default: 0)
- `ordering` (string): Sort field (`last_name`, `-birth_year`, `works_count`)
- `country` (string): Filter by country name
- `birth_year__gte` (int): Born on or after year
- `birth_year__lte` (int): Born on or before year
- `death_year__gte` (int): Died on or after year
- `death_year__lte` (int): Died on or before year
- `is_living` (bool): Filter living composers
- `period` (string): Filter by period (Renaissance, Baroque, Classical, Romantic, Modern, Contemporary)
- `search` (string): Search by name

**Example Request**:
```bash
GET /v1/composers/?country=Spain&birth_year__gte=1900&ordering=-birth_year&limit=20
```

**Example Response**:
```json
{
  "count": 234,
  "next": "https://api.example.org/v1/composers/?limit=20&offset=20&country=Spain",
  "previous": null,
  "results": [
    {
      "id": 42,
      "full_name": "Tárrega, Francisco",
      "first_name": "Francisco",
      "last_name": "Tárrega",
      "birth_year": 1852,
      "death_year": 1909,
      "is_living": false,
      "country": {
        "id": 45,
        "name": "Spain"
      },
      "period": "Romantic",
      "works_count": 78,
      "biography_excerpt": "Spanish composer and classical guitarist...",
      "url": "/v1/composers/42/"
    },
    ...
  ]
}
```

---

### Get Composer Detail
**GET** `/v1/composers/{id}/`

Returns detailed information about a specific composer.

**Path Parameters**:
- `id` (int): Composer ID

**Example Request**:
```bash
GET /v1/composers/42/
```

**Example Response**:
```json
{
  "id": 42,
  "full_name": "Tárrega, Francisco",
  "first_name": "Francisco",
  "last_name": "Tárrega",
  "birth_year": 1852,
  "death_year": 1909,
  "is_living": false,
  "country": {
    "id": 45,
    "name": "Spain",
    "iso_code": "ES"
  },
  "country_description": null,
  "period": "Romantic",
  "biography": "Francisco Tárrega was a Spanish composer and classical guitarist...",
  "works_count": 78,
  "aliases": [
    "Tarrega, Francisco",
    "Francisco Tárrega Eixea"
  ],
  "external_links": {
    "imslp": "https://imslp.org/wiki/Category:Tárrega,_Francisco",
    "wikipedia": "https://en.wikipedia.org/wiki/Francisco_Tárrega"
  },
  "statistics": {
    "total_works": 78,
    "total_views": 12453,
    "avg_difficulty": 6.5,
    "earliest_work_year": 1875,
    "latest_work_year": 1909
  },
  "is_verified": true,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-28T16:45:00Z"
}
```

---

### Get Composer's Works
**GET** `/v1/composers/{id}/works/`

Returns all works by a specific composer.

**Path Parameters**:
- `id` (int): Composer ID

**Query Parameters**:
- All standard work filters (instrumentation, year, difficulty, etc.)
- `ordering`: Sort by (`title`, `composition_year`, `-view_count`)

**Example Request**:
```bash
GET /v1/composers/42/works/?instrumentation=Solo&ordering=title
```

**Example Response**:
```json
{
  "count": 52,
  "next": "https://api.example.org/v1/composers/42/works/?offset=20",
  "previous": null,
  "composer": {
    "id": 42,
    "full_name": "Tárrega, Francisco"
  },
  "results": [
    {
      "id": 1234,
      "title": "Recuerdos de la Alhambra",
      "composition_year": 1896,
      "instrumentation": "Solo",
      "difficulty_level": 8,
      "view_count": 8543,
      "url": "/v1/works/1234/"
    },
    ...
  ]
}
```

---

## 2. Works

### List Works
**GET** `/v1/works/`

Returns paginated list of works.

**Query Parameters**:
- `limit` (int): Items per page
- `offset` (int): Offset for pagination
- `ordering` (string): Sort field (`title`, `-view_count`, `composition_year`)
- `composer` (int): Filter by composer ID
- `composer__country` (string): Filter by composer's country
- `instrumentation` (string): Filter by instrumentation category
- `composition_year__gte` (int): Composed on or after
- `composition_year__lte` (int): Composed on or before
- `difficulty_level__lte` (int): Maximum difficulty (1-10)
- `has_youtube` (bool): Has YouTube link
- `has_imslp` (bool): Has IMSLP link
- `search` (string): Search by title

**Example Request**:
```bash
GET /v1/works/?instrumentation=Solo&difficulty_level__lte=5&ordering=-view_count&limit=20
```

**Example Response**:
```json
{
  "count": 8923,
  "next": "https://api.example.org/v1/works/?instrumentation=Solo&limit=20&offset=20",
  "previous": null,
  "results": [
    {
      "id": 1234,
      "title": "Recuerdos de la Alhambra",
      "subtitle": null,
      "composer": {
        "id": 42,
        "full_name": "Tárrega, Francisco",
        "country": "Spain"
      },
      "composition_year": 1896,
      "instrumentation": "Solo",
      "difficulty_level": 8,
      "duration_minutes": 4,
      "key_signature": "A minor",
      "view_count": 8543,
      "tags": ["tremolo", "romantic", "spanish"],
      "url": "/v1/works/1234/"
    },
    ...
  ]
}
```

---

### Get Work Detail
**GET** `/v1/works/{id}/`

Returns detailed information about a specific work.

**Path Parameters**:
- `id` (int): Work ID

**Example Request**:
```bash
GET /v1/works/1234/
```

**Example Response**:
```json
{
  "id": 1234,
  "title": "Recuerdos de la Alhambra",
  "subtitle": null,
  "composer": {
    "id": 42,
    "full_name": "Tárrega, Francisco",
    "birth_year": 1852,
    "death_year": 1909,
    "country": "Spain",
    "url": "/v1/composers/42/"
  },
  "opus_number": null,
  "catalog_number": null,
  "composition_year": 1896,
  "composition_year_approx": false,
  "instrumentation": {
    "id": 1,
    "name": "Solo",
    "description": "Solo classical guitar"
  },
  "instrumentation_detail": "Solo guitar",
  "difficulty_level": 8,
  "duration_minutes": 4,
  "key_signature": "A minor",
  "description": "One of the most famous pieces in the classical guitar repertoire, featuring the tremolo technique throughout.",
  "movements": null,
  "tags": [
    {
      "id": 12,
      "name": "tremolo",
      "category": "technique"
    },
    {
      "id": 34,
      "name": "romantic",
      "category": "period"
    },
    {
      "id": 56,
      "name": "spanish",
      "category": "style"
    }
  ],
  "external_links": {
    "imslp": "https://imslp.org/wiki/Recuerdos_de_la_Alhambra_(T%C3%A1rrega,_Francisco)",
    "youtube": "https://youtube.com/watch?v=example",
    "score": null
  },
  "view_count": 8543,
  "is_verified": true,
  "is_public": true,
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-28T16:45:00Z"
}
```

---

### Increment Work View Count
**POST** `/v1/works/{id}/view/`

Increments the view count for a work (for analytics).

**Path Parameters**:
- `id` (int): Work ID

**Example Request**:
```bash
POST /v1/works/1234/view/
```

**Example Response**:
```json
{
  "id": 1234,
  "view_count": 8544
}
```

---

## 3. Search

### Universal Search
**GET** `/v1/search/`

Searches across all resources (composers, works).

**Query Parameters**:
- `q` (string, required): Search query
- `limit` (int): Results per page (default: 20, max: 100)
- `offset` (int): Offset for pagination
- `type` (string): Filter by type (`composer`, `work`)

**Example Request**:
```bash
GET /v1/search/?q=Bach+guitar+prelude&limit=10
```

**Example Response**:
```json
{
  "query": "Bach guitar prelude",
  "count": 42,
  "next": "https://api.example.org/v1/search/?q=Bach+guitar+prelude&offset=10",
  "previous": null,
  "results": [
    {
      "type": "work",
      "id": 5678,
      "title": "Prelude in D minor, BWV 999",
      "composer": {
        "id": 123,
        "name": "Bach, Johann Sebastian"
      },
      "instrumentation": "Solo",
      "year": 1720,
      "relevance_score": 9.2,
      "url": "/v1/works/5678/"
    },
    {
      "type": "composer",
      "id": 123,
      "name": "Bach, Johann Sebastian",
      "birth_year": 1685,
      "death_year": 1750,
      "country": "Germany",
      "works_count": 23,
      "relevance_score": 8.7,
      "url": "/v1/composers/123/"
    },
    ...
  ]
}
```

---

### Search Composers
**GET** `/v1/search/composers/`

Searches only composers.

**Query Parameters**:
- `q` (string, required): Search query
- `limit`, `offset`: Pagination

**Example Request**:
```bash
GET /v1/search/composers/?q=villa+lobos
```

**Example Response**:
```json
{
  "query": "villa lobos",
  "count": 2,
  "results": [
    {
      "id": 789,
      "full_name": "Villa-Lobos, Heitor",
      "birth_year": 1887,
      "death_year": 1959,
      "country": "Brazil",
      "works_count": 145,
      "relevance_score": 9.8,
      "url": "/v1/composers/789/"
    }
  ]
}
```

---

### Search Works
**GET** `/v1/search/works/`

Searches only works.

**Query Parameters**:
- `q` (string, required): Search query
- `limit`, `offset`: Pagination
- Additional filters: `instrumentation`, `composer__country`, etc.

**Example Request**:
```bash
GET /v1/search/works/?q=sonata&instrumentation=Solo
```

**Example Response**:
```json
{
  "query": "sonata",
  "count": 234,
  "filters": {
    "instrumentation": "Solo"
  },
  "results": [
    {
      "id": 3456,
      "title": "Sonata",
      "composer": {
        "id": 234,
        "name": "Ponce, Manuel"
      },
      "instrumentation": "Solo",
      "year": 1928,
      "difficulty_level": 9,
      "relevance_score": 8.5,
      "url": "/v1/works/3456/"
    },
    ...
  ]
}
```

---

## 4. Reference Data

### List Countries
**GET** `/v1/countries/`

Returns list of all countries in the database.

**Query Parameters**:
- `ordering`: Sort by (`name`, `-composers_count`)

**Example Response**:
```json
{
  "count": 92,
  "results": [
    {
      "id": 45,
      "name": "Spain",
      "iso_code": "ES",
      "composers_count": 342,
      "works_count": 4523
    },
    {
      "id": 12,
      "name": "Brazil",
      "iso_code": "BR",
      "composers_count": 156,
      "works_count": 2341
    },
    ...
  ]
}
```

---

### List Instrumentation Categories
**GET** `/v1/instrumentations/`

Returns list of all instrumentation categories.

**Example Response**:
```json
{
  "count": 21,
  "results": [
    {
      "id": 1,
      "name": "Solo",
      "description": "Solo classical guitar",
      "works_count": 23456
    },
    {
      "id": 2,
      "name": "Duo",
      "description": "Two instruments including guitar",
      "works_count": 3421
    },
    ...
  ]
}
```

---

### List Tags
**GET** `/v1/tags/`

Returns list of all tags.

**Query Parameters**:
- `category` (string): Filter by category (genre, style, technique, form)
- `ordering`: Sort by (`name`, `-usage_count`)

**Example Response**:
```json
{
  "count": 156,
  "results": [
    {
      "id": 12,
      "name": "tremolo",
      "slug": "tremolo",
      "category": "technique",
      "usage_count": 234,
      "description": "Technique using rapid repetition of a single note"
    },
    {
      "id": 34,
      "name": "romantic",
      "slug": "romantic",
      "category": "period",
      "usage_count": 1823,
      "description": "Romantic period (1820-1900)"
    },
    ...
  ]
}
```

---

## 5. Statistics & Analytics

### Popular Works
**GET** `/v1/stats/popular/`

Returns most viewed works.

**Query Parameters**:
- `limit` (int): Number of results (default: 20, max: 100)
- `period` (string): Time period (`day`, `week`, `month`, `year`, `all`)

**Example Response**:
```json
{
  "period": "month",
  "results": [
    {
      "id": 1234,
      "title": "Recuerdos de la Alhambra",
      "composer": "Tárrega, Francisco",
      "view_count": 8543,
      "url": "/v1/works/1234/"
    },
    ...
  ]
}
```

---

### Composer Statistics
**GET** `/v1/stats/composers/`

Returns composer statistics (most works, most viewed, etc.).

**Query Parameters**:
- `order_by` (string): `works_count`, `views`, `avg_difficulty`
- `limit` (int): Number of results

**Example Response**:
```json
{
  "order_by": "works_count",
  "results": [
    {
      "id": 789,
      "full_name": "Villa-Lobos, Heitor",
      "country": "Brazil",
      "works_count": 145,
      "total_views": 45234,
      "avg_difficulty": 7.5
    },
    ...
  ]
}
```

---

### Database Statistics
**GET** `/v1/stats/database/`

Returns overall database statistics.

**Example Response**:
```json
{
  "composers": {
    "total": 4523,
    "living": 1234,
    "verified": 4012
  },
  "works": {
    "total": 67164,
    "verified": 58234,
    "with_youtube": 12345,
    "with_imslp": 34567
  },
  "countries": {
    "total": 92,
    "top_5": [
      {"name": "Spain", "composers": 342},
      {"name": "USA", "composers": 298},
      {"name": "Italy", "composers": 245},
      {"name": "France", "composers": 223},
      {"name": "Germany", "composers": 198}
    ]
  },
  "instrumentations": {
    "total": 21,
    "top_5": [
      {"name": "Solo", "works": 23456},
      {"name": "Chamber Music", "works": 12345},
      {"name": "Duo", "works": 8901},
      {"name": "Trio", "works": 5678},
      {"name": "Concerto", "works": 3456}
    ]
  },
  "last_updated": "2026-01-29T10:00:00Z"
}
```

---

## Rate Limiting

### Limits

**Anonymous requests**:
- 1000 requests per hour per IP
- 60 requests per minute per IP

**Authenticated requests** (future):
- 5000 requests per hour per token
- 100 requests per minute per token

**API Key holders** (future):
- 10000 requests per hour
- 200 requests per minute

### Headers
Every response includes rate limit information:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1643723400
```

### Rate Limit Exceeded Response
**HTTP 429 Too Many Requests**

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "details": {
      "limit": 1000,
      "remaining": 0,
      "reset_at": "2026-01-29T15:00:00Z"
    }
  }
}
```

---

## CORS Policy

### Allowed Origins
- `https://baltimoreклассicalguitar.org` (production frontend)
- `http://localhost:3000` (development)
- `http://localhost:5173` (Vite development)

### Allowed Methods
```
GET, POST, PUT, PATCH, DELETE, OPTIONS
```

### Allowed Headers
```
Authorization, Content-Type, X-API-Key
```

### Preflight Cache
```
Access-Control-Max-Age: 86400
```

---

## Implementation Notes

### Django REST Framework Setup

```python
# settings.py

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 100,
    
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '1000/hour',
        'user': '5000/hour',
    },
    
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    
    'EXCEPTION_HANDLER': 'cgmd.api.exceptions.custom_exception_handler',
}

# CORS
CORS_ALLOWED_ORIGINS = [
    "https://baltimoreклassicalguitar.org",
    "http://localhost:3000",
    "http://localhost:5173",
]
```

### URL Structure

```python
# urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'composers', ComposerViewSet)
router.register(r'works', WorkViewSet)
router.register(r'countries', CountryViewSet)
router.register(r'instrumentations', InstrumentationViewSet)
router.register(r'tags', TagViewSet)

urlpatterns = [
    path('v1/', include([
        path('', include(router.urls)),
        path('search/', UniversalSearchView.as_view()),
        path('search/composers/', ComposerSearchView.as_view()),
        path('search/works/', WorkSearchView.as_view()),
        path('stats/popular/', PopularWorksView.as_view()),
        path('stats/composers/', ComposerStatsView.as_view()),
        path('stats/database/', DatabaseStatsView.as_view()),
    ])),
]
```

---

## Testing the API

### Using cURL

```bash
# List composers
curl https://api.example.org/v1/composers/

# Get specific composer
curl https://api.example.org/v1/composers/42/

# Search works
curl "https://api.example.org/v1/search/works/?q=prelude&instrumentation=Solo"

# Filter with multiple parameters
curl "https://api.example.org/v1/works/?composer__country=Spain&composition_year__gte=1900&limit=10"
```

### Using Python (requests)

```python
import requests

# Base URL
BASE_URL = "https://api.example.org/v1"

# Get composers from Spain
response = requests.get(f"{BASE_URL}/composers/", params={
    "country": "Spain",
    "birth_year__gte": 1900,
    "limit": 20
})
composers = response.json()

# Search for works
response = requests.get(f"{BASE_URL}/search/works/", params={
    "q": "sonata",
    "instrumentation": "Solo"
})
results = response.json()

# Get work detail
work_id = results['results'][0]['id']
response = requests.get(f"{BASE_URL}/works/{work_id}/")
work = response.json()
```

### Using JavaScript (fetch)

```javascript
// Base URL
const BASE_URL = 'https://api.example.org/v1';

// Get composers
async function getComposers(filters = {}) {
  const params = new URLSearchParams(filters);
  const response = await fetch(`${BASE_URL}/composers/?${params}`);
  return await response.json();
}

// Search works
async function searchWorks(query, filters = {}) {
  const params = new URLSearchParams({ q: query, ...filters });
  const response = await fetch(`${BASE_URL}/search/works/?${params}`);
  return await response.json();
}

// Usage
const spanishComposers = await getComposers({ 
  country: 'Spain', 
  birth_year__gte: 1900 
});

const soloSonatas = await searchWorks('sonata', { 
  instrumentation: 'Solo' 
});
```

---

## API Documentation Tools

### Swagger/OpenAPI (Recommended)

Use `drf-spectacular` for automatic API documentation:

```python
# settings.py
INSTALLED_APPS = [
    ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Classical Guitar Database API',
    'DESCRIPTION': 'Public API for the Baltimore Classical Guitar Society database',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

Access interactive documentation at: `https://api.example.org/v1/docs/`

---

## Future API Enhancements

### Phase 2 (Post-Launch)
1. **Autocomplete endpoint** for search suggestions
2. **Related works** recommendation endpoint
3. **Export endpoints** (PDF, CSV, BibTeX)
4. **Batch operations** for retrieving multiple resources
5. **WebSocket support** for real-time updates

### Phase 3 (Advanced Features)
1. **GraphQL API** as alternative to REST
2. **Webhooks** for data change notifications
3. **OAuth2 authentication** for third-party apps
4. **API analytics dashboard** for administrators
5. **Versioned documentation** archive

---

## Change Log

### Version 1.0 (2026-01-29)
- Initial API design
- Core endpoints for composers, works, search
- Basic filtering and pagination
- Rate limiting
- CORS configuration

---

**Maintained by**: Baltimore Classical Guitar Society  
**Contact**: api@baltimoreклassicalguitar.org  
**Documentation**: https://api.baltimoreклassicalguitar.org/v1/docs/
