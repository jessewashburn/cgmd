import api from './api';
import { Composer, Work, PaginatedResponse } from '../types';

export const composerService = {
  getAll: async (page = 1, search = '') => {
    const params: Record<string, string | number> = { page };
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
    const response = await api.get<PaginatedResponse<Work>>(`/composers/${id}/works/`);
    return response.data.results || [];
  },
};

export const workService = {
  getAll: async (page = 1, search = '') => {
    const params: Record<string, string | number> = { page };
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

  getHighlighted: async () => {
    const response = await api.get<Work>('/works/highlighted/');
    return response.data;
  },
};

interface Stats {
  total_composers: number;
  total_works: number;
}

// Client-side cache so multiple components don't re-fetch
let statsCache: Stats | null = null;
let statsFetching: Promise<Stats> | null = null;

export const statsService = {
  getSummary: async (): Promise<Stats> => {
    if (statsCache) return statsCache;
    if (statsFetching) return statsFetching;

    statsFetching = api.get<Stats>('/stats/summary/').then((res) => {
      statsCache = res.data;
      statsFetching = null;
      return res.data;
    });
    return statsFetching;
  },
};

// Preload stats at module load time so they're ready before React mounts.
// Swallow errors: a failed preload must not surface as an unhandled rejection.
statsService.getSummary().catch(() => {});
