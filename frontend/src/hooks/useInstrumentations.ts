import { useState, useEffect } from 'react';
import api from '../lib/api';

/**
 * Custom hook to fetch and filter instrumentation categories.
 * Filters out junk data like opus numbers and titles, keeping only valid instrumentation terms.
 */
export function useInstrumentations() {
  const [instrumentations, setInstrumentations] = useState<string[]>([]);

  useEffect(() => {
    const fetchInstrumentations = async () => {
      try {
        const response = await api.get('/instrumentations/', {
          params: { page_size: 500 }
        });
        const categories = response.data.results || response.data;
        
        // Filter for real instrumentation categories (not titles or junk)
        const validInstrumentations = categories
          .map((cat: any) => cat.name)
          .filter((name: string) => {
            if (!name || name.length < 3) return false;
            
            const lower = name.toLowerCase();
            
            // Include if it contains key instrumentation terms
            const hasValidTerms = 
              lower.includes('guitar') ||
              lower.includes('ensemble') ||
              lower.includes('orchestra') ||
              lower.includes('voice') ||
              lower.includes('choir') ||
              lower.includes('percussion') ||
              lower.includes('strings') ||
              lower.includes('wind') ||
              lower.includes('brass') ||
              (lower === 'solo') ||
              (lower === 'duo') ||
              (lower === 'trio') ||
              (lower === 'quartet') ||
              (lower === 'quintet') ||
              (lower === 'sextet') ||
              (lower === 'septet') ||
              (lower === 'octet');
            
            // Exclude if it looks like a title (has certain patterns)
            const looksLikeTitle = 
              lower.includes('op.') ||
              lower.includes('for ') ||
              lower.includes(' - ') ||
              lower.includes('bagatelle') ||
              lower.includes('study') ||
              lower.includes('etude') ||
              name.includes('#') ||
              /^\d+$/.test(name) || // Just a number
              name.length > 50; // Too long to be an instrumentation
            
            return hasValidTerms && !looksLikeTitle;
          });
        
        setInstrumentations(validInstrumentations);
      } catch (err) {
        console.error('Error fetching instrumentations:', err);
      }
    };
    
    fetchInstrumentations();
  }, []);

  return instrumentations;
}
