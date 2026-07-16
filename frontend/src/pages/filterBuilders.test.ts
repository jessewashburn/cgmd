import { describe, it, expect } from 'vitest';
import { buildWorkFilterParams } from './WorkListPage';
import { buildComposerFilterParams } from './ComposerListPage';
import { DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX, TableFilterState } from '../hooks/useServerTable';

const noFilters: TableFilterState = {
  instrumentation: '',
  country: '',
  yearRange: [DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX],
  eras: [],
};

describe('buildWorkFilterParams', () => {
  it('omits everything at defaults', () => {
    expect(buildWorkFilterParams(noFilters)).toEqual({});
  });

  it('maps to the /works/ backend param names', () => {
    const params = buildWorkFilterParams({
      instrumentation: 'Guitar solo',
      country: 'Spain',
      yearRange: [1800, 1900],
      eras: [],
    });
    expect(params).toEqual({
      instrumentation: 'Guitar solo',
      composer_country: 'Spain',
      year_min: 1800,
      year_max: 1900,
    });
  });

  it('omits the year range when only one bound changed but both equal defaults', () => {
    expect(buildWorkFilterParams({ ...noFilters, instrumentation: 'Duo' })).toEqual({
      instrumentation: 'Duo',
    });
  });

  it('sends eras as CSV under composer_eras', () => {
    expect(buildWorkFilterParams({ ...noFilters, eras: ['romantic', 'modern'] })).toEqual({
      composer_eras: 'romantic,modern',
    });
  });
});

describe('buildComposerFilterParams', () => {
  it('omits everything at defaults', () => {
    expect(buildComposerFilterParams(noFilters)).toEqual({});
  });

  it('maps to the /composers/ backend param names', () => {
    const params = buildComposerFilterParams({
      instrumentation: 'Guitar solo',
      country: 'Spain',
      yearRange: [1700, 1850],
      eras: [],
    });
    expect(params).toEqual({
      instrumentation: 'Guitar solo',
      country_name: 'Spain',
      birth_year_min: 1700,
      birth_year_max: 1850,
    });
  });

  it('sends eras as CSV, not a repeated param', () => {
    expect(buildComposerFilterParams({ ...noFilters, eras: ['romantic', 'modern'] })).toEqual({
      eras: 'romantic,modern',
    });
  });

  it('omits eras when none are selected', () => {
    expect(buildComposerFilterParams({ ...noFilters, eras: [] })).toEqual({});
  });

  it('combines eras with the birth-year range (they AND on the backend)', () => {
    expect(
      buildComposerFilterParams({ ...noFilters, eras: ['baroque'], yearRange: [1900, 2000] }),
    ).toEqual({
      eras: 'baroque',
      birth_year_min: 1900,
      birth_year_max: 2000,
    });
  });
});
