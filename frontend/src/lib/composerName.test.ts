import { describe, it, expect } from 'vitest';
import { youtubeSearchQuery } from './composerName';

describe('youtubeSearchQuery', () => {
  it('flips "Last, First" into natural order', () => {
    expect(youtubeSearchQuery('Kleine Serenade', 'Poser, Hans')).toBe(
      'Kleine Serenade Hans Poser'
    );
  });

  it('keeps multi-word first names together', () => {
    expect(youtubeSearchQuery('Passaggio', 'Aa, Michel van der')).toBe(
      'Passaggio Michel van der Aa'
    );
  });

  it('leaves names already in natural order alone', () => {
    expect(youtubeSearchQuery('Capricho Árabe', 'Francisco Tárrega')).toBe(
      'Capricho Árabe Francisco Tárrega'
    );
  });

  it('omits a missing composer', () => {
    expect(youtubeSearchQuery('Kleine Serenade', null)).toBe('Kleine Serenade');
  });
});
