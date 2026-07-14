import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import { cognitoConfigured } from './amplify';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the Cognito access token (if signed in) as a bearer to every request.
// Amplify refreshes it transparently; when not signed in the request goes out
// anonymously (public reads still work).
api.interceptors.request.use(async (config) => {
  if (cognitoConfigured) {
    try {
      const { tokens } = await fetchAuthSession();
      const token = tokens?.accessToken?.toString();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // Not signed in — proceed anonymously.
    }
  }
  return config;
});

export default api;
