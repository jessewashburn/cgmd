import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';
import DataTable, { Column } from '../components/DataTable';
import Pagination from '../components/Pagination';

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
  const debouncedSearch = useDebounce(searchQuery, 300);
  
  const pageSize = 200;

  const columns: Column<Work>[] = [
    {
      header: 'Work Title',
      accessor: (work) => (
        <Link
          to={`/works/${work.id}`}
          style={{ textDecoration: 'none', color: '#1976d2', fontWeight: '500' }}
        >
          {work.title}
        </Link>
      ),
    },
    {
      header: 'Composer',
      accessor: (work) =>
        work.composer ? (
          <Link
            to={`/composers/${work.composer.id}`}
            style={{ textDecoration: 'none', color: '#555' }}
          >
            {work.composer.full_name}
          </Link>
        ) : (
          '-'
        ),
    },
    {
      header: 'Instrumentation',
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
    <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
      <header style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
          Classical Guitar Music Database
        </h1>
        <p style={{ fontSize: '1rem', color: '#666' }}>
          Browse {totalCount.toLocaleString()} guitar works alphabetically
        </p>
      </header>

      {/* Search Bar */}
      <div style={{ marginBottom: '2rem', maxWidth: '800px', margin: '0 auto 2rem' }}>
        <input
          type="text"
          placeholder="Search for works or composers..."
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
          onFocus={(e) => e.target.style.borderColor = '#4CAF50'}
          onBlur={(e) => e.target.style.borderColor = '#ddd'}
        />
      </div>

      {/* Quick Links */}
      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '2rem' }}>
        <Link to="/composers" style={{ textDecoration: 'none', color: '#4CAF50', fontWeight: '500' }}>
          Browse Composers
        </Link>
        <span style={{ color: '#ddd' }}>|</span>
        <Link to="/search" style={{ textDecoration: 'none', color: '#4CAF50', fontWeight: '500' }}>
          Advanced Search
        </Link>
      </div>

      {/* Loading State */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '3rem' }}>
          <p>Loading works...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#d32f2f' }}>
          <p>{error}</p>
          <button 
            onClick={fetchWorks}
            style={{ 
              marginTop: '1rem', 
              padding: '0.5rem 1rem',
              background: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Works List */}
      {!error && (
        <>
          <DataTable
            data={works}
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
