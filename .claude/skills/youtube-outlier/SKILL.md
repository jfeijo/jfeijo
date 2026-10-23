---
name: youtube-outlier
description: Find YouTube outlier videos (far more views than usual for a topic in the last 30 days) for the Roses Unfiltered channel (Guns N' Roses and classic rock, pt-BR), explain why they worked, and turn them into video ideas. Use when the user says "ytoutlier", "outliers", "what's trending", "o que está bombando", or asks for video ideas based on what is performing on YouTube.
---

# YouTube Outlier — Roses Unfiltered

Adapted from ClawHub `dalime/youtube-outlier-skill` v1.0.1 (see `UPSTREAM_README.md`, `skill-card.md`).

Channel config: `projects/roses-unfiltered.json` (topics, language pt, region BR, last 30 days).
If the user names other topics, use those instead of the config list.

## Mode A — with a YouTube API key (most accurate)
Use this when the user gives a `YOUTUBE_API_KEY` (ask for it if they want exact view counts).

```bash
cd scripts && npm install
YOUTUBE_API_KEY=... npx ts-node index.ts --project=roses-unfiltered --dry-run
# one-off topics: add --niche="Slash, Izzy Stradlin"
```

The script writes `output/roses-unfiltered-<date>.csv` with:
date, niche, title, channel, views, outlier_score (views ÷ median of the search), url, thumbnail, main_idea, key_points, hashtags.
Optional env vars: `ANTHROPIC_API_KEY` (summaries), `GOOGLE_SHEETS_CREDENTIALS_JSON` (append to the sheet in the config),
`DISCORD_BOT_TOKEN` + `DISCORD_CHANNEL_ID` (post a summary). Drop `--dry-run` only when the user wants those sent.

If `npm install` or the YouTube API is blocked by the sandbox network, say so and use Mode B.

## Mode B — no key (web search)
For each topic in the config, search the web/YouTube for videos from the last 30 days and pick the ones with
clearly more views than the others on the same topic (or than the channel's usual views). Report what you can verify;
never invent view counts — mark them "aprox." or "n/d" when unsure.

## Output to the user (in Portuguese)
1. Table: título, canal, views, score/por que é outlier, link.
2. Padrões em comum (tema, formato, título, thumbnail).
3. 3–5 ideias de vídeo para o Roses Unfiltered inspiradas nos outliers, cada uma com título sugerido.
