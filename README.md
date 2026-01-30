# Classical Guitar Music Database - Backend

Django REST API for the Classical Guitar Music Database project.

## Tech Stack

- **Python**: 3.12.6
- **Django**: 6.0.1
- **Django REST Framework**: 3.16.1
- **Database**: MySQL
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)

## Project Structure

```
cgmd/
├── cgmd_backend/          # Django project settings
├── music/                 # Main app for music data models
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (not in git)
├── .env.example          # Example environment file
└── README.md            # This file
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update the database credentials:

```bash
cp .env.example .env
```

Edit `.env` with your MySQL credentials.

### 5. Create MySQL Database

```bash
mysql -u root -p
```

```sql
CREATE DATABASE cgmd CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

### 6. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Run Development Server

```bash
python manage.py runserver
```

The API will be available at: http://localhost:8000/

The admin portal will be at: http://localhost:8000/admin/

## Database Models

- **Country**: Countries lookup table
- **InstrumentationCategory**: Instrument grouping categories
- **DataSource**: Track data sources (Sheerpluck, IMSLP, etc.)
- **Composer**: Composer information
- **ComposerAlias**: Alternative composer name spellings
- **Work**: Musical works/pieces
- **Tag**: Flexible categorization tags
- **WorkTag**: Many-to-many relationship between works and tags
- **WorkSearchIndex**: Denormalized search optimization table

## Next Steps

- [ ] Create serializers for API endpoints
- [ ] Set up REST API views and routes
- [ ] Implement data import pipeline for Sheerpluck CSV
- [ ] Configure CORS for frontend integration
- [ ] Set up API documentation with drf-spectacular

## Development Notes

- Database schema is designed for MySQL with full-text search support
- Models include auto-normalization for searchable fields
- Admin interface is configured with custom filtering and search
