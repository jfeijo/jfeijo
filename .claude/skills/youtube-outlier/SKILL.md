---
name: youtube-outlier
description: Find YouTube outlier videos (far above the median views for a topic in the last 30 days) for a channel project, summarize why they worked, and save them to the project's Google Sheet. Use for "ytoutlier", "outlier videos", "what's trending in my niche", or video ideas for Roses Unfiltered.
---

# YouTube Outlier (Roses Unfiltered)

Adapted from ClawHub `dalime/youtube-outlier-skill` v1.0.1 (see `UPSTREAM_README.md`, `skill-card.md`).

## Projects
- `projects/roses-unfiltered.json` — Roses Unfiltered (Guns N' Roses / classic rock, pt-BR).
  - Drive folder: https://drive.google.com/drive/folders/1nnS2QE8L7gX0QoSzFH0HnVXJMA7tSyAo
  - Output sheet: https://docs.google.com/spreadsheets/d/1jrevY_QI7ofhLqiTQlr___yrgcb6f45-x3MsE-bxqP0
  - Edit `niches` there to change the topics searched.

## How to run
1. `cp .env.example .env` in this folder and set at least `YOUTUBE_API_KEY`.
2. `cd scripts && npm install`
3. `npm run roses` — all niches of the project
   - one-off topics: `npx ts-node index.ts --project=roses-unfiltered --niche="Slash, Izzy Stradlin"`
   - preview only: add `--dry-run` (writes the local CSV, sends nothing)

Results always go to `output/<project>-<date>.csv`. They are also appended to the Google Sheet when
`GOOGLE_SHEETS_CREDENTIALS_JSON` is set, and posted to Discord when `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` are set.

If no service account is set up, Claude can copy the CSV rows into the sheet with the Google Drive connector instead.

## Columns
date, niche, title, channel, views, outlier_score (views ÷ median of the search), url, thumbnail, main_idea, key_points, hashtags
