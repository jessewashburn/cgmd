import api from './api';
import { Composer, Work, PaginatedResponse } from '../types';
import { fuzzySearchService } from '../utils/fuzzySearch';

// Cache for fuzzy search
let allWorks: Work[] = [];
let allComposers: Composer[] = [];
let worksLoaded = false;
let composersLoaded = false;

export const composerService = {
  getAll: async (page = 1, search = '') => {
    const params: any = { page };
    if (search) params.search = search;
    const response = await api.get<PaginatedResponse<Composer>>('/composers/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get<Composer>(`/composers/${id}/`);
    return response.data;
  },

  getByPeriod: async (period: string) => {
    const response = await api.get<Composer[]>(`/composers/by_period/?period=${period}`);
    return response.data;
  },

  getWorks: async (id: number) => {
    const response = await api.get<Work[]>(`/composers/${id}/works/`);
    return response.data;
  },
};

export const workService = {
  getAll: async (page = 1, search = '') => {
    const params: any = { page };
    if (search) params.search = search;
    const response = await api.get<PaginatedResponse<Work>>('/works/', { params });
    return response.data;
  },

  getById: async (id: number) => {
    const response = await api.get<Work>(`/works/${id}/`);
    return response.data;
  },

  getPopular: async () => {
    const response = await api.get<Work[]>('/works/popular/');
    return response.data;
  },

  getRecent: async () => {
    const response = await api.get<Work[]>('/works/recent/');
    return response.data;
  },
};

export const searchService = {
  // Traditional backend search
  search: async (query: string, page = 1) => {
    const response = await api.get<PaginatedResponse<Work>>('/works/', {
      params: { search: query, page },
    });
    return response.data;
  },

  // Fuzzy search for works (client-side)
  fuzzySearchWorks: async (query: string): Promise<Work[]> => {
    // Load all works if not already loaded
    if (!worksLoaded) {
      const allWorksData: Work[] = [];
      let page = 1;
      let hasMore = true;

      while (hasMore) {
        const response = await api.get<PaginatedResponse<Work>>('/works/', {
          params: { page, page_size: 100 },
        });
        allWorksData.push(...response.data.results);
        hasMore = response.data.next !== null;
        page++;
      }

      allWorks = allWorksData;
      fuzzySearchService.initializeWorks(allWorks);
      worksLoaded = true;
    }

    return fuzzySearchService.searchWorks(query);
  },

  // Fuzzy search for composers (client-side)
  fuzzySearchComposers: async (query: string): Promise<Composer[]> => {
    // Load all composers if not already loaded
    if (!composersLoaded) {
      const allComposersData: Composer[] = [];
      let page = 1;
      let hasMore = true;

      while (hasMore) {
        const response = await api.get<PaginatedResponse<Composer>>('/composers/', {
          params: { page, page_size: 100 },
        });
        allComposersData.push(...response.data.results);
        hasMore = response.data.next !== null;
        page++;
      }

      allComposers = allComposersData;
      fuzzySearchService.initializeComposers(allComposers);
      composersLoaded = true;
    }

    return fuzzySearchService.searchComposers(query);
  },

  // Combined fuzzy search (both works and composers)
  fuzzySearchAll: async (query: string) => {
    const [works, composers] = await Promise.all([
      searchService.fuzzySearchWorks(query),
      searchService.fuzzySearchComposers(query),
    ]);

    return { works, composers };
  },
};
