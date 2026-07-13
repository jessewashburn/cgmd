import { useState } from 'react';
import api from '../../lib/api';
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

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      const suggestionType = itemType === 'composer' ? 'edit_composer' : 'edit_work';

      await api.post('/suggestions/', {
        suggestion_type: suggestionType,
        title: `Edit ${itemType}: ${itemData.full_name || itemData.title}`,
        description: comment || 'Suggested changes submitted via form',
        suggested_data: formData,
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
    </>
  );

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Suggest Changes</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="suggestion-form">
          {itemType === 'composer' ? renderComposerFields() : renderWorkFields()}

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
    </div>
  );
}
