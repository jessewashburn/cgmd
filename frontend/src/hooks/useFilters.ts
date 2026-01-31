import { useState } from 'react';

export function useFilters() {
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [yearRange, setYearRange] = useState<[number, number]>([1400, 2025]);
  const [selectedInstrumentation, setSelectedInstrumentation] = useState<string>('');
  const [selectedCountry, setSelectedCountry] = useState<string>('');

  const clearFilters = () => {
    setYearRange([1400, 2025]);
    setSelectedInstrumentation('');
    setSelectedCountry('');
  };

  return {
    showAdvancedFilters,
    setShowAdvancedFilters,
    yearRange,
    setYearRange,
    selectedInstrumentation,
    setSelectedInstrumentation,
    selectedCountry,
    setSelectedCountry,
    clearFilters,
  };
}
