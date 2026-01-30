import { useState } from 'react';

/**
 * Custom hook for managing sortable column state.
 * Toggles sort direction if the same column is clicked, otherwise sets new column to ascending.
 */
export function useSort<T extends string>(initialColumn: T | null = null) {
  const [sortColumn, setSortColumn] = useState<T | null>(initialColumn);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const handleSort = (column: T) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  return { sortColumn, sortDirection, handleSort };
}
