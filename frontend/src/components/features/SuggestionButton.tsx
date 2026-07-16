import { useState } from 'react';
import { SuggestionTarget } from '../../types';
import SuggestionModal from './SuggestionModal';
import './SuggestionButton.css';

interface SuggestionButtonProps {
  itemType: 'composer' | 'work';
  itemData: SuggestionTarget;
}

export default function SuggestionButton({ itemType, itemData }: SuggestionButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <>
      <button
        className="suggestion-btn"
        onClick={() => setIsModalOpen(true)}
        title="Suggest changes"
        aria-label="Suggest changes"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>

      {isModalOpen && (
        <SuggestionModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          itemType={itemType}
          itemData={itemData}
        />
      )}
    </>
  );
}
