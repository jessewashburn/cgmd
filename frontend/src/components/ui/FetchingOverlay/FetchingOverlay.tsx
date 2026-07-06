import { ReactNode } from 'react';
import './FetchingOverlay.css';

interface FetchingOverlayProps {
  /** When true, dims the content and shows a spinner while keeping children on screen. */
  active: boolean;
  children: ReactNode;
}

/**
 * Wraps table content and shows a non-blocking loading veil during background refetches.
 * Pairs with TanStack Query's keepPreviousData so paging/sorting never flash empty.
 */
export default function FetchingOverlay({ active, children }: FetchingOverlayProps) {
  return (
    <div className="fetching-overlay-wrapper">
      {active && (
        <div className="fetching-overlay" aria-hidden="true">
          <div className="spinner" style={{ width: '24px', height: '24px' }} />
        </div>
      )}
      {children}
    </div>
  );
}
