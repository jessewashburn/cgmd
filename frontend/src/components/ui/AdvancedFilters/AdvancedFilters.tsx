import { useState, useRef, useEffect } from 'react';
import { EraFacet } from '../../../hooks/useEraFacets';
import '../../../styles/shared/ListPage.css';

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
  /** Era chips. Omit `eras` to hide the row entirely (shared component). */
  eras?: EraFacet[];
  selectedEras?: string[];
  onEraToggle?: (slug: string) => void;
  /** Group label. "Era" on /composers; "Composer Era" on /works, where a bare
   *  "Era" would read as the work's era rather than its composer's. */
  eraLabel?: string;
  /** What the chip counts are counting, for the tooltip. */
  eraCountNoun?: string;
  /** "Include arrangements" checkbox. Omit `onIncludeArrangementsChange` to hide it —
   *  /composers has no use for it (shared component, like the era chips above).
   *
   *  Deliberately a checkbox and not a third "arrangements only" state: the ask was to
   *  include or exclude them, and defaulting to true makes unchecking the exclude. */
  includeArrangements?: boolean;
  onIncludeArrangementsChange?: (value: boolean) => void;
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
  eras,
  selectedEras = [],
  onEraToggle,
  eraLabel = 'Era',
  eraCountNoun = 'composers',
  includeArrangements = true,
  onIncludeArrangementsChange,
}: AdvancedFiltersProps) {
  const [showFilters, setShowFilters] = useState(false);
  const [showInstrumentationDropdown, setShowInstrumentationDropdown] = useState(false);
  const [showCountryDropdown, setShowCountryDropdown] = useState(false);
  const instrumentationRef = useRef<HTMLDivElement>(null);
  const countryRef = useRef<HTMLDivElement>(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (instrumentationRef.current && !instrumentationRef.current.contains(event.target as Node)) {
        setShowInstrumentationDropdown(false);
      }
      if (countryRef.current && !countryRef.current.contains(event.target as Node)) {
        setShowCountryDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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
          {/* Era chips — multi-select: picking two eras means either, not both.
              Counts reflect the other active filters, so a chip reading (0) is a
              dead end the user can see before clicking it. */}
          {eras && eras.length > 0 && onEraToggle && (
            <div className="filter-group filter-group-wide">
              <label className="filter-label">{eraLabel}</label>
              <div className="era-chips" role="group" aria-label={`Filter by ${eraLabel.toLowerCase()}`}>
                {eras.map((era) => {
                  const selected = selectedEras.includes(era.slug);
                  // An unselected chip with no matches leads nowhere; dim it, but
                  // keep it clickable so a selected chip can always be turned off.
                  const empty = era.count === 0 && !selected;
                  return (
                    <button
                      key={era.slug}
                      type="button"
                      className={`era-chip${selected ? ' selected' : ''}${empty ? ' empty' : ''}`}
                      aria-pressed={selected}
                      title={`${era.label} (${era.start_year}–${era.end_year}) — ${era.count.toLocaleString()} ${eraCountNoun}`}
                      onClick={() => onEraToggle(era.slug)}
                    >
                      {era.label}
                      <span className="era-chip-count">{era.count.toLocaleString()}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

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
          <div className="filter-group" ref={instrumentationRef}>
            <label className="filter-label">Instrumentation</label>
            <div className="custom-dropdown">
              <button
                className="filter-select dropdown-button"
                onClick={() => setShowInstrumentationDropdown(!showInstrumentationDropdown)}
                type="button"
              >
                {selectedInstrumentation || 'All Instrumentations'}
                <span className="dropdown-arrow">{showInstrumentationDropdown ? '▲' : '▼'}</span>
              </button>
              {showInstrumentationDropdown && (
                <div className="dropdown-menu">
                  <div
                    className={`dropdown-option ${!selectedInstrumentation ? 'selected' : ''}`}
                    onClick={() => {
                      onInstrumentationChange('');
                      setShowInstrumentationDropdown(false);
                    }}
                  >
                    All Instrumentations
                  </div>
                  {instrumentations.map((inst) => (
                    <div
                      key={inst}
                      className={`dropdown-option ${selectedInstrumentation === inst ? 'selected' : ''}`}
                      onClick={() => {
                        onInstrumentationChange(inst);
                        setShowInstrumentationDropdown(false);
                      }}
                    >
                      {inst}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Country Dropdown */}
          <div className="filter-group" ref={countryRef}>
            <label className="filter-label">
              {yearRangeLabel.includes('Birth') ? 'Country' : 'Composer Country'}
            </label>
            <div className="custom-dropdown">
              <button
                className="filter-select dropdown-button"
                onClick={() => setShowCountryDropdown(!showCountryDropdown)}
                type="button"
              >
                {selectedCountry || 'All Countries'}
                <span className="dropdown-arrow">{showCountryDropdown ? '▲' : '▼'}</span>
              </button>
              {showCountryDropdown && (
                <div className="dropdown-menu">
                  <div
                    className={`dropdown-option ${!selectedCountry ? 'selected' : ''}`}
                    onClick={() => {
                      onCountryChange('');
                      setShowCountryDropdown(false);
                    }}
                  >
                    All Countries
                  </div>
                  {countries.map((country) => (
                    <div
                      key={country}
                      className={`dropdown-option ${selectedCountry === country ? 'selected' : ''}`}
                      onClick={() => {
                        onCountryChange(country);
                        setShowCountryDropdown(false);
                      }}
                    >
                      {country}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Include arrangements — works list only. On by default: an arrangement with
              a real score to link to is repertoire, so it belongs in the list unless the
              user says otherwise. Unchecking is the filter-out. */}
          {onIncludeArrangementsChange && (
            <div className="filter-group">
              <label className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={includeArrangements}
                  onChange={(e) => onIncludeArrangementsChange(e.target.checked)}
                />
                <span>Include arrangements</span>
              </label>
            </div>
          )}

          {/* Clear Filters Button */}
          <button className="clear-filters-button" onClick={onClearFilters}>
            Clear Filters
          </button>
        </div>
      )}
    </>
  );
}
