import { describe, it, expect } from 'vitest';
import { buildWorkFilterParams } from './WorkListPage';
import { buildComposerFilterParams } from './ComposerListPage';
import { DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX, TableFilterState } from '../hooks/useServerTable';

const noFilters: TableFilterState = {
  instrumentation: '',
  country: '',
  yearRange: [DEFAULT_YEAR_MIN, DEFAULT_YEAR_MAX],
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
    });
    expect(params).toEqual({
      instrumentation: 'Guitar solo',
      composer_country: 'Spain',
      composer_birth_year_min: 1800,
      composer_birth_year_max: 1900,
    });
  });

  it('omits the year range when only one bound changed but both equal defaults', () => {
    expect(buildWorkFilterParams({ ...noFilters, instrumentation: 'Duo' })).toEqual({
      instrumentation: 'Duo',
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
    });
    expect(params).toEqual({
      instrumentation: 'Guitar solo',
      country_name: 'Spain',
      birth_year_min: 1700,
      birth_year_max: 1850,
    });
  });
});
