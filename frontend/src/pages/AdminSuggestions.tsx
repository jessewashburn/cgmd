import { useState, useEffect, useCallback } from 'react';
import api from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import PageHeader from '../components/layout/PageHeader';
import './AdminSuggestions.css';


interface Suggestion {
  id: number;
  suggestion_type: string;
  suggestion_type_display: string;
  status: string;
  status_display: string;
  title: string;
  description: string;
  submitter_name: string;
  submitter_email: string;
  admin_notes: string;
  created_at: string;
  reviewed_at: string | null;
  related_work: number | null;
  suggested_data: Record<string, unknown> | null;
}

interface DraftLink { label?: string; url?: string; link_type?: string }

interface ComposerMatch {
  id: number;
  full_name: string;
  birth_year: number | null;
  score?: number;
  match_type?: string;
}

interface ApplyPrompt {
  suggestionId: number;
  suggestedName: string;
  exactMatch: ComposerMatch | null;
  looseMatches: ComposerMatch[];
}

export default function AdminSuggestions() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('pending');
  const [selectedSuggestion, setSelectedSuggestion] = useState<Suggestion | null>(null);
  const [adminNotes, setAdminNotes] = useState('');
  const [applyPrompt, setApplyPrompt] = useState<ApplyPrompt | null>(null);
  const { logout } = useAuth();

  const fetchSuggestions = useCallback(async () => {
    try {
      setLoading(true);
      const params = filter !== 'all' ? { status: filter } : {};
      const response = await api.get(`/suggestions/`, { params });
      setSuggestions(response.data.results || response.data);
    } catch (error: unknown) {
      console.error('Failed to load suggestions:', error);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  const handleApprove = async (id: number) => {
    try {
      await api.post(`/suggestions/${id}/approve/`);
      fetchSuggestions();
      setSelectedSuggestion(null);
    } catch (error) {
      alert('Failed to approve suggestion');
    }
  };

  const handleReject = async (id: number) => {
    try {
      await api.post(`/suggestions/${id}/reject/`, { admin_notes: adminNotes });
      fetchSuggestions();
      setSelectedSuggestion(null);
      setAdminNotes('');
    } catch (error) {
      alert('Failed to reject suggestion');
    }
  };

  const handleMarkMerged = async (id: number) => {
    try {
      await api.post(`/suggestions/${id}/mark_merged/`);
      fetchSuggestions();
      setSelectedSuggestion(null);
    } catch (error) {
      alert('Failed to mark as merged');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this suggestion?')) return;

    try {
      await api.delete(`/suggestions/${id}/`);
      fetchSuggestions();
      setSelectedSuggestion(null);
    } catch (error) {
      alert('Failed to delete suggestion');
    }
  };

  const summarizeApply = (data: Record<string, any>) => {
    const parts: string[] = [];
    if (data.composer) parts.push(`composer ${data.composer.action}`);
    if (data.work) parts.push(`work ${data.work.action}`);
    if (Array.isArray(data.fields_updated) && data.fields_updated.length) {
      parts.push(`${data.fields_updated.length} field(s) updated`);
    }
    if (typeof data.links_added === 'number') parts.push(`${data.links_added} link(s) added`);
    return parts.join(', ') || 'applied';
  };

  // Apply a suggestion. For new work/composer the server replies 409 with match
  // candidates when the composer is ambiguous; we surface those for confirmation.
  const runApply = async (id: number, body?: Record<string, unknown>) => {
    try {
      const res = await api.post(`/suggestions/${id}/apply/`, body || {});
      alert(`Applied: ${summarizeApply(res.data || {})}.`);
      setApplyPrompt(null);
      fetchSuggestions();
      setSelectedSuggestion(null);
    } catch (error: unknown) {
      const err = error as { response?: { status?: number; data?: { error?: string; composer?: any } } };
      if (err.response?.status === 409 && err.response.data?.composer) {
        const c = err.response.data.composer;
        setApplyPrompt({
          suggestionId: id,
          suggestedName: c.suggested?.name || '',
          exactMatch: c.exact_match || null,
          looseMatches: c.loose_matches || [],
        });
        return;
      }
      alert(err.response?.data?.error || 'Failed to apply suggestion');
    }
  };

  const handleApply = (id: number) => runApply(id);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="admin-suggestions page page--wide">
      <PageHeader 
        tagline="ADMIN PORTAL"
        title="User Suggestions"
        subtitle="Review and manage user submissions"
      />

      <div className="admin-content">
        <div className="filters">
          <button 
            className={filter === 'pending' ? 'active' : ''}
            onClick={() => setFilter('pending')}
          >
            Pending
          </button>
          <button 
            className={filter === 'approved' ? 'active' : ''}
            onClick={() => setFilter('approved')}
          >
            Approved
          </button>
          <button 
            className={filter === 'merged' ? 'active' : ''}
            onClick={() => setFilter('merged')}
          >
            Merged
          </button>
          <button 
            className={filter === 'rejected' ? 'active' : ''}
            onClick={() => setFilter('rejected')}
          >
            Rejected
          </button>
          <button 
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All
          </button>
        </div>

        <div className="suggestions-layout">
          <div className="suggestions-list">
            {suggestions.length === 0 ? (
              <div className="no-suggestions">
                No {filter !== 'all' && filter} suggestions found.
              </div>
            ) : (
              suggestions.map((suggestion) => (
                <div
                  key={suggestion.id}
                  className={`suggestion-card ${selectedSuggestion?.id === suggestion.id ? 'selected' : ''}`}
                  onClick={() => setSelectedSuggestion(suggestion)}
                >
                  <div className="suggestion-header">
                    <span className={`badge badge-${suggestion.status}`}>
                      {suggestion.status_display}
                    </span>
                    <span className="badge badge-type">
                      {suggestion.suggestion_type_display}
                    </span>
                  </div>
                  <h3>{suggestion.title}</h3>
                  <p className="suggestion-preview">
                    {suggestion.description.substring(0, 100)}
                    {suggestion.description.length > 100 && '...'}
                  </p>
                  <div className="suggestion-meta">
                    {suggestion.submitter_name && (
                      <span>👤 {suggestion.submitter_name}</span>
                    )}
                    <span>📅 {new Date(suggestion.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {selectedSuggestion && (
            <div className="suggestion-detail">
              <div className="detail-header">
                <h2>{selectedSuggestion.title}</h2>
                <button 
                  className="close-button"
                  onClick={() => setSelectedSuggestion(null)}
                >
                  ×
                </button>
              </div>

              <div className="detail-badges">
                <span className={`badge badge-${selectedSuggestion.status}`}>
                  {selectedSuggestion.status_display}
                </span>
                <span className="badge badge-type">
                  {selectedSuggestion.suggestion_type_display}
                </span>
              </div>

              <div className="detail-section">
                <h4>Description</h4>
                <p>{selectedSuggestion.description}</p>
              </div>

              {selectedSuggestion.suggested_data && (() => {
                const data = selectedSuggestion.suggested_data as Record<string, unknown>;
                const scalars = Object.entries(data).filter(
                  ([k, v]) => k !== 'links' && (v === null || typeof v !== 'object'),
                );
                const links = Array.isArray(data.links) ? (data.links as DraftLink[]) : [];
                if (scalars.length === 0 && links.length === 0) return null;
                return (
                  <div className="detail-section">
                    <h4>Proposed Data</h4>
                    <dl className="suggested-data">
                      {scalars.map(([k, v]) => (
                        <div key={k} className="suggested-data-row">
                          <dt>{k}</dt>
                          <dd>{v === null || v === '' ? '—' : String(v)}</dd>
                        </div>
                      ))}
                    </dl>
                    {links.length > 0 && (
                      <div className="suggested-links">
                        <strong>Links</strong>
                        <ul>
                          {links.map((l, i) => (
                            <li key={i}>
                              {l.label ? `${l.label}: ` : ''}
                              <a href={l.url} target="_blank" rel="noopener noreferrer">{l.url}</a>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                );
              })()}

              {selectedSuggestion.submitter_name && (
                <div className="detail-section">
                  <h4>Submitted By</h4>
                  <p>{selectedSuggestion.submitter_name}</p>
                  {selectedSuggestion.submitter_email && (
                    <p><a href={`mailto:${selectedSuggestion.submitter_email}`}>{selectedSuggestion.submitter_email}</a></p>
                  )}
                </div>
              )}

              {selectedSuggestion.admin_notes && (
                <div className="detail-section">
                  <h4>Admin Notes</h4>
                  <p>{selectedSuggestion.admin_notes}</p>
                </div>
              )}

              <div className="detail-actions">
                {selectedSuggestion.status === 'pending' && (
                  <>
                    <button 
                      className="btn-approve"
                      onClick={() => handleApprove(selectedSuggestion.id)}
                    >
                      ✓ Approve
                    </button>
                    <button 
                      className="btn-reject"
                      onClick={() => {
                        const notes = prompt('Add notes (optional):');
                        if (notes !== null) {
                          setAdminNotes(notes);
                          handleReject(selectedSuggestion.id);
                        }
                      }}
                    >
                      ✗ Reject
                    </button>
                  </>
                )}

                {selectedSuggestion.status === 'approved' && (
                  <button
                    className="btn-merge"
                    onClick={() => handleMarkMerged(selectedSuggestion.id)}
                  >
                    ✓ Mark as Merged
                  </button>
                )}

                {(['new_work', 'new_composer'].includes(selectedSuggestion.suggestion_type) ||
                  (selectedSuggestion.suggestion_type === 'edit_work' && selectedSuggestion.related_work)) &&
                  selectedSuggestion.status !== 'merged' &&
                  selectedSuggestion.status !== 'rejected' && (
                  <button
                    className="btn-apply"
                    onClick={() => handleApply(selectedSuggestion.id)}
                    title="Incorporate this suggestion into the database"
                  >
                    ⚡ Apply
                  </button>
                )}

                <button
                  className="btn-delete"
                  onClick={() => handleDelete(selectedSuggestion.id)}
                >
                  🗑 Delete
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {applyPrompt && (
        <div className="apply-overlay" onClick={() => setApplyPrompt(null)}>
          <div className="apply-dialog" onClick={(e) => e.stopPropagation()}>
            <h3>Resolve composer</h3>
            <p className="apply-dialog-sub">
              Suggested composer: <strong>{applyPrompt.suggestedName}</strong>. Reuse an existing
              record if it's the same person, or create a new one.
            </p>

            {applyPrompt.exactMatch && (
              <div className="match-row exact">
                <div>
                  <span className="match-badge match-badge-exact">Direct match</span>{' '}
                  {applyPrompt.exactMatch.full_name}
                  {applyPrompt.exactMatch.birth_year ? ` (b. ${applyPrompt.exactMatch.birth_year})` : ''}
                </div>
                <button onClick={() => runApply(applyPrompt.suggestionId, { composer_id: applyPrompt.exactMatch!.id })}>
                  Use this
                </button>
              </div>
            )}

            {applyPrompt.looseMatches.map((m) => (
              <div key={m.id} className="match-row">
                <div>
                  <span className="match-badge match-badge-loose">
                    Possible {m.score != null ? `· ${Math.round(m.score * 100)}%` : ''}
                  </span>{' '}
                  {m.full_name}{m.birth_year ? ` (b. ${m.birth_year})` : ''}
                </div>
                <button onClick={() => runApply(applyPrompt.suggestionId, { composer_id: m.id })}>
                  Use this
                </button>
              </div>
            ))}

            {!applyPrompt.exactMatch && applyPrompt.looseMatches.length === 0 && (
              <p className="apply-dialog-sub">No existing composer matched.</p>
            )}

            <div className="apply-dialog-actions">
              <button
                className="btn-apply"
                onClick={() => runApply(applyPrompt.suggestionId, { create_new_composer: true })}
              >
                Create new composer
              </button>
              <button className="btn-cancel" onClick={() => setApplyPrompt(null)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="logout-container">
        <button onClick={logout} className="logout-button">
          Logout
        </button>
      </div>
    </div>
  );
}
