# Solmu - Guitar Music Network

Our repertoire, all in one place.

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
- Axios (API client)
- Fuse.js (fuzzy search)

### Backend
- Django 6.0
- Django REST Framework
- SQLite database
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

- Browse 1,000+ classical guitar composers
- Search 100,000+ guitar works
- Advanced filtering (year, country, instrumentation)
- Fuzzy search with typo tolerance
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
GET  /api/search/?q=query      Search composers and works
GET  /api/instrumentations/    List instrumentation types
GET  /api/countries/           List countries
```

All list endpoints support:
- Pagination: `?page=1&page_size=200`
- Filtering: `?instrumentation=X&country_name=Y`
- Search: `?search=term`

## Development

### State Management
- Local state: `useState`
- Side effects: `useEffect`
- Custom hooks: `useFilters`, `useSort`, `useDebounce`

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
import { useFilters } from '@/hooks/useFilters';
```

## Building for Production

```bash
cd frontend
npm run build
# Output in frontend/dist/
```

Configure Django to serve static files or deploy separately.

## Performance Optimizations

- Debounced search (300ms)
- Memoized computations (`useMemo`)
- Optimized re-renders (`useCallback`)
- Code splitting (Vite)
- Lazy loading components

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

Repository: https://github.com/yourusername/solmu
