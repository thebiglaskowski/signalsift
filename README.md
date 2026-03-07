# SignalSift

<p align="center">
  <img src="assets/signalsift.png" alt="Claude Conductor Logo" width="600">
</p>

**Your personal internet research assistant.** Automatically monitors Reddit, YouTube, and Hacker News for topics you care about, scores content by relevance, spots trends, and generates clean markdown reports you can read or feed into AI tools.

> *"Like having a research assistant who reads the internet for you."*

---

## What It Does

SignalSift runs on a simple loop: **scan → score → report**.

1. **Scans** subreddits, YouTube channels, and Hacker News on demand or via cron
2. **Scores** each piece of content against your keywords using semantic matching — so "startup" also catches "side project", "bootstrapped", "indie hacker", etc.
3. **Spots trends** — tracks which topics are rising or cooling over time
4. **Generates markdown reports** organized by source and relevance, ready for reading or pasting into ChatGPT/Claude for deeper analysis

What makes it different from just using RSS:
- Keyword scoring filters out noise — only content that actually matches your interests gets surfaced
- Semantic matching (optional) catches synonyms and related concepts, not just exact strings
- Trend detection shows you what's gaining momentum, not just what's new
- AI summarization (optional) gives you a one-paragraph digest of long threads

---

## Prerequisites

- **Python 3.11+** — check with `python --version`
- **uv** — fast Python package manager ([install guide](https://docs.astral.sh/uv/))

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install uv (Windows PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

No other setup is required to get started — Reddit works via RSS with zero credentials.

---

## Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/thebiglaskowski/SignalSift.git
cd SignalSift

# 2. Create a virtual environment and install
uv venv
uv pip install -e .

# 3. Copy the environment file (fill in keys later — none required to start)
cp .env.example .env

# 4. Initialize the database with example sources and keywords
uv run sift init

# 5. Run your first scan
uv run sift scan

# 6. Generate a report
uv run sift report
```

Open the `reports/` folder — there's a dated markdown file waiting for you (e.g., `reports/2025-01-14.md`).

The default setup includes popular subreddits (programming, LocalLLaMA, startups, etc.) and a set of signal-oriented keywords. You'll want to swap these out for your own interests — see [Configuration](#configuration) below.

---

## Configuration

### Adding Sources

SignalSift tracks three types of sources: subreddits, YouTube channels, and Hacker News (always on).

```bash
# Add subreddits
uv run sift sources add reddit programming
uv run sift sources add reddit MachineLearning
uv run sift sources add reddit SideProject

# Add YouTube channels (use the channel ID, not the handle)
# Find it at: youtube.com/@channelname/about → scroll to "Channel ID"
uv run sift sources add youtube UC8butISFwT-Wl7EV0hUK0BQ

# Remove a source
uv run sift sources remove reddit programming

# List everything you're tracking
uv run sift sources list
```

Hacker News is always scanned — there's no source to add.

### Setting Keywords

Keywords are what SignalSift scores content against. Each keyword belongs to a category, which keeps them organized and lets you apply different weights per group.

```bash
# Add one or more keywords — category is required
uv run sift keywords add "machine learning" "fine tuning" --category techniques
uv run sift keywords add "switched from" "compared to" --category tool_mentions
uv run sift keywords add "what worked for me" "case study" --category success_signals

# Add with a custom weight (default is 1.0; higher = more influential)
uv run sift keywords add "case study" "success story" --category success_signals --weight 1.5

# See available built-in categories
uv run sift keywords categories

# List all keywords (grouped by category)
uv run sift keywords list

# Filter by category
uv run sift keywords list --category techniques

# Remove a keyword
uv run sift keywords remove "machine learning"
```

**Built-in categories:**

| Category | Use for |
|----------|---------|
| `success_signals` | Posts about wins, results, strategies that worked |
| `pain_points` | Frustrations, problems, things not working |
| `tool_mentions` | Software, tools, comparisons |
| `techniques` | Methods, tactics, how-tos |
| `monetization` | Revenue, income, pricing discussions |
| `ai_visibility` | AI search, LLM mentions, GEO |
| `content_generation` | AI writing, content automation |

You can also use any custom category name — e.g., `--category crypto` or `--category competitors`.

**Tips for good keywords:**
- Phrases beat single words — `"side project launch"` is much more targeted than `"project"`
- Intent patterns catch high-signal posts — `"switched from"`, `"struggling with"`, `"what worked for me"`
- Use `--weight 1.5` for your highest-priority signals

### Topic-Filtered Reports

If you track multiple unrelated subjects (e.g., crypto, SEO, webdev), you can generate a focused report for just one of them:

```bash
# See which topics have keywords configured
uv run sift report --list-topics

# Generate a report for one topic only
uv run sift report --topic crypto
uv run sift report --topic content_generation
uv run sift report --topic keyword_research
```

Topic names come from the `--category` you used when adding keywords. The filtered report is saved as `reports/YYYY-MM-DD-<topic>.md` so it won't overwrite your full report. No extra source configuration is needed — topics are just a filter on content already in your database from your normal scans.

### Tuning Settings

The main knobs live in `src/signalsift/config/defaults.py`, but key values can be overridden via environment variables or a `config.yaml` file at the project root.

**Reddit settings:**

| Setting | Default | What it does |
|---------|---------|--------------|
| `REDDIT_MIN_SCORE` | `10` | Minimum post upvotes to include |
| `REDDIT_MIN_COMMENTS` | `3` | Minimum comment count |
| `REDDIT_MAX_AGE_DAYS` | `30` | How far back to look |
| `REDDIT_POSTS_PER_SUBREDDIT` | `100` | Posts to fetch per subreddit per scan |

**YouTube settings:**

| Setting | Default | What it does |
|---------|---------|--------------|
| `YOUTUBE_MIN_DURATION` | `300` (5 min) | Skip very short videos |
| `YOUTUBE_MAX_DURATION` | `5400` (90 min) | Skip very long videos |
| `YOUTUBE_MAX_AGE_DAYS` | `30` | How far back to look |
| `YOUTUBE_VIDEOS_PER_CHANNEL` | `10` | Videos to fetch per channel |

**Scoring:**

| Setting | Default | What it does |
|---------|---------|--------------|
| `MIN_RELEVANCE_SCORE` | `30` | Content below this score is excluded from reports |

**Report output:**

| Setting | Default | What it does |
|---------|---------|--------------|
| `MAX_ITEMS_PER_SECTION` | `15` | Items per source section in the report |
| `EXCERPT_LENGTH` | `300` | Character length of content excerpts |

---

## API Keys (Mostly Optional)

```bash
cp .env.example .env
# then edit .env with your keys
```

| Service | Required? | What you get |
|---------|-----------|--------------|
| Reddit API | No | Works via RSS by default — no signup needed |
| YouTube Data API v3 | Optional | Video metadata and channel scanning |
| OpenAI | Optional | AI-powered content summaries |
| Anthropic | Optional | AI-powered content summaries (Claude) |

### Reddit (no key needed by default)

SignalSift uses Reddit's public RSS feeds — no account, no approval process. If you hit rate limits or want additional metadata, you can optionally enable the full Reddit API:

1. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) and log in
2. Click **Create App** at the bottom
3. Choose **script** as the app type
4. Fill in any name and set redirect URI to `http://localhost:8080`
5. After creating, copy the **client ID** (shown under the app name) and the **secret**
6. Add them to `.env`:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   ```

### YouTube Data API v3

Required if you want to scan YouTube channels. The free tier (10,000 units/day) is more than enough for personal use.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and sign in
2. Click **Select a project → New Project**, give it a name, click **Create**
3. In the left menu go to **APIs & Services → Library**
4. Search for **YouTube Data API v3** and click **Enable**
5. Go to **APIs & Services → Credentials → + Create Credentials → API Key**
6. Copy the generated key and add it to `.env`:
   ```
   YOUTUBE_API_KEY=AIza...
   ```

To find a channel's ID (not the @handle): go to the channel on YouTube, click **About**, then look for **Share channel → Copy channel ID**. It starts with `UC`.

### OpenAI

Used for AI summarization of long threads. Optional — reports work fine without it.

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Click **+ Create new secret key**, give it a name
3. Copy the key (you won't see it again) and add to `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```

### Anthropic (Claude)

Alternative to OpenAI for AI summarization.

1. Go to [console.anthropic.com](https://console.anthropic.com/) and sign in
2. Navigate to **API Keys → + Create Key**
3. Copy the key and add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

---

## Optional Features

SignalSift has a base install that works without any extras, and three opt-in feature sets:

### NLP — Smart Keyword Matching (`.[nlp]`)

```bash
uv pip install -e ".[nlp]"
# Also download the spaCy language model:
uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl
```

Without NLP, keyword matching is exact string search. With NLP (spaCy), SignalSift does linguistic analysis — stemming, lemmatization, entity recognition. This means `"machine learning"` also catches `"ML models"`, `"learning algorithms"`, etc. Useful if your keywords are broad concepts rather than specific brand names.

### AI Summarization (`.[ai]`)

```bash
uv pip install -e ".[ai]"
```

Adds AI-powered summary generation to reports. Requires either `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in your `.env`. When enabled, each report section gets a short paragraph summarizing the key themes across all matching content — useful for getting the gist without reading every item.

### FAISS Semantic Search (`.[semantic]`)

```bash
uv pip install -e ".[semantic]"
```

FAISS (Facebook AI Similarity Search) accelerates semantic matching by 10–100x on large keyword sets. Without it, SignalSift uses a brute-force cosine similarity approach which is fine up to ~100 keywords. If you have hundreds of keywords or want faster scans, install this.

### Install Everything

```bash
uv pip install -e ".[all]"
# Plus the spaCy model if you want NLP:
uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl
```

---

## How It Works

```
Sources (Reddit RSS / YouTube API / HN API)
         ↓
    Raw content fetched and stored in SQLite
         ↓
    Keyword scoring — each item gets a relevance score
    based on how many keywords match and their weights
         ↓
    Trend analysis — compares score velocity over time
    to flag rising vs. declining topics
         ↓
    Optional: NLP enrichment, AI summarization
         ↓
    Markdown report generated from Jinja2 templates
```

Scores are additive: a post matching 3 keywords scores higher than one matching 1. Keyword weights let you rank certain signals higher (e.g., a post containing `"case study"` or `"what worked for me"` gets a 1.5x boost vs. a generic keyword match).

Everything is stored locally in SQLite at `data/signalsift.db` — no cloud, no external data services.

---

## Automating with Cron

Run SignalSift on a schedule to get daily digests without thinking about it.

**Daily at 7am (macOS/Linux):**

```bash
# Edit your crontab
crontab -e

# Add this line (adjust the path to your SignalSift directory)
0 7 * * * cd /path/to/SignalSift && uv run sift scan && uv run sift report
```

**Weekly on Monday mornings:**

```bash
0 8 * * 1 cd /path/to/SignalSift && uv run sift scan && uv run sift report
```

Reports are saved to `reports/YYYY-MM-DD.md`. Open the latest one with any markdown viewer, or drop it into your AI assistant of choice for a deeper digest.

---

## Commands Reference

| Command | What it does |
|---------|-------------|
| `uv run sift init` | Initialize database with example sources and keywords |
| `uv run sift scan` | Fetch new content from all configured sources |
| `uv run sift scan --reddit` | Scan Reddit only |
| `uv run sift scan --youtube` | Scan YouTube only |
| `uv run sift scan --hackernews` | Scan Hacker News only |
| `uv run sift report` | Generate a markdown report of recent content |
| `uv run sift report --list-topics` | Show available topic categories and exit |
| `uv run sift report --topic <category>` | Generate a report filtered to one topic (e.g. `crypto`, `seo`) |
| `uv run sift status` | Show database stats and configuration summary |
| `uv run sift sources list` | List all tracked sources |
| `uv run sift sources add <type> <id>` | Add a source (`reddit`, `youtube`) |
| `uv run sift sources remove <type> <id>` | Remove a source |
| `uv run sift keywords list` | List all keywords |
| `uv run sift keywords add <kw> [kw...] --category <cat>` | Add one or more keywords to a category |
| `uv run sift keywords categories` | List available keyword categories |
| `uv run sift keywords remove <kw>` | Remove a keyword |
| `uv run sift cache clear` | Remove old cached content |
| `uv run sift migrate --check` | Show pending database migrations |
| `uv run sift migrate` | Apply pending database migrations |

---

## Project Layout

```
SignalSift/
├── pyproject.toml            # Project config, dependencies, tool settings
├── uv.lock                   # Locked dependency versions
├── .env                      # Your API keys (git-ignored)
├── .env.example              # Template — copy this to .env
├── data/                     # SQLite database (git-ignored)
├── logs/                     # Debug logs (git-ignored)
├── reports/                  # Generated markdown reports (git-ignored)
└── src/signalsift/
    ├── cli/                  # Click command groups (user-facing interface)
    ├── config/               # Pydantic-settings config + defaults
    ├── database/             # SQLite connection, schema, queries, migrations
    ├── processing/           # Scoring, sentiment, trends, NLP, AI summarization
    ├── reports/
    │   └── templates/        # Jinja2 report templates (default.md.j2)
    ├── sources/              # Reddit (RSS+API), YouTube, HackerNews adapters
    ├── utils/                # Retry logic, logging, text helpers
    └── exceptions.py         # Custom exception hierarchy
```

---

## Development

### Setup

```bash
# Install with dev dependencies
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run full test suite
uv run pytest tests/ -v

# With coverage report
uv run pytest tests/ -v --cov=src/signalsift --cov-report=term-missing
```

**Test coverage: 80% (740 tests)**

### Quality Gates

All four gates must pass before committing:

```bash
uv run ruff check src/ tests/      # linting
uv run black --check src/ tests/   # formatting
uv run mypy src/                   # type checking
uv run pytest                      # tests
```

### Database Migrations

Schema changes are managed via a simple migration system in `src/signalsift/database/migrations.py`. Migrations run automatically on database init, but you can manage them manually:

```bash
uv run sift migrate --check        # see what's pending
uv run sift migrate                # apply all pending migrations
uv run sift migrate --version 2    # migrate to a specific version
```

### Why uv?

[uv](https://docs.astral.sh/uv/) is a Rust-based Python package manager that's 10–100x faster than pip. It handles virtual environments, dependency resolution, and script running in one tool. If you're used to `pip install` and `python -m`, just swap in `uv pip install` and `uv run`.

---

## Troubleshooting

**`uv run sift scan` returns no results**

- Check `uv run sift sources list` — you need at least one source configured
- Check `uv run sift keywords list` — you need keywords for scoring to work
- Run `uv run sift status` to see database stats
- Check `logs/signalsift.log` for errors

**YouTube scan fails with API errors**

- Confirm `YOUTUBE_API_KEY` is set in your `.env`
- Make sure the YouTube Data API v3 is enabled in your Google Cloud project (not just created — it must be explicitly enabled)
- The free quota is 10,000 units/day; each video fetch costs ~3 units

**Reddit scan is slow**

- The default RSS mode has a 2-second delay between requests to be polite to Reddit's servers. This is intentional.
- If you have many subreddits, expect scans to take a few minutes

**Reports are empty or very sparse**

- Lower `MIN_RELEVANCE_SCORE` — the default threshold of 30 may be filtering too aggressively for a fresh install
- Broaden your keywords — very specific phrases may not match much content yet
- Check the date range: `MAX_AGE_DAYS` controls how far back content is pulled

**`mypy` or `ruff` errors after pulling**

```bash
uv pip install -e ".[dev]"   # make sure dev deps are current
uv run ruff check src/ tests/ --fix   # auto-fix what's possible
```

---

## FAQ

**Q: Why use RSS for Reddit instead of the official API?**
Reddit's API now requires an approved app and has strict rate limits for third-party use. RSS is public, requires no account, and works indefinitely. The optional API mode is there if you specifically need higher-fidelity data.

**Q: Can I use this for any topic?**
Yes — just configure subreddits, YouTube channels, and keywords relevant to your interests. The defaults are tech/startup-oriented but there's nothing topic-specific in the engine.

**Q: Where do reports go?**
The `reports/` folder, named by date (e.g., `reports/2025-06-15.md`). The folder is git-ignored so reports don't clutter the repo.

**Q: Is my data sent anywhere?**
No — everything is stored locally in `data/signalsift.db`. The only outbound connections are to fetch content from Reddit/YouTube/HN, and optionally to OpenAI/Anthropic if you've configured AI summarization.

**Q: What's FAISS and do I need it?**
FAISS accelerates the semantic similarity search used during keyword scoring. It's optional — SignalSift falls back to a slower brute-force approach if FAISS isn't installed. For personal use with under ~100 keywords you won't notice the difference.

**Q: Can I add my own sources?**
Not yet via the CLI, but the `BaseSource` class in `src/signalsift/sources/base.py` is designed to be extended. Adding a new source adapter means implementing a handful of methods.

---

Built for personal use. MIT License.
