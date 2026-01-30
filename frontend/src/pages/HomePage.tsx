import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import { useDebounce } from '../hooks/useDebounce';

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
      {!loading && !error && works.length > 0 && (
        <>
          <div style={{ marginBottom: '2rem' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', background: 'white', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
              <thead>
                <tr style={{ background: '#f5f5f5', borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Work Title</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Composer</th>
                  <th style={{ padding: '1rem', textAlign: 'left', fontWeight: '600' }}>Instrumentation</th>
                </tr>
              </thead>
              <tbody>
                {works.map((work) => (
                  <tr 
                    key={work.id} 
                    style={{ borderBottom: '1px solid #eee' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f9f9f9'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                  >
                    <td style={{ padding: '1rem' }}>
                      <Link 
                        to={`/works/${work.id}`}
                        style={{ textDecoration: 'none', color: '#1976d2', fontWeight: '500' }}
                      >
                        {work.title}
                      </Link>
                    </td>
                    <td style={{ padding: '1rem' }}>
                      {work.composer && (
                        <Link 
                          to={`/composers/${work.composer.id}`}
                          style={{ textDecoration: 'none', color: '#555' }}
                        >
                          {work.composer.full_name}
                        </Link>
                      )}
                    </td>
                    <td style={{ padding: '1rem', color: '#666' }}>
                      {work.instrumentation_category?.name || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '2rem' }}>
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              style={{
                padding: '0.5rem 1rem',
                background: currentPage === 1 ? '#ddd' : '#4CAF50',
                color: currentPage === 1 ? '#999' : 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
              }}
            >
              Previous
            </button>
            
            <span style={{ color: '#666' }}>
              Page {currentPage} of {totalPages} ({totalCount.toLocaleString()} total works)
            </span>
            
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              style={{
                padding: '0.5rem 1rem',
                background: currentPage === totalPages ? '#ddd' : '#4CAF50',
                color: currentPage === totalPages ? '#999' : 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: currentPage === totalPages ? 'not-allowed' : 'pointer'
              }}
            >
              Next
            </button>
          </div>
        </>
      )}

      {/* No Results */}
      {!loading && !error && works.length === 0 && (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#666' }}>
          <p>No works found. Try adjusting your search.</p>
        </div>
      )}
    </div>
  );
}
