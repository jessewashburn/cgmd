# Frontend Architecture

## Directory Structure

```
src/
├── components/           # All React components
│   ├── features/         # Feature-specific components
│   │   └── composers/
│   │       └── ExpandableComposerRow/
│   ├── layout/           # Layout components
│   │   └── Navbar/
│   └── ui/               # Reusable UI components
│       ├── AdvancedFilters/
│       ├── DataTable/
│       ├── Pagination/
│       └── SearchBar/
├── hooks/                # Custom React hooks
├── lib/                  # Utilities, API, services
├── pages/                # Page-level components
├── styles/               # Global styles only
├── types/                # TypeScript type definitions
├── App.tsx               # Root component
└── main.tsx              # Application entry
```

## Component Structure

Each component follows this pattern:

```
ComponentName/
├── ComponentName.tsx     # Component implementation
├── ComponentName.css     # Component-specific styles
└── index.ts              # Barrel export
```

Benefits:
- Styles colocated with components
- Clean imports via barrel exports
- Easy to locate related files
- Simplified testing and maintenance

## Component Categories

### Layout Components (`components/layout/`)
Structural components that define page layout:
- `Navbar` - Navigation header with mobile menu

### UI Components (`components/ui/`)
Reusable, generic UI elements:
- `DataTable` - Sortable table with custom columns
- `Pagination` - Page navigation controls
- `SearchBar` - Search input with debouncing
- `AdvancedFilters` - Filter panel with year/country/instrumentation

### Feature Components (`components/features/`)
Domain-specific components:
- `composers/ExpandableComposerRow` - Composer row with expandable works list

## Custom Hooks (`hooks/`)

Shared stateful logic:
- `useCountries` - Fetch and cache country list
- `useDebounce` - Debounce value changes
- `useFilters` - Manage filter state
- `useInstrumentations` - Fetch and cache instrumentations
- `useSort` - Handle column sorting

## Library (`lib/`)

Utilities and services:
- `api.ts` - Axios API client configuration
- `fuzzySearch.ts` - Fuzzy search utilities
- `index.ts` - Service layer (composers, works, search)

## Pages (`pages/`)

Top-level route components:
- `AboutPage` - About page
- `ComposerDetailPage` - Single composer view
- `ComposerListPage` - Composer listing (homepage)
- `SearchPage` - Global search
- `WorkDetailPage` - Single work view
- `WorkListPage` - Works listing

## Styling Strategy

### Global Styles (`styles/`)
- `global.css` - CSS variables, resets, utilities
- `shared/` - Shared page styles (ListPage, DetailPage)

### Component Styles
Each component has its own CSS file colocated in its folder.

### CSS Variables
Defined in `global.css`:
```css
--color-header: #b4a155
--color-accent: #950500
--spacing-sm: 1rem
--border-radius: 8px
```

## Import Patterns

### Barrel Exports
Components use index.ts for clean imports:
```typescript
// Instead of:
import Navbar from './components/layout/Navbar/Navbar';

// Use:
import Navbar from './components/layout/Navbar';
```

### Path Aliases
Relative imports from src:
```typescript
import api from '../lib/api';
import { useFilters } from '../hooks/useFilters';
```

## State Management

### Local State
- `useState` for component-local state
- `useReducer` for complex state logic

### Shared State
- Custom hooks for cross-component state
- Context API for app-wide state (if needed)

### Server State
- Direct API calls with axios
- Local caching in service layer

## Code Conventions

### Naming
- Components: PascalCase (`DataTable.tsx`)
- Hooks: camelCase with 'use' prefix (`useFilters.ts`)
- Utilities: camelCase (`fuzzySearch.ts`)
- Types: PascalCase (`Composer`, `Work`)

### File Organization
- One component per file
- Export component as default
- Export types/interfaces as named exports

### TypeScript
- Strict mode enabled
- Explicit types for props and state
- Shared types in `types/index.ts`

## Performance

### Optimization Techniques
- `useMemo` for expensive computations
- `useCallback` for stable function references
- `useDebounce` for search inputs
- Code splitting with React.lazy

### Bundle Optimization
- Vite handles code splitting
- Tree shaking enabled
- CSS minification in production

## Testing Strategy

### Unit Tests
Test individual components and hooks in isolation.

### Integration Tests
Test component interactions and data flow.

### E2E Tests
Test complete user workflows.

## Build Process

### Development
```bash
npm run dev
```
Runs Vite dev server on http://localhost:5173

### Production
```bash
npm run build
```
Outputs optimized bundle to `dist/`

### Preview Production
```bash
npm run preview
```
Preview production build locally

## Adding New Features

### New Page
1. Create page component in `pages/`
2. Add route in `App.tsx`
3. Add navigation link in `Navbar`

### New Component
1. Create folder in appropriate category
2. Add `.tsx`, `.css`, and `index.ts`
3. Import where needed

### New Hook
1. Create file in `hooks/`
2. Export custom hook
3. Use in components

## Common Patterns

### Data Fetching
```typescript
useEffect(() => {
  fetchData();
}, [dependency]);
```

### Form State
```typescript
const [value, setValue] = useState('');
const debouncedValue = useDebounce(value, 300);
```

### Conditional Rendering
```typescript
{loading && <LoadingState />}
{error && <ErrorState />}
{data && <DataDisplay />}
```

## Troubleshooting

### Import Errors
Check file paths are relative to importing file.

### Style Not Applied
Verify CSS file is imported in component.

### Component Not Updating
Check dependencies in useEffect/useMemo.

## Resources

- [React Documentation](https://react.dev)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)
- [React Router](https://reactrouter.com/)
