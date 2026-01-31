import { useState } from 'react';
import '../../../styles/shared/ListPage.css';

interface YearRangeFilterProps {
  label: string;
  yearRange: [number, number];
  onChange: (range: [number, number]) => void;
}

interface AdvancedFiltersProps {
  yearRangeLabel: string;
  yearRange: [number, number];
  onYearRangeChange: (range: [number, number]) => void;
  selectedInstrumentation: string;
  onInstrumentationChange: (value: string) => void;
  instrumentations: string[];
  selectedCountry: string;
  onCountryChange: (value: string) => void;
  countries: string[];
  onClearFilters: () => void;
}

export default function AdvancedFilters({
  yearRangeLabel,
  yearRange,
  onYearRangeChange,
  selectedInstrumentation,
  onInstrumentationChange,
  instrumentations,
  selectedCountry,
  onCountryChange,
  countries,
  onClearFilters,
}: AdvancedFiltersProps) {
  const [showFilters, setShowFilters] = useState(false);

  return (
    <>
      {/* Advanced Filters Toggle */}
      <div className="advanced-filters-toggle">
        <button
          className="toggle-button"
          onClick={() => setShowFilters(!showFilters)}
        >
          {showFilters ? '▲' : '▼'} Advanced Filters
        </button>
      </div>

      {/* Advanced Filters Panel */}
      {showFilters && (
        <div className="advanced-filters-panel">
          {/* Year Range Slider */}
          <div className="filter-group">
            <label className="filter-label">
              {yearRangeLabel}: {yearRange[0]} - {yearRange[1]}
            </label>
            <div className="slider-container">
              <input
                type="range"
                className="range-slider"
                min="1400"
                max="2025"
                value={yearRange[0]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  onYearRangeChange([Math.min(val, yearRange[1]), yearRange[1]]);
                }}
              />
              <input
                type="range"
                className="range-slider"
                min="1400"
                max="2025"
                value={yearRange[1]}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  onYearRangeChange([yearRange[0], Math.max(val, yearRange[0])]);
                }}
              />
            </div>
          </div>

          {/* Instrumentation Dropdown */}
          <div className="filter-group">
            <label className="filter-label">Instrumentation</label>
            <select
              className="filter-select"
              value={selectedInstrumentation}
              onChange={(e) => onInstrumentationChange(e.target.value)}
            >
              <option value="">All Instrumentations</option>
              {instrumentations.map((inst) => (
                <option key={inst} value={inst}>
                  {inst}
                </option>
              ))}
            </select>
          </div>

          {/* Country Dropdown */}
          <div className="filter-group">
            <label className="filter-label">
              {yearRangeLabel.includes('Birth') ? 'Country' : 'Composer Country'}
            </label>
            <select
              className="filter-select"
              value={selectedCountry}
              onChange={(e) => onCountryChange(e.target.value)}
            >
              <option value="">All Countries</option>
              {countries.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>

          {/* Clear Filters Button */}
          <button className="clear-filters-button" onClick={onClearFilters}>
            Clear Filters
          </button>
        </div>
      )}
    </>
  );
}
