"""Default configuration values for SignalSift."""

from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

# Database
DEFAULT_DB_PATH = DATA_DIR / "signalsift.db"

# Reddit defaults
DEFAULT_REDDIT_USER_AGENT = "SignalSift/1.0 (personal research tool)"
DEFAULT_REDDIT_MIN_SCORE = 10
DEFAULT_REDDIT_MIN_COMMENTS = 3
DEFAULT_REDDIT_MAX_AGE_DAYS = 30
DEFAULT_REDDIT_POSTS_PER_SUBREDDIT = 100
DEFAULT_REDDIT_REQUEST_DELAY = 2.0

# YouTube defaults
DEFAULT_YOUTUBE_MIN_DURATION = 300  # 5 minutes
DEFAULT_YOUTUBE_MAX_DURATION = 5400  # 90 minutes
DEFAULT_YOUTUBE_MAX_AGE_DAYS = 30
DEFAULT_YOUTUBE_VIDEOS_PER_CHANNEL = 10
DEFAULT_YOUTUBE_TRANSCRIPT_LANGUAGE = "en"
DEFAULT_YOUTUBE_TRANSCRIPT_MAX_LENGTH = 50000

# Scoring defaults
DEFAULT_MIN_RELEVANCE_SCORE = 30

# Report defaults
DEFAULT_MAX_ITEMS_PER_SECTION = 15
DEFAULT_EXCERPT_LENGTH = 300

# Logging defaults
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_MAX_SIZE_MB = 10
DEFAULT_LOG_BACKUP_COUNT = 3

# =============================================================================
# DEFAULT SUBREDDITS - Example communities (customize for your interests)
# =============================================================================
# Tier 1: High signal, professional discussions
# Tier 2: Medium signal, good community engagement
# Tier 3: Supplementary, broader topics

DEFAULT_SUBREDDITS = {
    1: [
        # Technology & Programming
        "programming",
        "webdev",
        "learnprogramming",
        # AI & Machine Learning
        "MachineLearning",
        "artificial",
        "LocalLLaMA",
    ],
    2: [
        # Startups & Business
        "startups",
        "Entrepreneur",
        "SideProject",
        # Tech News
        "technology",
        "tech",
        # Productivity
        "productivity",
        "getdisciplined",
    ],
    3: [
        # General Interest
        "InternetIsBeautiful",
        "dataisbeautiful",
        "todayilearned",
        # Self Improvement
        "selfimprovement",
        "DecidingToBeBetter",
    ],
}

# =============================================================================
# DEFAULT YOUTUBE CHANNELS - Example channels (customize for your interests)
# =============================================================================

DEFAULT_YOUTUBE_CHANNELS = {
    # Tech & Programming
    "UC8butISFwT-Wl7EV0hUK0BQ": "freeCodeCamp",
    "UCvjgXvBlHQA9_0IIrKCa8Nw": "Fireship",
    "UC-8QAzbLcRglXeN_MY9blyw": "Ben Awad",

    # AI & Tech News
    "UCWN3xxRkmTPmbKwht9FuE5A": "Siraj Raval",
    "UCbmNph6atAoGfqLoCL_duAg": "Sam Witteveen",
}

# =============================================================================
# DEFAULT KEYWORDS - Actionable, specific signals for content discovery
# =============================================================================
# Guidelines for effective keywords:
# - Prefer phrases over single words (more specific context)
# - Include intent indicators (asking, sharing, comparing)
# - Avoid generic terms that match too broadly

DEFAULT_KEYWORDS = {
    # === High-Value Signals (1.5 weight) ===
    "success_signals": [
        # Specific achievement patterns
        "finally figured out",
        "my strategy for",
        "case study",
        "increased by",
        "grew from",
        "results after",
        "what worked for me",
        "breakthrough moment",
        "game changer",
        "highly recommend",
        "success story",
        "turned around",
        # Specific metrics
        "traffic increased",
        "revenue grew",
        "conversion rate",
        "ranked for",
    ],
    "pain_points": [
        # Problem indicators
        "struggling with",
        "frustrated by",
        "can't figure out",
        "doesn't work anymore",
        "stopped working",
        "any alternatives to",
        "looking for replacement",
        "need help with",
        "what am I doing wrong",
        "hit a wall",
        "wasted time on",
        "disappointed with",
        # Specific problem contexts
        "traffic dropped",
        "rankings fell",
        "not getting results",
        "algorithm update",
    ],

    # === Core Tool Categories (1.2-1.3 weight) ===
    "tool_mentions": [
        # Comparison patterns
        "switched from",
        "moved to",
        "better than",
        "compared to",
        "vs",
        "alternative to",
        # Tool discovery patterns
        "started using",
        "been using",
        "recommend for",
        "best tool for",
        "favorite tool",
        # Named tools (competitors to monitor)
        "Ahrefs",
        "Semrush",
        "Moz",
        "Surfer SEO",
        "Clearscope",
        "Frase",
        "Jasper",
        "Copy.ai",
    ],
    "keyword_research": [
        # Research activities
        "keyword research",
        "finding keywords",
        "keyword difficulty",
        "search volume",
        "long-tail keywords",
        "keyword gap",
        "competitor keywords",
        "keyword clustering",
        # Intent patterns
        "how to find keywords",
        "best keywords for",
        "keyword strategy",
    ],
    "content_generation": [
        # AI content patterns
        "AI content",
        "AI writing",
        "content at scale",
        "automated content",
        "AI detection",
        "human-like content",
        "content optimization",
        "content brief",
        # Workflow patterns
        "content workflow",
        "content calendar",
        "batch content",
    ],
    "monetization": [
        # Revenue patterns
        "affiliate income",
        "display ads",
        "AdSense revenue",
        "Mediavine",
        "AdThrive",
        "sponsored content",
        "monetization strategy",
        # Specific metrics
        "RPM",
        "EPMV",
        "affiliate commission",
        "passive income site",
        "niche site income",
    ],
    "ai_visibility": [
        # AI search patterns
        "AI search",
        "ChatGPT",
        "Perplexity",
        "AI answer",
        "AI overview",
        "AI citation",
        "featured in AI",
        "optimizing for AI",
        "GEO",
        "generative engine optimization",
        "AI SEO",
        "LLM optimization",
    ],
    "competition": [
        # Competitive analysis
        "competitor analysis",
        "competitor research",
        "competitive edge",
        "outrank competitors",
        "competitor backlinks",
        "SERP analysis",
        "ranking factors",
        "domain authority",
        "topical authority",
    ],

    # === Supporting Categories (1.1-1.2 weight) ===
    "techniques": [
        # Specific tactics
        "link building",
        "guest posting",
        "broken link",
        "skyscraper technique",
        "content hub",
        "pillar page",
        "internal linking",
        "schema markup",
        "technical SEO",
        "site audit",
        "crawl budget",
    ],
    "image_generation": [
        "AI images",
        "image optimization",
        "alt text",
        "image SEO",
        "Midjourney",
        "DALL-E",
        "Stable Diffusion",
        "stock photos",
    ],
    "ecommerce": [
        "product pages",
        "category SEO",
        "ecommerce SEO",
        "product descriptions",
        "Amazon SEO",
        "Shopify SEO",
        "conversion optimization",
    ],
    "local_seo": [
        "local SEO",
        "Google Business",
        "local pack",
        "NAP consistency",
        "local citations",
        "local keywords",
        "near me",
        "service area",
    ],

    # === Trend/News Signals (1.0 weight) ===
    "trends": [
        "just launched",
        "new feature",
        "beta access",
        "early adopter",
        "announcement",
        "update released",
        "major change",
        "industry news",
        "Google update",
        "algorithm change",
    ],
}
