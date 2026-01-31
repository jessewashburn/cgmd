# Solmu Frontend - Quick Reference

## Project Structure

```
frontend/src/
├── assets/                   # Static assets (images, icons)
│   ├── Solmu.png
│   └── react.svg
│
├── components/               # All React components
│   ├── features/             # Feature-specific components
│   │   └── composers/
│   │       └── ExpandableComposerRow/
│   │           ├── ExpandableComposerRow.tsx
│   │           ├── ExpandableComposerRow.css
│   │           └── index.ts
│   │
│   ├── layout/               # Layout components
│   │   └── Navbar/
│   │       ├── Navbar.tsx
│   │       ├── Navbar.css
│   │       └── index.ts
│   │
│   └── ui/                   # Reusable UI components
│       ├── AdvancedFilters/
│       │   ├── AdvancedFilters.tsx
│       │   └── index.ts
│       ├── DataTable/
│       │   ├── DataTable.tsx
│       │   ├── DataTable.css
│       │   └── index.ts
│       ├── Pagination/
│       │   ├── Pagination.tsx
│       │   ├── Pagination.css
│       │   └── index.ts
│       └── SearchBar/
│           ├── SearchBar.tsx
│           └── index.ts
│
├── hooks/                    # Custom React hooks
│   ├── useCountries.ts
│   ├── useDebounce.ts
│   ├── useFilters.ts
│   ├── useInstrumentations.ts
│   └── useSort.ts
│
├── lib/                      # Utilities and services
│   ├── api.ts                # Axios API client
│   ├── fuzzySearch.ts        # Search utilities
│   ├── index.ts              # Service exports
│   └── index.ts.backup
│
├── pages/                    # Page components (routes)
│   ├── AboutPage.tsx
│   ├── ComposerDetailPage.tsx
│   ├── ComposerListPage.tsx  # Homepage
│   ├── SearchPage.tsx
│   ├── WorkDetailPage.tsx
│   └── WorkListPage.tsx
│
├── styles/                   # Global styles only
│   ├── global.css
│   ├── pages/
│   │   ├── ComposerDetailPage.css
│   │   ├── ComposerListPage.css
│   │   ├── HomePage.css
│   │   └── WorkDetailPage.css
│   └── shared/
│       ├── DetailPage.css
│       └── ListPage.css
│
├── types/                    # TypeScript type definitions
│   └── index.ts
│
├── App.css                   # App component styles
├── App.tsx                   # Root component
├── index.css                 # Root styles
├── main.tsx                  # Application entry point
└── vite-env.d.ts             # Vite type definitions
```

## Import Cheatsheet

### Components
```typescript
// Layout
import Navbar from '@/components/layout/Navbar';

// UI Components
import DataTable from '@/components/ui/DataTable';
import Pagination from '@/components/ui/Pagination';
import SearchBar from '@/components/ui/SearchBar';
import AdvancedFilters from '@/components/ui/AdvancedFilters';

// Feature Components
import ExpandableComposerRow from '@/components/features/composers/ExpandableComposerRow';
```

### Hooks
```typescript
import { useDebounce } from '@/hooks/useDebounce';
import { useFilters } from '@/hooks/useFilters';
import { useSort } from '@/hooks/useSort';
import { useCountries } from '@/hooks/useCountries';
import { useInstrumentations } from '@/hooks/useInstrumentations';
```

### Library
```typescript
import api from '@/lib/api';
import { fuzzySearch } from '@/lib/fuzzySearch';
import { composerService, workService, searchService } from '@/lib';
```

### Types
```typescript
import type { Composer, Work, PaginatedResponse } from '@/types';
```

## Component Categories

### Layout Components
Purpose: Define page structure and navigation
- **Navbar** - App navigation with mobile hamburger menu

### UI Components
Purpose: Reusable, domain-agnostic UI elements
- **DataTable** - Generic table with sorting and custom columns
- **Pagination** - Page navigation controls
- **SearchBar** - Search input component
- **AdvancedFilters** - Filter panel (year, country, instrumentation)

### Feature Components
Purpose: Domain-specific business logic
- **ExpandableComposerRow** - Composer table row with expandable works list

## Quick Commands

```bash
# Development
npm run dev              # Start dev server (http://localhost:5173)
npm run build            # Build for production
npm run preview          # Preview production build
npm run lint             # Run ESLint

# Backend
python manage.py runserver  # Start Django API (http://localhost:8000)
```

## Common Tasks

### Add New UI Component
```bash
mkdir -p src/components/ui/NewComponent
touch src/components/ui/NewComponent/{NewComponent.tsx,NewComponent.css,index.ts}
```

### Add New Page
```bash
touch src/pages/NewPage.tsx
# Then add route in App.tsx
```

### Add New Hook
```bash
touch src/hooks/useNewHook.ts
```

## File Naming Conventions

- Components: `PascalCase.tsx` (e.g., `DataTable.tsx`)
- Hooks: `camelCase.ts` with `use` prefix (e.g., `useFilters.ts`)
- Utilities: `camelCase.ts` (e.g., `fuzzySearch.ts`)
- Types: `PascalCase` interfaces/types (e.g., `Composer`, `Work`)

## Key Features

- 1,000+ classical guitar composers
- 100,000+ guitar works
- Advanced filtering (year, country, instrumentation)
- Fuzzy search with typo tolerance
- Mobile-responsive design
- Real-time search with debouncing

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **React Router** - Routing
- **Axios** - HTTP client
- **Fuse.js** - Fuzzy search

## Documentation

- `README.md` - Project overview and setup
- `ARCHITECTURE.md` - Detailed architecture guide
- `REORGANIZATION.md` - Reorganization changelog
- `QUICK_REFERENCE.md` - This file

## Common Patterns

### Data Fetching
```typescript
const [data, setData] = useState([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  fetchData();
}, [dependency]);
```

### Search with Debounce
```typescript
const [query, setQuery] = useState('');
const debouncedQuery = useDebounce(query, 300);

useEffect(() => {
  search(debouncedQuery);
}, [debouncedQuery]);
```

### Filtering
```typescript
const {
  yearRange,
  setYearRange,
  selectedCountry,
  setSelectedCountry,
  clearFilters
} = useFilters();
```

## API Endpoints

```
GET  /api/composers/              # List composers
GET  /api/composers/:id/          # Get composer
GET  /api/composers/:id/works/    # Get composer works
GET  /api/works/                  # List works
GET  /api/works/:id/              # Get work
GET  /api/search/?q=query         # Search
GET  /api/countries/              # List countries
GET  /api/instrumentations/       # List instrumentations
```

## Environment

- **Development**: http://localhost:5173
- **API**: http://localhost:8000
- **Production**: TBD

## Support

For questions or issues, refer to:
1. `ARCHITECTURE.md` for detailed architecture
2. `README.md` for setup instructions
3. `REORGANIZATION.md` for structure changes
