// YouTube search and enrichment helpers (adapted from dalime/youtube-outlier-skill v1.0.1)
import axios from 'axios';
import Anthropic from '@anthropic-ai/sdk';

export interface SearchOptions {
  daysBack: number;
  relevanceLanguage?: string;
  regionCode?: string;
}

export interface YoutubeVideo {
  id: string;
  title: string;
  description: string;
  thumbnail: string;
  viewCount: number;
  publishedAt: string;
  channelTitle: string;
  url: string;
  outlierScore: number; // views divided by the median views of the search results
}

export interface EnrichedVideo extends YoutubeVideo {
  mainIdea: string;
  keyPoints: string;
  hashtags: string[];
}

const API_KEY = process.env.YOUTUBE_API_KEY || '';
const anthropic = process.env.ANTHROPIC_API_KEY ? new Anthropic() : null;
const MODEL = process.env.ANTHROPIC_MODEL || 'claude-haiku-5-5';

/** Searches recent videos for a niche and keeps the top 20% by views. */
export async function getYoutubeOutlierVideos(niche: string, opts: SearchOptions): Promise<YoutubeVideo[]> {
  if (!API_KEY) throw new Error('YOUTUBE_API_KEY is not set');
  const since = new Date(Date.now() - opts.daysBack * 864e5).toISOString();

  const search = await axios.get('https://www.googleapis.com/youtube/v3/search', {
    params: {
      part: 'snippet', type: 'video', maxResults: 50, order: 'viewCount',
      q: niche, publishedAfter: since, key: API_KEY,
      relevanceLanguage: opts.relevanceLanguage, regionCode: opts.regionCode,
    },
  });
  const ids = search.data.items.map((i: any) => i.id.videoId).filter(Boolean);
  if (!ids.length) return [];

  const details = await axios.get('https://www.googleapis.com/youtube/v3/videos', {
    params: { part: 'snippet,statistics', id: ids.join(','), key: API_KEY },
  });
  const videos = details.data.items.map((item: any) => ({
    id: item.id,
    title: item.snippet.title,
    description: item.snippet.description,
    thumbnail: item.snippet.thumbnails?.high?.url || '',
    viewCount: Number(item.statistics.viewCount || 0),
    publishedAt: item.snippet.publishedAt,
    channelTitle: item.snippet.channelTitle,
    url: `https://www.youtube.com/watch?v=${item.id}`,
    outlierScore: 0,
  })) as YoutubeVideo[];

  const sorted = [...videos].sort((a, b) => b.viewCount - a.viewCount);
  const median = sorted[Math.floor(sorted.length / 2)]?.viewCount || 1;
  sorted.forEach(v => (v.outlierScore = Math.round((v.viewCount / Math.max(median, 1)) * 10) / 10));
  return sorted.slice(0, Math.max(1, Math.floor(sorted.length * 0.2)));
}

/** Adds a short summary (via Claude, if ANTHROPIC_API_KEY is set) and hashtags. */
export async function extractVideoMetadata(video: YoutubeVideo): Promise<EnrichedVideo> {
  let mainIdea = '';
  let keyPoints = '';
  if (anthropic) {
    const msg = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 400,
      messages: [{
        role: 'user',
        content:
          'Analise este vídeo do YouTube. Na primeira linha, escreva a ideia principal em uma frase. ' +
          'Nas linhas seguintes, liste até 3 motivos prováveis para o vídeo ter performado acima da média.\n' +
          `Título: ${video.title}\nCanal: ${video.channelTitle}\nDescrição: ${video.description.slice(0, 2000)}`,
      }],
    });
    const text = msg.content.map(b => (b.type === 'text' ? b.text : '')).join('').trim();
    const [first, ...rest] = text.split('\n');
    mainIdea = first || '';
    keyPoints = rest.join('\n').trim();
  }
  const hashtags = (video.description.match(/#[\p{L}\p{N}_]+/gu) || []).map(s => s.slice(1));
  return { ...video, mainIdea, keyPoints, hashtags };
}
