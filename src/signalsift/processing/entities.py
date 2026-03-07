"""Named Entity Recognition for SignalSift.

This module extracts structured entities from content using spaCy NER,
including tool mentions, monetary values, websites, and organizations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from signalsift.utils.logging import get_logger

if TYPE_CHECKING:
    from spacy.language import Language
    from spacy.tokens import Doc

logger = get_logger(__name__)


@dataclass
class ToolMention:
    """A mention of a competitor or SEO tool."""

    tool: str
    context: str  # Surrounding text for sentiment inference
    position: int  # Character position in text
    sentiment_hint: str | None = (
        None  # "positive", "negative", "neutral", "switching_from", "switching_to"
    )


@dataclass
class MoneyMention:
    """A monetary value mentioned in content."""

    amount: float
    currency: str
    period: str | None  # "monthly", "yearly", "one-time", None
    context: str
    raw_text: str


@dataclass
class WebsiteMention:
    """A website or domain mentioned in content."""

    domain: str
    context: str
    position: int


@dataclass
class EntityExtractionResult:
    """Complete entity extraction results for a piece of content."""

    tools: list[ToolMention] = field(default_factory=list)
    money: list[MoneyMention] = field(default_factory=list)
    websites: list[WebsiteMention] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    people: list[str] = field(default_factory=list)


# Known SEO tools for enhanced detection
KNOWN_TOOLS: dict[str, dict[str, str]] = {
    # All-in-one SEO platforms
    "ahrefs": {"category": "backlink", "tier": "enterprise"},
    "semrush": {"category": "all-in-one", "tier": "enterprise"},
    "moz": {"category": "all-in-one", "tier": "enterprise"},
    "moz pro": {"category": "all-in-one", "tier": "enterprise"},
    "se ranking": {"category": "all-in-one", "tier": "mid"},
    "serpstat": {"category": "all-in-one", "tier": "mid"},
    "ubersuggest": {"category": "all-in-one", "tier": "budget"},
    "mangools": {"category": "keyword", "tier": "budget"},
    "kwfinder": {"category": "keyword", "tier": "budget"},
    # Content optimization
    "surfer": {"category": "content", "tier": "mid"},
    "surfer seo": {"category": "content", "tier": "mid"},
    "clearscope": {"category": "content", "tier": "enterprise"},
    "marketmuse": {"category": "content", "tier": "enterprise"},
    "frase": {"category": "content", "tier": "mid"},
    "neuronwriter": {"category": "content", "tier": "budget"},
    # Technical SEO
    "screaming frog": {"category": "technical", "tier": "mid"},
    "sitebulb": {"category": "technical", "tier": "mid"},
    "deepcrawl": {"category": "technical", "tier": "enterprise"},
    "botify": {"category": "technical", "tier": "enterprise"},
    # AI content tools
    "jasper": {"category": "ai_content", "tier": "mid"},
    "copy.ai": {"category": "ai_content", "tier": "mid"},
    "content at scale": {"category": "ai_content", "tier": "mid"},
    "koala ai": {"category": "ai_content", "tier": "budget"},
    "writesonic": {"category": "ai_content", "tier": "mid"},
    "article forge": {"category": "ai_content", "tier": "mid"},
    "zimmwriter": {"category": "ai_content", "tier": "budget"},
    "byword": {"category": "ai_content", "tier": "mid"},
    # Link building
    "pitchbox": {"category": "outreach", "tier": "enterprise"},
    "buzzstream": {"category": "outreach", "tier": "mid"},
    "hunter.io": {"category": "outreach", "tier": "mid"},
    "respona": {"category": "outreach", "tier": "mid"},
    # Rank tracking
    "accuranker": {"category": "rank_tracking", "tier": "mid"},
    "wincher": {"category": "rank_tracking", "tier": "budget"},
    "serprobot": {"category": "rank_tracking", "tier": "budget"},
    # Other tools
    "spyfu": {"category": "competitor", "tier": "mid"},
    "similarweb": {"category": "competitor", "tier": "enterprise"},
    "buzzsumo": {"category": "content_research", "tier": "mid"},
    "answerthepublic": {"category": "keyword", "tier": "budget"},
    "originality.ai": {"category": "ai_detection", "tier": "budget"},
    "gptzero": {"category": "ai_detection", "tier": "budget"},
}

# Patterns for sentiment context detection
SWITCHING_FROM_PATTERNS = [
    r"switched?\s+from",
    r"moved?\s+away\s+from",
    r"left",
    r"abandoned",
    r"gave\s+up\s+on",
    r"stopped\s+using",
    r"cancelled",
    r"canceled",
]

SWITCHING_TO_PATTERNS = [
    r"switched?\s+to",
    r"moved?\s+to",
    r"started\s+using",
    r"now\s+using",
    r"trying\s+out",
    r"signed\s+up\s+for",
]

POSITIVE_PATTERNS = [
    r"love",
    r"amazing",
    r"great",
    r"best",
    r"recommend",
    r"worth\s+it",
    r"game\s*changer",
    r"helped",
    r"increased",
]

NEGATIVE_PATTERNS = [
    r"hate",
    r"terrible",
    r"worst",
    r"expensive",
    r"overpriced",
    r"buggy",
    r"broken",
    r"waste",
    r"disappointed",
    r"frustrat",
]

# Domain extraction pattern
DOMAIN_PATTERN = re.compile(
    r"\b(?:https?://)?(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*(?:\.[a-zA-Z0-9][-a-zA-Z0-9]*)+)\b",
    re.IGNORECASE,
)

# Money patterns
MONEY_PATTERNS = [
    # $X,XXX or $X.XX format
    (
        re.compile(
            r"\$\s*([\d,]+(?:\.\d{2})?)\s*(?:k|K)?(?:/(?:mo|month|yr|year|day))?", re.IGNORECASE
        ),
        "USD",
    ),
    # Xk/month format
    (
        re.compile(
            r"([\d.]+)\s*(?:k|K)\s*(?:/|per\s*)?(mo|month|monthly|yr|year|yearly)?", re.IGNORECASE
        ),
        "USD",
    ),
    # EUR format
    (re.compile(r"([\d,]+(?:\.\d{2})?)\s*(?:€|EUR|euros?)", re.IGNORECASE), "EUR"),
    # GBP format
    (re.compile(r"£\s*([\d,]+(?:\.\d{2})?)", re.IGNORECASE), "GBP"),
]

PERIOD_KEYWORDS = {
    "mo": "monthly",
    "month": "monthly",
    "monthly": "monthly",
    "/m": "monthly",
    "yr": "yearly",
    "year": "yearly",
    "yearly": "yearly",
    "annual": "yearly",
    "/y": "yearly",
    "day": "daily",
    "daily": "daily",
    "/d": "daily",
}


class EntityExtractor:
    """Extract named entities from content using spaCy and custom patterns."""

    def __init__(self, model_name: str = "en_core_web_md") -> None:
        """
        Initialize the entity extractor.

        Args:
            model_name: spaCy model to use for NER.
        """
        self._nlp: Language | None = None
        self._model_name = model_name
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        """Load the spaCy model."""
        try:
            import spacy

            self._nlp = spacy.load(self._model_name)
            self._available = True
            logger.debug(f"Entity extractor loaded spaCy model: {self._model_name}")
        except ImportError:
            logger.warning("spaCy not installed - entity extraction limited")
            self._available = False
        except OSError:
            logger.warning(
                f"spaCy model '{self._model_name}' not found - entity extraction limited"
            )
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check if NER is available."""
        return self._available

    def extract(self, text: str) -> EntityExtractionResult:
        """
        Extract all entity types from text.

        Args:
            text: The text to analyze.

        Returns:
            EntityExtractionResult with all extracted entities.
        """
        result = EntityExtractionResult()

        # Extract tools (custom pattern matching - works without spaCy)
        result.tools = self._extract_tools(text)

        # Extract money mentions (regex-based)
        result.money = self._extract_money(text)

        # Extract websites (regex-based)
        result.websites = self._extract_websites(text)

        # Extract organizations and people (requires spaCy)
        if self._available and self._nlp:
            doc = self._nlp(text)
            result.organizations = self._extract_organizations(doc)
            result.people = self._extract_people(doc)

        return result

    def _extract_tools(self, text: str) -> list[ToolMention]:
        """Extract mentions of SEO tools."""
        tools: list[ToolMention] = []
        text_lower = text.lower()
        seen_positions: set[int] = set()

        for tool_name in KNOWN_TOOLS:
            # Find all occurrences
            start = 0
            while True:
                pos = text_lower.find(tool_name, start)
                if pos == -1:
                    break

                # Avoid overlapping detections
                if any(abs(pos - seen_pos) < len(tool_name) for seen_pos in seen_positions):
                    start = pos + 1
                    continue

                seen_positions.add(pos)

                # Get context (50 chars before and after)
                context_start = max(0, pos - 50)
                context_end = min(len(text), pos + len(tool_name) + 50)
                context = text[context_start:context_end]

                # Determine sentiment hint from context
                sentiment_hint = self._detect_tool_sentiment(context.lower())

                tools.append(
                    ToolMention(
                        tool=tool_name,
                        context=context,
                        position=pos,
                        sentiment_hint=sentiment_hint,
                    )
                )
                start = pos + 1

        return tools

    def _detect_tool_sentiment(self, context: str) -> str | None:
        """Detect sentiment hint from tool mention context."""
        # Check switching patterns first
        for pattern in SWITCHING_FROM_PATTERNS:
            if re.search(pattern, context):
                return "switching_from"

        for pattern in SWITCHING_TO_PATTERNS:
            if re.search(pattern, context):
                return "switching_to"

        # Check positive/negative patterns
        positive_count = sum(1 for p in POSITIVE_PATTERNS if re.search(p, context))
        negative_count = sum(1 for p in NEGATIVE_PATTERNS if re.search(p, context))

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        elif positive_count == negative_count and positive_count > 0:
            return "mixed"

        return "neutral"

    def _extract_money(self, text: str) -> list[MoneyMention]:
        """Extract monetary values from text."""
        money_mentions: list[MoneyMention] = []
        seen_positions: set[int] = set()

        for pattern, currency in MONEY_PATTERNS:
            for match in pattern.finditer(text):
                # Avoid duplicates
                if match.start() in seen_positions:
                    continue
                seen_positions.add(match.start())

                raw_text = match.group(0)
                amount_str = match.group(1).replace(",", "")

                try:
                    amount = float(amount_str)

                    # Handle 'k' multiplier
                    if "k" in raw_text.lower() and amount < 1000:
                        amount *= 1000

                    # Detect period
                    period = None
                    text_lower = raw_text.lower()
                    for key, value in PERIOD_KEYWORDS.items():
                        if key in text_lower:
                            period = value
                            break

                    # Also check surrounding context for period
                    if period is None:
                        context_end = min(len(text), match.end() + 20)
                        after_text = text[match.end() : context_end].lower()
                        for key, value in PERIOD_KEYWORDS.items():
                            if key in after_text:
                                period = value
                                break

                    # Get context
                    context_start = max(0, match.start() - 30)
                    context_end = min(len(text), match.end() + 30)
                    context = text[context_start:context_end]

                    money_mentions.append(
                        MoneyMention(
                            amount=amount,
                            currency=currency,
                            period=period,
                            context=context,
                            raw_text=raw_text,
                        )
                    )
                except ValueError:
                    continue

        return money_mentions

    def _extract_websites(self, text: str) -> list[WebsiteMention]:
        """Extract website/domain mentions from text."""
        websites: list[WebsiteMention] = []
        seen_domains: set[str] = set()

        # Common domains to exclude
        excluded = {
            "reddit.com",
            "youtube.com",
            "twitter.com",
            "x.com",
            "facebook.com",
            "instagram.com",
            "tiktok.com",
            "linkedin.com",
            "google.com",
            "github.com",
            "imgur.com",
            "i.redd.it",
        }

        for match in DOMAIN_PATTERN.finditer(text):
            domain = match.group(1).lower()

            # Skip common/social domains
            if domain in excluded or any(domain.endswith(f".{ex}") for ex in excluded):
                continue

            # Skip if already seen
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            # Get context
            context_start = max(0, match.start() - 30)
            context_end = min(len(text), match.end() + 30)
            context = text[context_start:context_end]

            websites.append(
                WebsiteMention(
                    domain=domain,
                    context=context,
                    position=match.start(),
                )
            )

        return websites

    def _extract_organizations(self, doc: Doc) -> list[str]:
        """Extract organization names from spaCy doc."""
        orgs: list[str] = []
        seen: set[str] = set()

        for ent in doc.ents:
            if ent.label_ == "ORG":
                org_name = ent.text.strip()
                org_lower = org_name.lower()
                if org_lower not in seen and len(org_name) > 1:
                    seen.add(org_lower)
                    orgs.append(org_name)

        return orgs

    def _extract_people(self, doc: Doc) -> list[str]:
        """Extract person names from spaCy doc."""
        people: list[str] = []
        seen: set[str] = set()

        for ent in doc.ents:
            if ent.label_ == "PERSON":
                person_name = ent.text.strip()
                person_lower = person_name.lower()
                if person_lower not in seen and len(person_name) > 1:
                    seen.add(person_lower)
                    people.append(person_name)

        return people

    def get_tool_info(self, tool_name: str) -> dict[str, str] | None:
        """Get metadata about a known tool."""
        return KNOWN_TOOLS.get(tool_name.lower())


# Module-level instance
_default_extractor: EntityExtractor | None = None


def get_extractor() -> EntityExtractor:
    """Get the default entity extractor instance."""
    global _default_extractor
    if _default_extractor is None:
        _default_extractor = EntityExtractor()
    return _default_extractor


def extract_entities(text: str) -> EntityExtractionResult:
    """Convenience function to extract entities from text."""
    return get_extractor().extract(text)
