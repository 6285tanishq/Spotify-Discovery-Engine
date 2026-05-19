declare module 'yt-search' {
  interface VideoResult {
    videoId: string;
    title: string;
    description: string;
    url: string;
    thumbnail: string;
    image: string;
    seconds: number;
    timestamp: string;
    duration: {
      seconds: number;
      timestamp: string;
    };
    ago: string;
    views: number;
    author: {
      name: string;
      url: string;
    };
  }

  interface SearchResult {
    videos: VideoResult[];
    playlists: unknown[];
    accounts: unknown[];
  }

  function ytSearch(query: string): Promise<SearchResult>;
  export = ytSearch;
}
