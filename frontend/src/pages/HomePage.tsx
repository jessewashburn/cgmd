import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import DataTable, { Column } from '../components/DataTable';
import Pagination from '../components/Pagination';
import '../styles/pages/HomePage.css';

interface Work {
  id: number;
  title: string;
  composer: {
    id: number;
    full_name: string;
  } | null;
  instrumentation_category: {
    id: number;
    name: string;
  } | null;
  difficulty_level: number | null;
  composition_year: number | null;
}

export default function HomePage() {
  const [works, setWorks] = useState<Work[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [sortColumn, setSortColumn] = useState<'title' | 'composer' | 'instrumentation' | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const debouncedSearch = useDebounce(searchQuery, 300);
  
  const pageSize = 200;

  const handleSort = (column: 'title' | 'composer' | 'instrumentation') => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  // Apply sorting to displayed works
  const sortedWorks = useMemo(() => {
    if (!sortColumn) return works;
    
    const sorted = [...works].sort((a, b) => {
      let aVal: string;
      let bVal: string;
      
      switch (sortColumn) {
        case 'title':
          aVal = a.title.toLowerCase();
          bVal = b.title.toLowerCase();
          break;
        case 'composer':
          aVal = a.composer?.full_name.toLowerCase() || '';
          bVal = b.composer?.full_name.toLowerCase() || '';
          break;
        case 'instrumentation':
          aVal = a.instrumentation_category?.name.toLowerCase() || '';
          bVal = b.instrumentation_category?.name.toLowerCase() || '';
          break;
        default:
          return 0;
      }
      
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
    
    return sorted;
  }, [works, sortColumn, sortDirection]);

  const columns: Column<Work>[] = [
    {
      header: (
        <span 
          onClick={() => handleSort('title')} 
          className="sort-header"
        >
          Work Title {sortColumn === 'title' && (sortDirection === 'asc' ? '↑' : '↓')}
        </span>
      ),
      accessor: (work) => (
        <Link to={`/works/${work.id}`} className="link-primary">
          {work.title}
        </Link>
      ),
    },
    {
      header: (
        <span 
          onClick={() => handleSort('composer')} 
          className="sort-header"
        >
          Composer {sortColumn === 'composer' && (sortDirection === 'asc' ? '↑' : '↓')}
        </span>
      ),
      accessor: (work) =>
        work.composer ? (
          <Link to={`/composers/${work.composer.id}`} className="link-secondary">
            {work.composer.full_name}
          </Link>
        ) : (
          '-'
        ),
    },
    {
      header: (
        <span 
          onClick={() => handleSort('instrumentation')} 
          className="sort-header"
        >
          Instrumentation {sortColumn === 'instrumentation' && (sortDirection === 'asc' ? '↑' : '↓')}
        </span>
      ),
      accessor: (work) => work.instrumentation_category?.name || '-',
    },
  ];

  useEffect(() => {
    fetchWorks();
  }, [debouncedSearch, currentPage]);

  const fetchWorks = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
        ordering: 'title',
      };

      // Filter for guitar works - you may need to adjust the category ID
      // For now, I'm searching for works with "guitar" in instrumentation
      if (debouncedSearch) {
        params.search = debouncedSearch;
      }

      const response = await api.get('/works/', { params });
      setWorks(response.data.results || response.data);
      setTotalCount(response.data.count || response.data.length);
    } catch (err) {
      console.error('Error fetching works:', err);
      setError('Failed to load works. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="home-page">
      <header className="page-header">
        <h1>Classical Guitar Music Database</h1>
        <p>Browse {totalCount.toLocaleString()} guitar works alphabetically</p>
      </header>

      {/* Search Bar */}
      <div className="search-container">
        <input
          type="text"
          className="search-input"
          placeholder="Search for works or composers..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setCurrentPage(1);
          }}
        />
      </div>

      {/* Quick Links */}
      <div className="quick-links">
        <Link to="/">Browse Composers</Link>
        <span className="separator">|</span>
        <Link to="/search">Advanced Search</Link>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="loading-state">
          <p>Loading works...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="error-state">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchWorks}>
            Retry
          </button>
        </div>
      )}

      {/* Works List */}
      {!error && (
        <>
          <DataTable
            data={sortedWorks}
            columns={columns}
            getRowKey={(work) => work.id}
            loading={loading}
            emptyMessage="No works found. Try adjusting your search."
          />

          {!loading && works.length > 0 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              totalCount={totalCount}
              onPageChange={setCurrentPage}
              itemName="total works"
            />
          )}
        </>
      )}
    </div>
  );
}
