import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import api from '../../lib/api';
import LinkListEditor, { DraftLink } from '../ui/LinkListEditor';
import './SuggestionModal.css';

interface SuggestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  itemType: 'composer' | 'work';
  itemData: any;
}

export default function SuggestionModal({ isOpen, onClose, itemType, itemData }: SuggestionModalProps) {
  const [formData, setFormData] = useState<any>(itemData);
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [loadingDetail, setLoadingDetail] = useState(itemType === 'work');

  // The modal is opened from several places with different work shapes (some
  // list rows lack links / full fields). Fetch the canonical work so the form —
  // including its existing bespoke links — always pre-fills correctly.
  useEffect(() => {
    if (itemType !== 'work' || !itemData?.id) {
      setLoadingDetail(false);
      return;
    }
    let cancelled = false;
    api.get(`/works/${itemData.id}/`)
      .then((res) => {
        if (cancelled) return;
        const work = res.data;
        const links: DraftLink[] = (work.links || [])
          .filter((l: any) => l.id != null) // bespoke WorkLinks only, not legacy-column links
          .map((l: any) => ({ label: l.label, url: l.url, link_type: l.link_type }));
        setFormData({ ...work, links });
      })
      .catch(() => { /* keep the partial itemData as a fallback */ })
      .finally(() => { if (!cancelled) setLoadingDetail(false); });
    return () => { cancelled = true; };
  }, [itemType, itemData?.id]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      const suggestionType = itemType === 'composer' ? 'edit_composer' : 'edit_work';

      const suggestedData = {
        ...formData,
        links: (formData.links || [])
          .map((l: DraftLink) => ({ label: l.label.trim(), url: l.url.trim(), link_type: l.link_type || 'other' }))
          .filter((l: DraftLink) => l.label && l.url),
      };

      await api.post('/suggestions/', {
        suggestion_type: suggestionType,
        title: `Edit ${itemType}: ${itemData.full_name || itemData.title}`,
        description: comment || 'Suggested changes submitted via form',
        suggested_data: suggestedData,
        related_composer: itemType === 'composer' ? itemData.id : null,
        related_work: itemType === 'work' ? itemData.id : null,
      });

      setSubmitStatus('success');
      setTimeout(() => {
        onClose();
        setSubmitStatus('idle');
        setComment('');
      }, 2000);
    } catch (error) {
      console.error('Error submitting suggestion:', error);
      setSubmitStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field: string, value: any) => {
    setFormData({ ...formData, [field]: value });
  };

  const renderComposerFields = () => (
    <>
      <div className="form-group">
        <label>Full Name</label>
        <input
          type="text"
          value={formData.full_name || ''}
          onChange={(e) => handleChange('full_name', e.target.value)}
        />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Birth Year</label>
          <input
            type="number"
            value={formData.birth_year || ''}
            onChange={(e) => handleChange('birth_year', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Death Year</label>
          <input
            type="number"
            value={formData.death_year || ''}
            onChange={(e) => handleChange('death_year', e.target.value)}
          />
        </div>
      </div>
      <div className="form-group">
        <label>Country</label>
        <input
          type="text"
          value={formData.country_name || ''}
          onChange={(e) => handleChange('country_name', e.target.value)}
        />
      </div>
    </>
  );

  const renderWorkFields = () => (
    <>
      <div className="form-group">
        <label>Title</label>
        <input
          type="text"
          value={formData.title || ''}
          onChange={(e) => handleChange('title', e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>Composer</label>
        <input
          type="text"
          value={formData.composer?.full_name || ''}
          disabled
        />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Instrumentation</label>
          <input
            type="text"
            value={formData.instrumentation_detail || ''}
            onChange={(e) => handleChange('instrumentation_detail', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Composition Year</label>
          <input
            type="number"
            value={formData.composition_year ?? ''}
            onChange={(e) =>
              handleChange('composition_year', e.target.value ? Number(e.target.value) : null)
            }
            placeholder="e.g., 2006"
            min={1000}
            max={2100}
          />
        </div>
      </div>
      <div className="form-group">
        <label>Links</label>
        <LinkListEditor
          links={formData.links || []}
          onChange={(links) => setFormData({ ...formData, links })}
        />
      </div>
    </>
  );

  // Portaled to <body>: this modal is rendered from inside table cells, and on
  // mobile DataTable's sticky first column (position: sticky + z-index) forms a
  // stacking context that would trap the overlay behind later rows. No z-index
  // can escape that — only leaving the subtree can.
  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Suggest Changes</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="suggestion-form">
          {itemType === 'work' && loadingDetail
            ? <p className="loading-detail">Loading work details…</p>
            : itemType === 'composer' ? renderComposerFields() : renderWorkFields()}

          <div className="form-group">
            <label>Additional Comments (optional)</label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Explain your suggested changes..."
              rows={3}
            />
          </div>

          {submitStatus === 'success' && (
            <div className="success-message">
              Thank you! Your suggestion has been submitted.
            </div>
          )}

          {submitStatus === 'error' && (
            <div className="error-message">
              Failed to submit suggestion. Please try again.
            </div>
          )}

          <div className="modal-actions">
            <button type="button" onClick={onClose} className="btn-cancel">
              Cancel
            </button>
            <button type="submit" disabled={isSubmitting} className="btn-submit">
              {isSubmitting ? 'Submitting...' : 'Submit Suggestion'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
