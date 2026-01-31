# Classical Guitar Music Database

A comprehensive database of classical guitar repertoire with Django REST API backend and React TypeScript frontend.

## 📁 Project Structure

```
cgmd/
├── cgmd_backend/      # Django project settings
├── music/             # Django app (models, views, serializers, admin)
├── frontend/          # React + TypeScript frontend
├── docs/              # Documentation
├── data/              # Data files and schema
├── scripts/           # Setup and utility scripts
└── README.md          # This file
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed organization.

## Tech Stack

### Backend
- **Python**: 3.12.6
- **Django**: 6.0.1
- **Django REST Framework**: 3.16.1
- **Database**: MySQL with utf8mb4
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)

### Frontend
- **React**: 18
- **TypeScript**: 5.2+
- **React Router**: 6
- **Axios**: API client
- **Vite**: Build tool
- **Deployment**: GitHub Pages

## Quick Start

### Backend Setup

1. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your MySQL credentials
```

4. **Create Database**
```bash
mysql -u root -p cgmd < data/database_schema.sql
```

5. **Run Migrations**
```bash
python manage.py migrate
python manage.py createsuperuser
```

6. **Import Data**
```bash
python manage.py import_sheerpluck
```

7. **Start Backend Server**
```bash
python manage.py runserver
```

Backend runs at: http://localhost:8000/api/

### Frontend Setup

1. **Install Dependencies**
```bash
cd frontend
npm install
```

2. **Start Dev Server**
```bash
npm run dev
```

Frontend runs at: http://localhost:3000

## API Endpoints

- `/api/composers/` - List and search composers
- `/api/works/` - List and search works
- `/api/composers/{id}/` - Composer details
- `/api/works/{id}/` - Work details
- `/api/stats/summary/` - Database statistics
- `/api/docs/` - Interactive API documentation (Swagger)

See [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) for complete reference.

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

### Import Sheerpluck Data

```bash
python manage.py import_sheerpluck
```

See [IMPORT_GUIDE.md](docs/IMPORT_GUIDE.md) for detailed import instructions.

### Build REST API

- [ ] Create serializers for API endpoints
- [ ] Set up REST API views and routes
- [ ] Configure CORS for frontend integration
- [ ] Set up API documentation with drf-spectacular

## Management Commands

### import_sheerpluck

Import classical guitar repertoire data from Sheerpluck CSV.

```bash
# Basic import
python manage.py import_sheerpluck

# Dry run (validate without saving)
python manage.py import_sheerpluck --dry-run

# Skip existing works
python manage.py import_sheerpluck --skip-existing

# Custom CSV path
python manage.py import_sheerpluck /path/to/data.csv
```

## Development Notes

- Database schema is designed for MySQL with full-text search support
- Models include auto-normalization for searchable fields
- Admin interface is configured with custom filtering and search

## Phase 4 - Frontend Complete! ✅

**Completed**:
- React + TypeScript app with Vite
- 5 pages: Home, Composers List/Detail, Work Detail, Search
- API service layer with type-safe interfaces  
- React Router configuration
- GitHub Pages deployment ready

**Next**: Test with backend, add styling, deploy to production

## Development Commands

**Backend**:
```bash
python manage.py runserver          # Start server
python manage.py import_sheerpluck  # Import data
python manage.py test               # Run tests
```

**Frontend**:
```bash
cd frontend
npm run dev        # Dev server (localhost:3000)
npm run build      # Production build
npm run deploy     # Deploy to GitHub Pages
```

See [docs/ROADMAP.md](docs/ROADMAP.md) for full project plan.
