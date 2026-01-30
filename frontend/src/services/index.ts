import api from './api';
import { Composer, Work, PaginatedResponse } from '../types';

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
  search: async (query: string, page = 1) => {
    const response = await api.get<PaginatedResponse<Work>>('/works/', {
      params: { search: query, page },
    });
    return response.data;
  },
};
