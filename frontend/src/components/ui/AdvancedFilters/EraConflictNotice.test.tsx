import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EraConflictNotice, { detectEraConflict } from './EraConflictNotice';
import { EraFacet } from '../../../hooks/useEraFacets';
import { DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX } from '../../../hooks/useServerTable';

const facet = (over: Partial<EraFacet> & { slug: string }): EraFacet => ({
  label: over.slug,
  start_year: 1580,
  end_year: 1750,
  implied_birth_min: 1505,
  implied_birth_max: 1730,
  count: 0,
  ...over,
});

const BAROQUE = facet({ slug: 'baroque', label: 'Baroque' });
const MODERN = facet({
  slug: 'modern',
  label: 'Modern',
  start_year: 1890,
  end_year: 2000,
  implied_birth_min: 1815,
  implied_birth_max: 1980,
});
// Implied births start at 1325 — below the slider's floor, so it must be clamped.
const RENAISSANCE = facet({
  slug: 'renaissance',
  label: 'Renaissance',
  start_year: 1400,
  end_year: 1600,
  implied_birth_min: 1325,
  implied_birth_max: 1580,
});
const ERAS = [BAROQUE, MODERN, RENAISSANCE];

describe('detectEraConflict', () => {
  it('is null when the year range is untouched', () => {
    // The common path: picking an era sends no birth-year param at all.
    expect(
      detectEraConflict(['baroque'], ERAS, [DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX], true),
    ).toBeNull();
  });

  it('is null when no era is selected', () => {
    expect(detectEraConflict([], ERAS, [1900, 2000], false)).toBeNull();
  });

  it('is null when the facets have not loaded yet', () => {
    expect(detectEraConflict(['baroque'], [], [1900, 2000], false)).toBeNull();
  });

  it('is null when the era and the year range actually overlap', () => {
    // Baroque implies births 1505-1730; 1600-1700 sits inside that, so an empty
    // result is some other filter's doing and this notice would be a lie.
    expect(detectEraConflict(['baroque'], ERAS, [1600, 1700], false)).toBeNull();
  });

  it('is null when the ranges merely touch at one year', () => {
    expect(detectEraConflict(['baroque'], ERAS, [1730, 2000], false)).toBeNull();
  });

  it('reports a genuine conflict with the implied range', () => {
    expect(detectEraConflict(['baroque'], ERAS, [1900, 2000], false)).toEqual({
      impliedMin: 1505,
      impliedMax: 1730,
      nameList: 'Baroque',
    });
  });

  it('unions the implied ranges when several eras are selected (they OR)', () => {
    expect(detectEraConflict(['baroque', 'modern'], ERAS, [1400, 1450], false)).toEqual({
      impliedMin: 1505,
      impliedMax: 1980,
      nameList: 'Baroque and Modern',
    });
  });

  it("clamps the implied range to the slider's own domain", () => {
    // Renaissance implies births from 1325, which the 1400-floored slider can't
    // represent — offering it would set a range the control couldn't show.
    expect(detectEraConflict(['renaissance'], ERAS, [1900, 2000], false)).toEqual({
      impliedMin: DEFAULT_YEAR_MIN,
      impliedMax: 1580,
      nameList: 'Renaissance',
    });
  });
});

describe('EraConflictNotice', () => {
  const conflict = { impliedMin: 1505, impliedMax: 1730, nameList: 'Baroque' };

  it('spells out both ranges', () => {
    render(
      <EraConflictNotice
        conflict={conflict}
        yearRange={[1900, 2000]}
        onWidenYearRange={() => {}}
        onClearYearRange={() => {}}
      />,
    );
    expect(screen.getByText(/Baroque/)).toBeInTheDocument();
    expect(screen.getByText('1505–1730')).toBeInTheDocument();
    expect(screen.getByText('1900–2000')).toBeInTheDocument();
  });

  it('offers to widen the range to the era, and reports the years it will set', async () => {
    const onWidenYearRange = vi.fn();
    render(
      <EraConflictNotice
        conflict={conflict}
        yearRange={[1900, 2000]}
        onWidenYearRange={onWidenYearRange}
        onClearYearRange={() => {}}
      />,
    );

    await userEvent.click(
      screen.getByRole('button', { name: /Widen birth years to 1505–1730/ }),
    );
    expect(onWidenYearRange).toHaveBeenCalledWith([1505, 1730]);
  });

  it('offers to clear the birth-year range', async () => {
    const onClearYearRange = vi.fn();
    render(
      <EraConflictNotice
        conflict={conflict}
        yearRange={[1900, 2000]}
        onWidenYearRange={() => {}}
        onClearYearRange={onClearYearRange}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /Clear birth-year range/ }));
    expect(onClearYearRange).toHaveBeenCalled();
  });
});
