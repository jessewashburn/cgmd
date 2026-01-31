import Fuse, { IFuseOptions } from 'fuse.js';
import { Work, Composer } from '../types';

/**
 * Strip leading symbols and punctuation from a string for sorting purposes
 * So "'Untitled" becomes "Untitled" and sorts under 'U'
 */
export function stripLeadingSymbols(str: string): string {
  return str.replace(/^[^\w\s]+/, '');
}

// Configuration for Work search
const workSearchOptions: IFuseOptions<Work> = {
  keys: [
    { name: 'title', weight: 2 },
    { name: 'composer.full_name', weight: 1.5 },
    { name: 'instrumentation_detail', weight: 0.5 },
    { name: 'catalog_number', weight: 0.8 },
  ],
  threshold: 0.4, // Lower = more strict (0.0 = exact match, 1.0 = match anything)
  includeScore: true,
  minMatchCharLength: 2,
  ignoreLocation: true,
};

// Configuration for Composer search
const composerSearchOptions: IFuseOptions<Composer> = {
  keys: [
    { name: 'full_name', weight: 2 },
    { name: 'first_name', weight: 1 },
    { name: 'last_name', weight: 1.5 },
    { name: 'period', weight: 0.5 },
    { name: 'country.name', weight: 0.3 },
  ],
  threshold: 0.4,
  includeScore: true,
  minMatchCharLength: 2,
  ignoreLocation: true,
};

export class FuzzySearchService {
  private workFuse: Fuse<Work> | null = null;
  private composerFuse: Fuse<Composer> | null = null;

  initializeWorks(works: Work[]) {
    this.workFuse = new Fuse(works, workSearchOptions);
  }

  initializeComposers(composers: Composer[]) {
    this.composerFuse = new Fuse(composers, composerSearchOptions);
  }

  searchWorks(query: string): Work[] {
    if (!this.workFuse || !query) return [];
    const results = this.workFuse.search(query);
    return results.map(result => result.item);
  }

  searchComposers(query: string): Composer[] {
    if (!this.composerFuse || !query) return [];
    const results = this.composerFuse.search(query);
    return results.map(result => result.item);
  }

  updateWorks(works: Work[]) {
    this.initializeWorks(works);
  }

  updateComposers(composers: Composer[]) {
    this.initializeComposers(composers);
  }
}

export const fuzzySearchService = new FuzzySearchService();
