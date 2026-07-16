import { EraConflict } from './detectEraConflict';

interface EraConflictNoticeProps {
  conflict: EraConflict;
  yearRange: [number, number];
  onWidenYearRange: (range: [number, number]) => void;
  onClearYearRange: () => void;
}

/**
 * Explains the one filter combination that can go wrong.
 *
 * Era tags are *derived from* birth years, so the era chips and the birth-year
 * slider are two views of a single axis. AND-ing them is correct but can be
 * baffling: "Baroque" + born 1900-2000 is legitimately zero rows, and an empty
 * table doesn't say why. Rather than making the query clever (auto-widening or
 * implicit ORs would be unpredictable), we keep the query honest and explain the
 * contradiction here — turning the two filters from adversaries into something
 * that teaches: picking an era shows you the birth years it implies.
 *
 * Render only when detectEraConflict() returns non-null.
 */
export default function EraConflictNotice({
  conflict,
  yearRange,
  onWidenYearRange,
  onClearYearRange,
}: EraConflictNoticeProps) {
  const { impliedMin, impliedMax, nameList } = conflict;

  return (
    <div className="era-conflict-notice">
      <p>
        <strong>{nameList}</strong> composers were born roughly{' '}
        <strong>
          {impliedMin}–{impliedMax}
        </strong>
        , but the birth-year filter is set to{' '}
        <strong>
          {yearRange[0]}–{yearRange[1]}
        </strong>
        . Those can&apos;t overlap, so nothing matches.
      </p>
      <div className="era-conflict-actions">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => onWidenYearRange([impliedMin, impliedMax])}
        >
          Widen birth years to {impliedMin}–{impliedMax}
        </button>
        <button type="button" className="clear-filters-button" onClick={onClearYearRange}>
          Clear birth-year range
        </button>
      </div>
    </div>
  );
}
