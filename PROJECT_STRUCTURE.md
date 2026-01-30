# Classical Guitar Music Database - Project Structure

This document describes the organization of the project files and directories.

## Directory Structure

```
cgmd/
├── cgmd_backend/          # Django project configuration
│   ├── __init__.py
│   ├── settings.py       # Main settings (database, apps, middleware)
│   ├── urls.py           # Main URL routing (API + admin)
│   ├── wsgi.py           # WSGI application for deployment
│   └── asgi.py           # ASGI application for async
│
├── music/                # Main Django app for music database
│   ├── migrations/       # Database migrations
│   │   └── 0001_initial.py
│   ├── management/       # Custom management commands
│   │   └── commands/
│   │       └── import_sheerpluck.py  # Data import command
│   ├── __init__.py
│   ├── admin.py          # Django admin configuration
│   ├── apps.py           # App configuration
│   ├── models.py         # Database models (9 models)
│   ├── serializers.py    # REST API serializers
│   ├── views.py          # REST API viewsets
│   ├── urls.py           # API URL routing
│   ├── utils.py          # Data cleaning utilities
│   └── tests.py          # Unit and integration tests
│
├── frontend/             # React + TypeScript frontend
│   ├── src/
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Page components
│   │   │   ├── HomePage.tsx
│   │   │   ├── ComposerListPage.tsx
│   │   │   ├── ComposerDetailPage.tsx
│   │   │   ├── WorkDetailPage.tsx
│   │   │   └── SearchPage.tsx
│   │   ├── services/     # API service layer
│   │   │   ├── api.ts    # Axios configuration
│   │   │   └── index.ts  # Service functions
│   │   ├── types/        # TypeScript type definitions
│   │   │   └── index.ts  # Model interfaces
│   │   ├── utils/        # Utility functions
│   │   ├── hooks/        # Custom React hooks
│   │   ├── App.tsx       # Main app with routing
│   │   └── main.tsx      # Entry point
│   ├── public/           # Static assets
│   ├── .env              # Development environment variables
│   ├── .env.production   # Production environment variables
│   ├── package.json      # NPM dependencies and scripts
│   ├── tsconfig.json     # TypeScript configuration
│   ├── vite.config.ts    # Vite build configuration
│   └── README.md         # Frontend documentation
│
├── docs/                 # Project documentation
│   ├── API_DESIGN.md            # Original API design spec
│   ├── API_DOCUMENTATION.md     # Complete API reference
│   ├── IMPORT_GUIDE.md          # Data import instructions
│   ├── PHASE3_SUMMARY.md        # Phase 3 completion summary
│   ├── ROADMAP.md               # Project roadmap and progress
│   └── SCHEMA_DOCUMENTATION.md  # Database schema documentation
│
├── data/                 # Data files
│   ├── database_schema.sql      # MySQL schema definition
│   └── sheerpluck_data.csv      # Source data (67K+ works)
│
├── scripts/              # Utility scripts
│   └── setup.sh          # Unix/Linux/Mac/Git Bash setup script
│
├── venv/                 # Python virtual environment (not in git)
│
├── .vscode/              # VS Code configuration
│   └── settings.json     # Python interpreter settings
│
├── .env                  # Environment variables (not in git)
├── .env.example          # Example environment configuration
├── .gitignore            # Git ignore rules
├── manage.py             # Django management script
├── PROJECT_STRUCTURE.md  # This file
├── README.md             # Main project documentation
└── requirements.txt      # Python dependencies

```

## Core Files

### Configuration

- **`.env`**: Environment variables (database credentials, secrets)
- **`.env.example`**: Template for environment configuration
- **`requirements.txt`**: Python package dependencies
- **`cgmd_backend/settings.py`**: Django settings (database, REST framework, CORS)

### Application Code

- **`music/models.py`**: Database models
  - Country, InstrumentationCategory, DataSource
  - Composer, ComposerAlias
  - Work, Tag, WorkTag, WorkSearchIndex

- **`music/serializers.py`**: REST API serializers
  - List serializers (lightweight)
  - Detail serializers (full data)

- **`music/views.py`**: REST API viewsets
  - ComposerViewSet, WorkViewSet
  - CountryViewSet, InstrumentationCategoryViewSet
  - TagViewSet, StatsViewSet

- **`music/admin.py`**: Django admin customization
  - Custom list displays
  - Inline editing
  - Search and filter configuration

- **`music/utils.py`**: Data processing utilities
  - Name normalization
  - Year parsing
  - Country name mapping

### Data Management

- **`music/management/commands/import_sheerpluck.py`**: Import command
  - CSV parsing
  - Batch processing
  - Deduplication logic
  - Progress tracking

### Documentation

- **`docs/API_DOCUMENTATION.md`**: Complete API reference with examples
- **`docs/IMPORT_GUIDE.md`**: Data import instructions
- **`docs/ROADMAP.md`**: Project phases and progress tracking
- **`docs/SCHEMA_DOCUMENTATION.md`**: Database design documentation
- **`README.md`**: Quick start and setup guide

### Scripts

- **`scripts/setup.sh`**: Automated setup for Unix/Linux/Mac/Git Bash

## File Naming Conventions

### Python Files
- **Models**: Singular nouns (e.g., `Composer`, `Work`)
- **Serializers**: `<Model>Serializer` or `<Model>ListSerializer`
- **ViewSets**: `<Model>ViewSet`
- **Tests**: `test_<feature>.py` or organized in `tests/` directory

### Documentation
- **Uppercase with underscores**: `API_DOCUMENTATION.md`
- **Descriptive names**: Clearly indicate content
- **Markdown format**: All docs use `.md` extension

### Data Files
- **Lowercase with underscores**: `sheerpluck_data.csv`
- **Descriptive names**: Include source and format

## Import Paths

When importing from the project:

```python
# Models
from music.models import Composer, Work

# Serializers
from music.serializers import ComposerDetailSerializer

# Utilities
from music.utils import normalize_name, clean_year
```

## URLs Structure

### API Endpoints
```
/api/composers/          # Composer list and search
/api/works/              # Work list and search
/api/countries/          # Country reference data
/api/instrumentations/   # Instrumentation categories
/api/tags/               # Tags
/api/stats/summary/      # Database statistics
```

### Admin
```
/admin/                  # Django admin interface
```

### API Documentation
```
/api/docs/               # Swagger UI
/api/redoc/              # ReDoc
/api/schema/             # OpenAPI schema
```

## Data Flow

### Import Process
```
data/sheerpluck_data.csv
    ↓
music/management/commands/import_sheerpluck.py
    ↓
music/utils.py (data cleaning)
    ↓
music/models.py (database)
```

### API Request Flow
```
Client Request
    ↓
cgmd_backend/urls.py (routing)
    ↓
music/urls.py (API routing)
    ↓
music/views.py (viewset)
    ↓
music/models.py (database query)
    ↓
music/serializers.py (formatting)
    ↓
JSON Response
```

## Development Workflow

### 1. Setup
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 2. Import Data
```bash
python manage.py import_sheerpluck
```

### 3. Run Development Server
```bash
python manage.py runserver
```

### 4. Access Services
- API: http://localhost:8000/api/
- Admin: http://localhost:8000/admin/
- Docs: http://localhost:8000/api/docs/

## Testing

### Run All Tests
```bash
python manage.py test
```

### Run Specific Tests
```bash
python manage.py test music.tests.DataCleaningTests
python manage.py test music.tests.APITests
```

### Test Coverage
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

## Deployment Structure

For production deployment, the structure remains the same but with additional files:

```
cgmd/
├── staticfiles/          # Collected static files (after collectstatic)
├── logs/                 # Application logs
├── .env.production       # Production environment variables
└── gunicorn_config.py    # Gunicorn configuration
```

## Git Ignore

Files excluded from version control:
- `venv/` - Virtual environment
- `.env` - Environment variables
- `*.pyc` - Python bytecode
- `__pycache__/` - Python cache
- `db.sqlite3` - SQLite database (development)
- `staticfiles/` - Collected static files

## Database Files

### Migrations
- Located in `music/migrations/`
- Version controlled
- Applied with `python manage.py migrate`

### Schema
- SQL definition in `data/database_schema.sql`
- Used for reference and MySQL setup
- Django migrations take precedence

## Documentation Organization

### User-Facing
- `README.md` - Quick start guide
- `docs/API_DOCUMENTATION.md` - API usage

### Developer-Facing
- `docs/SCHEMA_DOCUMENTATION.md` - Database design
- `docs/IMPORT_GUIDE.md` - Data import process
- `PROJECT_STRUCTURE.md` - This file

### Project Management
- `docs/ROADMAP.md` - Development phases
- `docs/PHASE3_SUMMARY.md` - Progress tracking

## Best Practices

### Adding New Features

1. **Models**: Add to `music/models.py`
2. **Migrations**: `python manage.py makemigrations`
3. **Serializers**: Add to `music/serializers.py`
4. **Views**: Add to `music/views.py`
5. **URLs**: Register in `music/urls.py`
6. **Tests**: Add to `music/tests.py`
7. **Documentation**: Update relevant docs

### Code Organization

- Keep models focused and single-purpose
- Use serializers for data transformation
- Implement business logic in models or utils
- Keep views thin (delegate to models/utils)
- Write tests for all new features

### Documentation

- Update API_DOCUMENTATION.md for new endpoints
- Update ROADMAP.md when completing phases
- Add docstrings to all functions/classes
- Include examples in documentation

## Maintenance

### Regular Tasks

- Review and update dependencies
- Run database backups
- Monitor error logs
- Update documentation
- Review and merge data imports

### Files to Monitor

- `requirements.txt` - Dependency versions
- `music/migrations/` - Database schema changes
- `.env` - Configuration changes
- `docs/ROADMAP.md` - Project progress

## Resources

- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- MySQL Documentation: https://dev.mysql.com/doc/

## Support

For questions about the project structure:
1. Check this document
2. Review the README.md
3. Check individual documentation in `docs/`
4. Review code comments and docstrings
