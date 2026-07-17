import { useState } from 'react';
import { createPortal } from 'react-dom';
import api from '../../../lib/api';
import LinkListEditor, { DraftLink } from '../LinkListEditor';
import '../../features/SuggestionModal.css';

interface SuggestNewWorkModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SuggestNewWorkModal({ isOpen, onClose }: SuggestNewWorkModalProps) {
  const [formData, setFormData] = useState({
    composer_name: '',
    composer_birth_year: '',
    composer_death_year: '',
    composer_country: '',
    work_title: '',
    composition_year: '',
    instrumentation_detail: '',
    is_arrangement: false,
    comment: '',
    links: [] as DraftLink[],
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validate required fields
    if (!formData.composer_name || !formData.work_title) {
      alert('Please provide at least composer name and work title');
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus('idle');

    const cleanLinks = formData.links
      .map((l) => ({ label: l.label.trim(), url: l.url.trim(), link_type: l.link_type || 'other' }))
      .filter((l) => l.label && l.url);

    try {
      await api.post('/suggestions/', {
        suggestion_type: 'new_work',
        title: `New work: ${formData.work_title} by ${formData.composer_name}`,
        description: formData.comment || 'New work suggestion submitted via form',
        suggested_data: {
          ...formData,
          composition_year: formData.composition_year ? Number(formData.composition_year) : null,
          links: cleanLinks,
        },
      });

      setSubmitStatus('success');
      setTimeout(() => {
        onClose();
        setSubmitStatus('idle');
        setFormData({
          composer_name: '',
          composer_birth_year: '',
          composer_death_year: '',
          composer_country: '',
          work_title: '',
          composition_year: '',
          instrumentation_detail: '',
          is_arrangement: false,
          comment: '',
          links: [],
        });
      }, 2000);
    } catch (error) {
      console.error('Error submitting new work suggestion:', error);
      setSubmitStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (field: string, value: string | boolean) => {
    setFormData({ ...formData, [field]: value });
  };

  // Portaled to <body> for the same reason as SuggestionModal (which owns the
  // shared .modal-overlay styles): never let an ancestor stacking context trap it.
  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Suggest a New Work</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="suggestion-form">
          <div className="form-section">
            <h3>Composer Information</h3>
            
            <div className="form-group">
              <label>Composer Name *</label>
              <input
                type="text"
                value={formData.composer_name}
                onChange={(e) => handleChange('composer_name', e.target.value)}
                placeholder="Enter composer's full name"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Birth Year</label>
                <input
                  type="number"
                  value={formData.composer_birth_year}
                  onChange={(e) => handleChange('composer_birth_year', e.target.value)}
                  placeholder="e.g., 1950"
                />
              </div>
              <div className="form-group">
                <label>Death Year</label>
                <input
                  type="number"
                  value={formData.composer_death_year}
                  onChange={(e) => handleChange('composer_death_year', e.target.value)}
                  placeholder="Leave empty if living"
                />
              </div>
            </div>

            <div className="form-group">
              <label>Country/Nationality</label>
              <input
                type="text"
                value={formData.composer_country}
                onChange={(e) => handleChange('composer_country', e.target.value)}
                placeholder="e.g., Spain, Brazil"
              />
            </div>
          </div>

          <div className="form-section">
            <h3>Work Information</h3>

            <div className="form-group">
              <label>Work Title *</label>
              <input
                type="text"
                value={formData.work_title}
                onChange={(e) => handleChange('work_title', e.target.value)}
                placeholder="Enter the work's title"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Instrumentation</label>
                <input
                  type="text"
                  value={formData.instrumentation_detail}
                  onChange={(e) => handleChange('instrumentation_detail', e.target.value)}
                  placeholder="e.g., Solo Guitar, Guitar Duo"
                />
              </div>
              <div className="form-group">
                <label>Composition Year</label>
                <input
                  type="number"
                  value={formData.composition_year}
                  onChange={(e) => handleChange('composition_year', e.target.value)}
                  placeholder="e.g., 2006"
                  min={1000}
                  max={2100}
                />
              </div>
            </div>

            {/* Suggesting the tag doesn't set it: an admin has to apply the suggestion,
                and it then lands as basis='suggested' so the IMSLP importer won't
                overwrite the decision. No arranger field — one IMSLP page can host five
                arrangers, so the column doesn't exist. */}
            <div className="form-group">
              <label className="form-checkbox">
                <input
                  type="checkbox"
                  checked={formData.is_arrangement}
                  onChange={(e) => handleChange('is_arrangement', e.target.checked)}
                />
                <span>This is an arrangement (arranged or transcribed for guitar)</span>
              </label>
            </div>
          </div>

          <div className="form-section">
            <h3>Links</h3>
            <LinkListEditor
              links={formData.links}
              onChange={(links) => setFormData({ ...formData, links })}
            />
          </div>

          <div className="form-group">
            <label>Additional Information</label>
            <textarea
              value={formData.comment}
              onChange={(e) => handleChange('comment', e.target.value)}
              placeholder="Add any additional details, sources, or context..."
              rows={3}
            />
          </div>

          {submitStatus === 'success' && (
            <div className="success-message">
              Thank you! Your suggestion has been submitted for review.
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
