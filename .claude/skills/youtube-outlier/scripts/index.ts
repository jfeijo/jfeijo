// YouTube outlier finder (adapted from dalime/youtube-outlier-skill v1.0.1)
// Usage: npx ts-node index.ts --project=roses-unfiltered [--niche="Slash, Duff"] [--dry-run]
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
import { google } from 'googleapis';
import { Client as DiscordClient, TextChannel } from 'discord.js';
import { getYoutubeOutlierVideos, extractVideoMetadata, EnrichedVideo } from './youtubeUtils';

dotenv.config({ path: path.join(__dirname, '..', '.env') });

interface Project {
  name: string;
  sheetId?: string;
  sheetRange?: string;
  relevanceLanguage?: string;
  regionCode?: string;
  daysBack?: number;
  niches: string[];
}

function arg(name: string): string | undefined {
  const a = process.argv.find(x => x.startsWith(`--${name}=`));
  return a ? a.slice(name.length + 3) : undefined;
}

function loadProject(slug: string): Project {
  const file = path.join(__dirname, '..', 'projects', `${slug}.json`);
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function toRow(niche: string, v: EnrichedVideo): string[] {
  return [
    new Date().toISOString().slice(0, 10), niche, v.title, v.channelTitle, String(v.viewCount),
    String(v.outlierScore), v.url, v.thumbnail, v.mainIdea, v.keyPoints, v.hashtags.join(' '),
  ];
}

function csvLine(row: string[]): string {
  return row.map(c => `"${c.replace(/"/g, '""')}"`).join(',');
}

async function appendToSheet(sheetId: string, range: string, rows: string[][]) {
  const auth = new google.auth.GoogleAuth({
    credentials: JSON.parse(process.env.GOOGLE_SHEETS_CREDENTIALS_JSON || '{}'),
    scopes: ['https://www.googleapis.com/auth/spreadsheets'],
  });
  const sheets = google.sheets({ version: 'v4', auth });
  await sheets.spreadsheets.values.append({
    spreadsheetId: sheetId, range, valueInputOption: 'RAW', requestBody: { values: rows },
  });
}

async function postToDiscord(title: string, rows: string[][]) {
  const client = new DiscordClient({ intents: [] });
  await client.login(process.env.DISCORD_BOT_TOKEN);
  try {
    const channel = await client.channels.fetch(process.env.DISCORD_CHANNEL_ID!);
    if (channel?.isTextBased()) {
      const lines = rows.slice(0, 15).map(r => `• ${r[2]} (${r[5]}x) <${r[6]}>`);
      const msg = `**${title}**\n${lines.join('\n')}`.slice(0, 1990);
      await (channel as TextChannel).send({ content: msg, allowedMentions: { parse: [] } });
    }
  } finally {
    await client.destroy();
  }
}

export async function run(projectSlug: string, nicheOverride?: string, dryRun = false) {
  const project = loadProject(projectSlug);
  const niches = nicheOverride ? nicheOverride.split(',').map(s => s.trim()).filter(Boolean) : project.niches;
  const opts = {
    daysBack: project.daysBack ?? 30,
    relevanceLanguage: project.relevanceLanguage,
    regionCode: project.regionCode,
  };

  const rows: string[][] = [];
  const seen = new Set<string>();
  for (const niche of niches) {
    const videos = (await getYoutubeOutlierVideos(niche, opts)).filter(v => !seen.has(v.id));
    videos.forEach(v => seen.add(v.id));
    for (const v of videos) rows.push(toRow(niche, await extractVideoMetadata(v)));
    console.log(`[${niche}] ${videos.length} outliers`);
  }
  rows.sort((a, b) => Number(b[5]) - Number(a[5]));

  // Always keep a local CSV copy.
  const outDir = path.join(__dirname, '..', 'output');
  fs.mkdirSync(outDir, { recursive: true });
  const csvFile = path.join(outDir, `${projectSlug}-${new Date().toISOString().slice(0, 10)}.csv`);
  fs.writeFileSync(csvFile, rows.map(csvLine).join('\n') + '\n');
  console.log(`Saved ${rows.length} rows to ${csvFile}`);

  if (dryRun || !rows.length) return `${rows.length} videos found${dryRun ? ' (dry run, nothing sent)' : ''}.`;

  if (project.sheetId && process.env.GOOGLE_SHEETS_CREDENTIALS_JSON) {
    await appendToSheet(project.sheetId, project.sheetRange || 'Sheet1!A1', rows);
    console.log('Appended to Google Sheet');
  }
  if (process.env.DISCORD_BOT_TOKEN && process.env.DISCORD_CHANNEL_ID) {
    await postToDiscord(`${project.name} — YouTube outliers`, rows);
    console.log('Posted to Discord');
  }
  return `${rows.length} videos saved.`;
}

if (require.main === module) {
  run(arg('project') || 'roses-unfiltered', arg('niche'), process.argv.includes('--dry-run'))
    .then(r => console.log('RESULT:', r))
    .catch(err => { console.error('ERROR:', err.message || err); process.exit(1); });
}
