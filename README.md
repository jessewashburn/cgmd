# Solmu - Guitar Music Network

Our repertoire, connected.

A modern web application for browsing and exploring classical guitar music, composers, and works.

## Project Structure

```
.
├── backend/
│   ├── cgmd_backend/         # Django project settings
│   ├── music/                # Main Django app
│   │   ├── models.py         # Database models
│   │   ├── serializers.py    # DRF serializers
│   │   ├── views.py          # API views
│   │   └── urls.py           # URL routing
│   └── manage.py             # Django management script
│
└── frontend/
    ├── public/               # Static assets
    ├── src/
    │   ├── components/       # Reusable UI components
    │   │   ├── features/     # Feature-specific components
    │   │   │   └── composers/
    │   │   │       └── ExpandableComposerRow/
    │   │   ├── layout/       # Layout components
    │   │   │   └── Navbar/
    │   │   └── ui/           # Generic UI components
    │   │       ├── AdvancedFilters/
    │   │       ├── DataTable/
    │   │       ├── Pagination/
    │   │       └── SearchBar/
    │   ├── hooks/            # Custom React hooks
    │   ├── lib/              # Utilities and services
    │   ├── pages/            # Page components
    │   ├── styles/           # Global styles
    │   ├── types/            # TypeScript definitions
    │   └── App.tsx           # Root component
    └── package.json
```

## Component Organization

Components follow a modular structure with colocated styles:

```
ComponentName/
├── ComponentName.tsx    # Component logic
├── ComponentName.css    # Component styles
└── index.ts             # Barrel export
```

This provides:
- Clear ownership of styles
- Easy imports via barrel exports
- Better code organization
- Simplified testing

## Technology Stack

### Frontend
- React 18 with TypeScript
- Vite (build tooling)
- React Router (navigation)
- TanStack Query (server-state: caching, dedup, race-safe requests)
- Axios (API client)

### Backend
- Django 6.0
- Django REST Framework
- PostgreSQL 17 (self-hosted in a container on the EC2 host in prod; local dev can use SQLite or a local Postgres)
- Python 3.10+

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.10+
- npm or yarn

### Installation

1. Clone and enter directory:
```bash
git clone <repository-url>
cd cgmd
```

2. Backend setup:
```bash
python -m venv venv
source venv/Scripts/activate     # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt

# Configure .env with your local DB credentials (or use the default SQLite dev DB)
# DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT

python manage.py migrate
```

3. Frontend setup:
```bash
cd frontend
npm install
```

### Running the Application

Start both servers:

Backend (Django):
```bash
python manage.py runserver
# http://localhost:8000
```

Frontend (Vite):
```bash
cd frontend
npm run dev
# http://localhost:5173
```

Access application at http://localhost:5173

## Key Features

- Browse 15,000+ classical guitar composers
- Search 74,000+ guitar works
- Advanced filtering (year, country, instrumentation)
- Typo-tolerant fuzzy search (PostgreSQL trigram, server-side)
- Shareable/refresh-proof views (all sort/filter/search/page state in the URL)
- Expandable composer rows
- Mobile-responsive design
- Real-time search with debouncing

## API Endpoints

### Composers
```
GET  /api/composers/           List composers (paginated)
GET  /api/composers/:id/       Get composer details
GET  /api/composers/:id/works/ List composer works
```

### Works
```
GET  /api/works/               List works (paginated)
GET  /api/works/:id/           Get work details
```

### Search & Filters
```
GET  /api/works/?search=term        Fuzzy search works (trigram)
GET  /api/composers/?search=term    Fuzzy search composers (trigram)
GET  /api/instrumentations/         List instrumentation types
GET  /api/countries/                List countries
```

All list endpoints support:
- Pagination: `?page=1&page_size=50`
- Ordering: `?ordering=title_sort_key` (prefix `-` for descending)
- Filtering (works): `?instrumentation=X&composer_country=Y&composer_birth_year_min=…`
- Filtering (composers): `?instrumentation=X&country_name=Y&birth_year_min=…`
- Search: `?search=term` (omit `ordering` to rank by relevance)

## Development

### State Management
- **Server state:** TanStack Query — list views use `useServerTable`, which keys the query on sort/filter/search/page for caching + race safety
- **URL as source of truth:** sort/filter/search/page live in the URL (`useSearchParams`), so views are shareable, refresh-proof, and back-button friendly
- **Local state:** `useState`; **debouncing:** `useDebounce`

### Styling
- Global styles: `src/styles/global.css`
- Component styles: Colocated with components
- CSS variables for theming
- Mobile-first responsive design

### Code Organization
```
components/
├── features/      # Feature-specific (e.g., ExpandableComposerRow)
├── layout/        # Layout structure (e.g., Navbar)
└── ui/            # Reusable UI (e.g., DataTable, SearchBar)
```

### Import Patterns
```typescript
// Clean imports via barrel exports
import Navbar from '@/components/layout/Navbar';
import DataTable from '@/components/ui/DataTable';
import { useServerTable } from '@/hooks/useServerTable';
```

## Testing

```bash
# Backend (pytest-django)
pytest

# Frontend unit/component (Vitest + Testing Library + MSW)
cd frontend && npm test

# End-to-end (Playwright — boots Django + Vite, seeds a test DB)
cd frontend && npm run test:e2e
```

CI (`.github/workflows/ci.yml`) runs all three on every PR — Postgres service for the backend/E2E, plus coverage gates.

## Building for Production

```bash
cd frontend
npm run build
# Output in frontend/dist/
```

The site runs entirely on AWS — frontend on **S3 + CloudFront** (private bucket via OAC), backend as a **Docker Compose stack on a single EC2 instance** (Django + gunicorn, PostgreSQL 17, and Caddy for TLS — all co-located; no Elastic Beanstalk, no RDS, no Supabase). See **[AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)** for the full runbook, and the one-command deploy scripts in [`scripts/`](scripts/) (`deploy-backend.sh`, `deploy-frontend.sh`).

## Performance Optimizations

- Server-state caching, dedup, and stale-while-revalidate (TanStack Query)
- Debounced search (300ms)
- Memoized computations (`useMemo`) and stable callbacks (`useCallback`)
- Code splitting and lazy-loaded routes (Vite / React.lazy)

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

Mobile responsive on all modern devices.

## Code Style

- TypeScript strict mode
- ESLint for linting
- PascalCase for components
- camelCase for utilities
- Consistent file naming

## Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/name`)
3. Commit changes (`git commit -m 'Add feature'`)
4. Push branch (`git push origin feature/name`)
5. Open Pull Request

## Project Status

Active development. See ROADMAP.md for planned features.

## License

MIT License

## Contact

Repository: https://github.com/jessewashburn/solmu
