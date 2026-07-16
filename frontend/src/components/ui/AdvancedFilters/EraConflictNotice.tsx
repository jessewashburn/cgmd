import { EraFacet } from '../../../hooks/useEraFacets';
import { DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX } from '../../../hooks/useServerTable';

export interface EraConflict {
  /** Birth-year range implied by the selected eras, clamped to the slider's domain. */
  impliedMin: number;
  impliedMax: number;
  /** "Baroque" / "Baroque and Modern" — the selected eras, prose-joined. */
  nameList: string;
}

/**
 * Is the era selection contradicted by the birth-year range?
 *
 * Exported so the page can choose between this notice and its generic "nothing
 * found" message — they'd otherwise both render, and the generic line is both
 * redundant and less informative once we can name the actual culprit.
 *
 * Returns null when there's no conflict to explain.
 */
export function detectEraConflict(
  selectedEras: string[],
  eras: EraFacet[],
  yearRange: [number, number],
  yearRangeIsDefault: boolean,
): EraConflict | null {
  // Only a *deliberately* moved slider can conflict — at its defaults no birth-year
  // param is sent at all, so "just pick an era" never lands here.
  if (yearRangeIsDefault || selectedEras.length === 0) return null;

  const selected = eras.filter((era) => selectedEras.includes(era.slug));
  if (selected.length === 0) return null;

  // Union of the implied ranges: with several eras selected (an OR), any birth year
  // that suits one of them is enough.
  const rawMin = Math.min(...selected.map((e) => e.implied_birth_min));
  const rawMax = Math.max(...selected.map((e) => e.implied_birth_max));

  // Clamp to the slider's own domain — Renaissance implies births from 1325, which
  // the control can't represent. Clamping to the default floor is also semantically
  // right: at the defaults no birth-year param is sent, i.e. no birth-year filter.
  const impliedMin = Math.max(rawMin, DEFAULT_YEAR_MIN);
  const impliedMax = Math.min(rawMax, DEFAULT_YEAR_MAX);

  // The slider genuinely excludes every birth year the eras imply.
  if (yearRange[1] >= impliedMin && yearRange[0] <= impliedMax) return null;

  const names = selected.map((e) => e.label);
  const nameList =
    names.length === 1
      ? names[0]
      : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;

  return { impliedMin, impliedMax, nameList };
}

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
