export type Instrument = 'guitar' | 'harmonica' | 'piano';

export interface SongData {
  title: string;
  artist: string;
  instrument: Instrument;
  query: string;
  videoId?: string;
  videoTitle?: string;
  lyrics?: string;
  chords?: string;
  songsterrId?: number;
  tabUrl?: string;
}
