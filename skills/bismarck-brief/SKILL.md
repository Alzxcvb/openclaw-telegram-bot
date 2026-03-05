---
name: bismarck-brief
description: Fetch and summarize the latest Bismarck Brief articles from their Substack RSS feed. Articles are summarized by the OpenRouter API and delivered daily.
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - OPENROUTER_API_KEY
      bins:
        - curl
    primaryEnv: OPENROUTER_API_KEY
    emoji: "📋"
    always: false
---

# Bismarck Brief

Automatically fetch and summarize the latest articles from [Bismarck Brief](https://brief.bismarckanalysis.com), a strategic intelligence publication covering AI, geopolitics, technology, and global institutions.

## Overview

The Bismarck Brief publishes strategic analysis roughly weekly on topics including:
- Artificial Intelligence and frontier model development
- Geopolitical competition and defense
- Technology companies and institutional dynamics
- Energy, infrastructure, and manufacturing
- Global economic strategy

This skill integrates with your daily morning brief to deliver:
- **Latest article headline** with Substack URL
- **Key summary** (2-3 sentences) using OpenRouter API
- **Topic tag** (AI, Geopolitics, Defense, etc.)

## Configuration

The morning brief automatically fetches the Bismarck Brief RSS feed daily and includes new articles in your briefing.

### Environment Variables

- `OPENROUTER_API_KEY` — Required for AI summarization (shared with other services)
- `BISMARCK_BRIEF_RSS_URL` — Optional override (defaults to standard Substack RSS)
- `BISMARCK_BRIEF_MAX_ARTICLES` — Max articles per day (default: 3)

## How It Works

1. **Fetch RSS**: Daily check of the Bismarck Brief Substack RSS feed
2. **Track State**: Stores last-checked article date to avoid duplicates
3. **Summarize**: Uses OpenRouter (Perplexity Sonar Pro) to summarize new articles
4. **Format**: Converts summaries to Markdown for Telegram delivery

## State File

Articles are tracked in `morning-brief/bismarck_brief_state.json`:

```json
{
  "last_article_date": "2025-12-30T15:06:14.624Z",
  "articles_seen": [
    "introducing-ai-2026-the-global-state"
  ]
}
```

## Example Output

```
📋 *Bismarck Brief*

🤖 *"Carl Zeiss' Tradition of Knowledge in Optics"*
Zeiss manufactures the ultra-precise mirrors and lenses for ASML's EUV lithography machines.
80% of all chips worldwide depend on Zeiss optics—making it a critical bottleneck in AI hardware scaling.
[Read on Substack](https://brief.bismarckanalysis.com/p/carl-zeiss-tradition-of-knowledge)
```

## Topics Covered

| Tag | Examples |
|-----|----------|
| 🤖 **AI** | Frontier models, compute, data centers, AI companies |
| 🌍 **Geopolitics** | Great power competition, China-US tech, sanctions |
| 🛡️ **Defense** | Military strategy, contractors, weapons innovation |
| ⚡ **Infrastructure** | Energy grids, semiconductors, supply chains |
| 💼 **Business** | Leadership, institutional dynamics, market analysis |

## Integration

This skill is automatically included in your daily morning brief. No additional setup required — just ensure `OPENROUTER_API_KEY` is set in your Railway environment.
