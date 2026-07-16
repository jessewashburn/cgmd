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
 * Lives here rather than beside EraConflictNotice so that the notice file exports
 * only its component (a module mixing the two breaks React Fast Refresh). The page
 * calls this to choose between the notice and its generic "nothing found" message —
 * they'd otherwise both render, and the generic line is both redundant and less
 * informative once we can name the actual culprit.
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
