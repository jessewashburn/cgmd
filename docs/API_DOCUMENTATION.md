# API Documentation

The Classical Guitar Music Database REST API provides programmatic access to classical guitar repertoire data.

## Base URL

```
Development: http://localhost:8000/api/
Production: https://your-domain.com/api/
```

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Authentication

Currently, the API is read-only and does not require authentication.

## Endpoints Overview

| Endpoint | Description |
|----------|-------------|
| `/api/composers/` | List and search composers |
| `/api/works/` | List and search musical works |
| `/api/countries/` | List countries |
| `/api/instrumentations/` | List instrumentation categories |
| `/api/tags/` | List tags |
| `/api/stats/summary/` | Database statistics |

## Composers API

### List Composers

```
GET /api/composers/
```

**Query Parameters:**
- `search` - Search in composer name
- `period` - Filter by period (Renaissance, Baroque, Classical, Romantic, Modern, Contemporary)
- `country` - Filter by country ID
- `is_living` - Filter living composers (true/false)
- `birth_year_min` - Minimum birth year
- `birth_year_max` - Maximum birth year
- `ordering` - Sort by field (`last_name`, `birth_year`, `-birth_year`)
- `page` - Page number
- `page_size` - Results per page (default: 50, max: 100)

**Example:**
```bash
curl "http://localhost:8000/api/composers/?search=bach&ordering=birth_year"
```

**Response:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "full_name": "Johann Sebastian Bach",
      "birth_year": 1685,
      "death_year": 1750,
      "is_living": false,
      "country_name": "Germany",
      "period": "Baroque",
      "work_count": 45
    }
  ]
}
```

### Get Composer Details

```
GET /api/composers/{id}/
```

**Example:**
```bash
curl "http://localhost:8000/api/composers/1/"
```

**Response:**
```json
{
  "id": 1,
  "full_name": "Johann Sebastian Bach",
  "first_name": "Johann Sebastian",
  "last_name": "Bach",
  "birth_year": 1685,
  "death_year": 1750,
  "is_living": false,
  "country": {
    "id": 1,
    "name": "Germany",
    "iso_code": "DE",
    "region": "Europe"
  },
  "biography": "German composer and musician...",
  "period": "Baroque",
  "imslp_url": "https://imslp.org/wiki/Category:Bach,_Johann_Sebastian",
  "wikipedia_url": "https://en.wikipedia.org/wiki/Johann_Sebastian_Bach",
  "work_count": 45,
  "aliases": [],
  "created_at": "2026-01-29T12:00:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

### Get Composer's Works

```
GET /api/composers/{id}/works/
```

Returns all public works by a specific composer.

### Filter by Period

```
GET /api/composers/by_period/?period=Baroque
```

### Filter by Country

```
GET /api/composers/by_country/?country_id=1
```

## Works API

### List Works

```
GET /api/works/
```

**Query Parameters:**
- `search` - Search in work title, composer name, opus number
- `composer` - Filter by composer ID
- `instrumentation_category` - Filter by instrumentation category ID
- `difficulty_level` - Filter by exact difficulty level (1-10)
- `difficulty_min` - Minimum difficulty level
- `difficulty_max` - Maximum difficulty level
- `year_min` - Minimum composition year
- `year_max` - Maximum composition year
- `ordering` - Sort by field (`title`, `composition_year`, `-view_count`)
- `page` - Page number
- `page_size` - Results per page

**Example:**
```bash
curl "http://localhost:8000/api/works/?composer=1&difficulty_max=5"
```

**Response:**
```json
{
  "count": 15,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Prelude in C Major",
      "composer_name": "Johann Sebastian Bach",
      "composition_year": 1722,
      "instrumentation_name": "Solo",
      "difficulty_level": 3,
      "opus_number": "BWV 846"
    }
  ]
}
```

### Get Work Details

```
GET /api/works/{id}/
```

Returns detailed information including tags, links, and increments view count.

**Response:**
```json
{
  "id": 1,
  "title": "Prelude in C Major",
  "subtitle": null,
  "composer": {
    "id": 1,
    "full_name": "Johann Sebastian Bach",
    "birth_year": 1685,
    "death_year": 1750,
    "country_name": "Germany",
    "work_count": 45
  },
  "opus_number": "BWV 846",
  "catalog_number": null,
  "composition_year": 1722,
  "composition_year_approx": false,
  "duration_minutes": 2,
  "key_signature": "C Major",
  "instrumentation_category": {
    "id": 1,
    "name": "Solo",
    "description": "Solo guitar",
    "sort_order": 1
  },
  "instrumentation_detail": "Solo guitar",
  "difficulty_level": 3,
  "description": "The famous prelude from the Well-Tempered Clavier...",
  "movements": null,
  "imslp_url": "https://imslp.org/...",
  "youtube_url": null,
  "score_url": null,
  "view_count": 127,
  "tags": ["Baroque", "Keyboard"],
  "created_at": "2026-01-29T12:00:00Z",
  "updated_at": "2026-01-29T12:00:00Z"
}
```

### Search Works

```
GET /api/works/search/?q=prelude
```

Advanced search across title, composer name, description, and opus number.

### Popular Works

```
GET /api/works/popular/?limit=20
```

Returns most viewed works.

### Recent Works

```
GET /api/works/recent/?limit=20
```

Returns recently added works.

### Filter by Instrumentation

```
GET /api/works/by_instrumentation/?category_id=1
```

## Countries API

### List Countries

```
GET /api/countries/
```

**Query Parameters:**
- `search` - Search in country name or ISO code
- `ordering` - Sort by `name`

**Response:**
```json
{
  "count": 100,
  "results": [
    {
      "id": 1,
      "name": "Germany",
      "iso_code": "DE",
      "region": "Europe"
    }
  ]
}
```

## Instrumentations API

### List Instrumentation Categories

```
GET /api/instrumentations/
```

**Response:**
```json
{
  "count": 50,
  "results": [
    {
      "id": 1,
      "name": "Solo",
      "description": "Solo guitar",
      "sort_order": 1
    },
    {
      "id": 2,
      "name": "Duo",
      "description": "Two guitars or guitar with another instrument",
      "sort_order": 2
    }
  ]
}
```

## Tags API

### List Tags

```
GET /api/tags/
```

**Query Parameters:**
- `search` - Search tag name
- `category` - Filter by tag category
- `ordering` - Sort by `name` or `usage_count`

### Get Works by Tag

```
GET /api/tags/{id}/works/
```

## Statistics API

### Database Summary

```
GET /api/stats/summary/
```

**Response:**
```json
{
  "total_composers": 12543,
  "total_works": 67164,
  "total_countries": 98,
  "living_composers": 8432,
  "composers_by_period": {
    "Baroque": 234,
    "Classical": 456,
    "Romantic": 1234,
    "Modern": 3456,
    "Contemporary": 7163
  },
  "works_by_instrumentation": {
    "Solo": 45123,
    "Duo": 8765,
    "Ensemble": 5432,
    "Chamber Music": 4321,
    "Orchestra": 3523
  }
}
```

## Pagination

All list endpoints support pagination:

```json
{
  "count": 67164,
  "next": "http://localhost:8000/api/works/?page=2",
  "previous": null,
  "results": [...]
}
```

**Control pagination:**
- `page` - Page number (default: 1)
- `page_size` - Results per page (default: 50, max: 100)

## Filtering

Use Django Filter Backend for precise filtering:

```
# Multiple filters
GET /api/works/?composer=1&difficulty_level=5&year_min=1900

# Exact match
GET /api/composers/?period=Baroque&is_living=false

# Range filters
GET /api/works/?year_min=1800&year_max=1900&difficulty_min=3&difficulty_max=7
```

## Searching

Use the `search` parameter for text search:

```
# Search composers
GET /api/composers/?search=mozart

# Search works
GET /api/works/?search=sonata

# Advanced work search
GET /api/works/search/?q=prelude+bach
```

## Ordering

Sort results using the `ordering` parameter:

```
# Ascending
GET /api/composers/?ordering=birth_year

# Descending (prefix with -)
GET /api/works/?ordering=-view_count

# Multiple fields
GET /api/composers/?ordering=last_name,first_name
```

## CORS

CORS is configured to allow requests from:
- Frontend development servers (localhost:3000, localhost:5173)
- GitHub Pages (production)

Configure additional origins in `.env`:
```
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.github.io
```

## Rate Limiting

Currently no rate limiting is enforced. This will be added in production.

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid parameter value"
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Examples

### Find all contemporary Spanish composers

```bash
curl "http://localhost:8000/api/composers/?period=Contemporary&country=Spain"
```

### Find easy solo guitar works from the 20th century

```bash
curl "http://localhost:8000/api/works/?difficulty_max=3&year_min=1900&year_max=1999&instrumentation_category=1"
```

### Search for works by Villa-Lobos

```bash
curl "http://localhost:8000/api/works/?search=villa-lobos"
```

### Get the most popular works

```bash
curl "http://localhost:8000/api/works/popular/?limit=10"
```

## Client Libraries

### JavaScript/TypeScript

```javascript
// Fetch all composers
const response = await fetch('http://localhost:8000/api/composers/');
const data = await response.json();

// Search works
const searchResponse = await fetch(
  'http://localhost:8000/api/works/search/?q=prelude'
);
const results = await searchResponse.json();
```

### Python

```python
import requests

# Get composer details
response = requests.get('http://localhost:8000/api/composers/1/')
composer = response.json()

# Search with filters
response = requests.get('http://localhost:8000/api/works/', params={
    'composer': 1,
    'difficulty_max': 5,
    'page_size': 20
})
works = response.json()
```

## Support

For API issues or questions:
- Check interactive docs at `/api/docs/`
- Review this documentation
- Check Django logs for errors
- See [README.md](README.md) for setup help
