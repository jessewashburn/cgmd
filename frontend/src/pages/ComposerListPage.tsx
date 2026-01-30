import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import DataTable, { Column } from '../components/DataTable';
import Pagination from '../components/Pagination';

interface Composer {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  birth_year: number | null;
  death_year: number | null;
  is_living: boolean;
  period: string;
  country: {
    id: number;
    name: string;
  } | null;
  work_count: number;
}

export default function ComposerListPage() {
  const [composers, setComposers] = useState<Composer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const debouncedSearch = useDebounce(searchQuery, 300);
  
  const pageSize = 200;

  const columns: Column<Composer>[] = [
    {
      header: 'Name',
      accessor: (composer) => (
        <Link
          to={`/composers/${composer.id}`}
          style={{ textDecoration: 'none', color: '#1976d2', fontWeight: '500' }}
        >
          {composer.full_name}
        </Link>
      ),
    },
    {
      header: 'Period',
      accessor: (composer) => composer.period || '-',
    },
    {
      header: 'Country',
      accessor: (composer) => composer.country?.name || '-',
    },
    {
      header: 'Years',
      accessor: (composer) => {
        const birth = composer.birth_year || '?';
        const death = composer.death_year || (composer.is_living ? 'present' : '?');
        return `${birth} - ${death}`;
      },
      align: 'center',
      width: '150px',
    },
    {
      header: 'Works',
      accessor: (composer) => composer.work_count,
      align: 'center',
      width: '100px',
    },
  ];

  useEffect(() => {
    fetchComposers();
  }, [debouncedSearch, currentPage]);

  const fetchComposers = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
        ordering: 'last_name,first_name',
      };

      if (debouncedSearch) {
        params.search = debouncedSearch;
      }

      const response = await api.get('/composers/', { params });
      setComposers(response.data.results || response.data);
      setTotalCount(response.data.count || response.data.length);
    } catch (err) {
      console.error('Error fetching composers:', err);
      setError('Failed to load composers. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <header style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
          Composers
        </h1>
        <p style={{ fontSize: '1rem', color: '#666' }}>
          Browse {totalCount.toLocaleString()} classical guitar composers
        </p>
      </header>

      {/* Search Bar */}
      <div style={{ marginBottom: '2rem', maxWidth: '800px', margin: '0 auto 2rem' }}>
        <input
          type="text"
          placeholder="Search for composers..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setCurrentPage(1);
          }}
          style={{
            width: '100%',
            padding: '1rem',
            fontSize: '1rem',
            border: '2px solid #ddd',
            borderRadius: '8px',
            outline: 'none',
          }}
          onFocus={(e) => (e.target.style.borderColor = '#4CAF50')}
          onBlur={(e) => (e.target.style.borderColor = '#ddd')}
        />
      </div>

      {/* Quick Links */}
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '2rem' }}>
        <Link to="/" style={{ textDecoration: 'none', color: '#4CAF50', fontWeight: '500' }}>
          ← Back to Works
        </Link>
        <span style={{ color: '#ddd' }}>|</span>
        <Link to="/search" style={{ textDecoration: 'none', color: '#4CAF50', fontWeight: '500' }}>
          Advanced Search
        </Link>
      </div>

      {/* Error State */}
      {error && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#d32f2f' }}>
          <p>{error}</p>
          <button
            onClick={fetchComposers}
            style={{
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Composers List */}
      {!error && (
        <>
          <DataTable
            data={composers}
            columns={columns}
            getRowKey={(composer) => composer.id}
            loading={loading}
            emptyMessage="No composers found. Try adjusting your search."
          />

          {!loading && composers.length > 0 && (
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              totalCount={totalCount}
              onPageChange={setCurrentPage}
              itemName="composers"
            />
          )}
        </>
      )}
    </div>
  );
}
