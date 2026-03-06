# Feature Documentation

> One doc per feature. Claude reads the relevant doc before touching any code.
> Working on a feature? Find it in the table below and read the doc first.

## Lookup Table

| Feature | Doc | Description |
|---------|-----|-------------|
| Database & Config | `documentation/01-database-config.md` | SQLite setup, migrations, settings, .env |
| Sources Management | `documentation/02-sources.md` | Add/remove/enable subreddits and YouTube channels |
| Keywords Management | `documentation/03-keywords.md` | Add/remove keywords with categories and weights |
| Content Scanning | `documentation/04-scan.md` | Fetch content from Reddit (RSS/API), YouTube, Hacker News |
| Relevance Scoring | `documentation/05-scoring.md` | 0-100 scoring engine for Reddit, YouTube, HN content |
| Report Generation | `documentation/06-reports.md` | Generate markdown reports from cached content |
| Cache Management | `documentation/07-cache.md` | Stats, prune, reset, export, clear cached content |
| Competitive Intelligence | `documentation/08-competitive-intelligence.md` | Track tool mentions, sentiment, feature gaps |

## Doc-First Workflow

When working on a feature:
1. Find the feature in the lookup table above
2. Read the full doc before writing any code
3. If no doc exists, run `/cs-docs "feature name"` to generate one
4. Update the doc if implementation reveals a mismatch

## Quality Bar

A good feature doc lets Claude implement the feature correctly without reading source code.
Business rules matter more than API shapes. Claude can infer patterns — it cannot infer limits,
cascade rules, permission gates, or state machines.
