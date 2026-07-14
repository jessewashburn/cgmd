import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';
import { Composer } from '../types';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorMessage from '../components/ui/ErrorMessage';
import './AdminComposers.css';


export default function AdminComposers() {
  const [composers, setComposers] = useState<Composer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchComposers();
  }, []);

  const fetchComposers = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/composers/`);
      setComposers(response.data.results || response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load composers');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete ${name}? This action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/composers/${id}/`);
      setComposers(composers.filter(c => c.id !== id));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete composer');
    }
  };

  const filteredComposers = composers.filter(composer =>
    composer.full_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorMessage message={error} />;

  return (
    <div className="admin-composers">
      <header className="admin-page-header">
        <div className="header-content">
          <Link to="/admin" className="back-link">← Back to Dashboard</Link>
          <h1>Manage Composers</h1>
        </div>
      </header>

      <div className="admin-content">
        <div className="admin-toolbar">
          <input
            type="text"
            placeholder="Search composers..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
          <button className="btn-primary">
            + Add New Composer
          </button>
        </div>

        <div className="composers-table-container">
          <table className="composers-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Period</th>
                <th>Country</th>
                <th>Years</th>
                <th>Works</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredComposers.map(composer => (
                <tr key={composer.id}>
                  <td className="composer-name">{composer.full_name}</td>
                  <td>{composer.period || '-'}</td>
                  <td>{composer.country?.name || '-'}</td>
                  <td>
                    {composer.birth_year && composer.death_year
                      ? `${composer.birth_year}–${composer.death_year}`
                      : composer.birth_year
                      ? `${composer.birth_year}–`
                      : '-'}
                  </td>
                  <td className="work-count">{composer.work_count}</td>
                  <td className="actions">
                    <button className="btn-edit">Edit</button>
                    <button 
                      className="btn-delete"
                      onClick={() => handleDelete(composer.id, composer.full_name)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {filteredComposers.length === 0 && (
          <div className="no-results">
            No composers found matching "{searchTerm}"
          </div>
        )}
      </div>
    </div>
  );
}
