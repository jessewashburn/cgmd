import { useState, useEffect } from 'react';
import api from '../services/api';

/**
 * Custom hook to fetch and sort country names.
 */
export function useCountries() {
  const [countries, setCountries] = useState<string[]>([]);

  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await api.get('/countries/', {
          params: { page_size: 500 }
        });
        const countryList = response.data.results || response.data;
        const countryNames = countryList
          .map((country: any) => country.name)
          .sort((a: string, b: string) => a.localeCompare(b));
        setCountries(countryNames);
      } catch (err) {
        console.error('Error fetching countries:', err);
      }
    };
    
    fetchCountries();
  }, []);

  return countries;
}
