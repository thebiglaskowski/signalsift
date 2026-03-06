"""Tests for entity extraction module."""

from unittest.mock import patch

import pytest

from signalsift.processing.entities import (
    KNOWN_TOOLS,
    EntityExtractionResult,
    EntityExtractor,
    MoneyMention,
    ToolMention,
    WebsiteMention,
    extract_entities,
    get_extractor,
)


class TestDataclasses:
    """Tests for entity dataclasses."""

    def test_tool_mention_creation(self):
        """Test creating a ToolMention instance."""
        mention = ToolMention(
            tool="ahrefs",
            context="I love using ahrefs for backlinks",
            position=15,
            sentiment_hint="positive",
        )

        assert mention.tool == "ahrefs"
        assert mention.context == "I love using ahrefs for backlinks"
        assert mention.position == 15
        assert mention.sentiment_hint == "positive"

    def test_tool_mention_default_sentiment(self):
        """Test ToolMention with default sentiment."""
        mention = ToolMention(tool="semrush", context="context", position=0)
        assert mention.sentiment_hint is None

    def test_money_mention_creation(self):
        """Test creating a MoneyMention instance."""
        mention = MoneyMention(
            amount=5000.0,
            currency="USD",
            period="monthly",
            context="making $5,000 per month",
            raw_text="$5,000",
        )

        assert mention.amount == 5000.0
        assert mention.currency == "USD"
        assert mention.period == "monthly"

    def test_website_mention_creation(self):
        """Test creating a WebsiteMention instance."""
        mention = WebsiteMention(
            domain="example.com",
            context="check out example.com for more",
            position=10,
        )

        assert mention.domain == "example.com"
        assert mention.position == 10

    def test_entity_extraction_result_defaults(self):
        """Test EntityExtractionResult with default values."""
        result = EntityExtractionResult()

        assert result.tools == []
        assert result.money == []
        assert result.websites == []
        assert result.organizations == []
        assert result.people == []


class TestEntityExtractorInit:
    """Tests for EntityExtractor initialization."""

    def test_init_without_spacy(self):
        """Test initialization when spaCy is not available."""
        with patch.object(EntityExtractor, "_load_model") as mock_load:
            mock_load.return_value = None
            EntityExtractor()
            mock_load.assert_called_once()

    def test_is_available_property(self):
        """Test is_available property."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._available = True

        assert extractor.is_available is True

        extractor._available = False
        assert extractor.is_available is False


class TestToolExtraction:
    """Tests for tool extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor without spaCy."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False
        return extractor

    def test_extract_single_tool(self, extractor):
        """Test extracting a single tool mention."""
        text = "I've been using Ahrefs for link building."
        tools = extractor._extract_tools(text)

        assert len(tools) == 1
        assert tools[0].tool == "ahrefs"

    def test_extract_multiple_tools(self, extractor):
        """Test extracting multiple tool mentions."""
        text = "Switched from Semrush to Ahrefs and also tried Moz."
        tools = extractor._extract_tools(text)

        tool_names = {t.tool for t in tools}
        assert "semrush" in tool_names
        assert "ahrefs" in tool_names
        assert "moz" in tool_names

    def test_extract_tool_multiple_occurrences(self, extractor):
        """Test extracting tool mentioned multiple times."""
        text = "Ahrefs is great. I use Ahrefs daily. Best tool is Ahrefs."
        tools = extractor._extract_tools(text)

        # Should find all occurrences
        assert len(tools) >= 2
        assert all(t.tool == "ahrefs" for t in tools)

    def test_extract_tool_with_spaces(self, extractor):
        """Test extracting tools with spaces in name."""
        text = "Screaming Frog is essential for technical SEO audits."
        tools = extractor._extract_tools(text)

        assert len(tools) == 1
        assert tools[0].tool == "screaming frog"

    def test_extract_no_tools(self, extractor):
        """Test when no tools are mentioned."""
        text = "General discussion about SEO strategies."
        tools = extractor._extract_tools(text)

        assert tools == []


class TestToolSentimentDetection:
    """Tests for tool sentiment detection."""

    @pytest.fixture
    def extractor(self):
        """Create extractor."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False
        return extractor

    def test_detect_switching_from(self, extractor):
        """Test detecting 'switching from' sentiment."""
        context = "I switched from ahrefs to something else"
        result = extractor._detect_tool_sentiment(context)
        assert result == "switching_from"

    def test_detect_switching_to(self, extractor):
        """Test detecting 'switching to' sentiment."""
        context = "I switched to semrush and it's better"
        result = extractor._detect_tool_sentiment(context)
        assert result == "switching_to"

    def test_detect_positive(self, extractor):
        """Test detecting positive sentiment."""
        context = "I love this tool, it's amazing and helped a lot"
        result = extractor._detect_tool_sentiment(context)
        assert result == "positive"

    def test_detect_negative(self, extractor):
        """Test detecting negative sentiment."""
        context = "I hate this tool, it's terrible and buggy"
        result = extractor._detect_tool_sentiment(context)
        assert result == "negative"

    def test_detect_neutral(self, extractor):
        """Test detecting neutral sentiment."""
        context = "I use this tool for my work"
        result = extractor._detect_tool_sentiment(context)
        assert result == "neutral"

    def test_detect_mixed(self, extractor):
        """Test detecting mixed sentiment."""
        context = "I love some features but hate the price"
        result = extractor._detect_tool_sentiment(context)
        assert result == "mixed"


class TestMoneyExtraction:
    """Tests for money extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False
        return extractor

    def test_extract_dollar_amount(self, extractor):
        """Test extracting dollar amounts."""
        text = "Made $5,000 from my site last month."
        money = extractor._extract_money(text)

        assert len(money) == 1
        assert money[0].amount == 5000.0
        assert money[0].currency == "USD"

    def test_extract_k_notation(self, extractor):
        """Test extracting K notation amounts."""
        text = "Earning 10k per month from affiliate."
        money = extractor._extract_money(text)

        assert len(money) == 1
        assert money[0].amount == 10000.0

    def test_extract_with_period(self, extractor):
        """Test extracting amount with period."""
        text = "Revenue of $2,000/month consistently."
        money = extractor._extract_money(text)

        assert len(money) >= 1
        # At least one should have monthly period
        periods = [m.period for m in money]
        assert "monthly" in periods or any(m.period for m in money)

    def test_extract_euro(self, extractor):
        """Test extracting Euro amounts."""
        text = "Costs 500 EUR for the yearly plan."
        money = extractor._extract_money(text)

        assert len(money) == 1
        assert money[0].currency == "EUR"

    def test_extract_gbp(self, extractor):
        """Test extracting GBP amounts."""
        text = "Price is £299 per month."
        money = extractor._extract_money(text)

        assert len(money) == 1
        assert money[0].currency == "GBP"

    def test_extract_no_money(self, extractor):
        """Test when no money is mentioned."""
        text = "Traffic increased significantly."
        money = extractor._extract_money(text)

        assert money == []


class TestWebsiteExtraction:
    """Tests for website extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False
        return extractor

    def test_extract_domain(self, extractor):
        """Test extracting domain names."""
        text = "Check out example.com for more info."
        websites = extractor._extract_websites(text)

        assert len(websites) == 1
        assert websites[0].domain == "example.com"

    def test_extract_full_url(self, extractor):
        """Test extracting from full URL."""
        text = "Visit https://www.mysite.io for details."
        websites = extractor._extract_websites(text)

        assert len(websites) == 1
        assert websites[0].domain == "mysite.io"

    def test_excludes_social_domains(self, extractor):
        """Test that social domains are excluded."""
        text = "Follow me on twitter.com and youtube.com"
        websites = extractor._extract_websites(text)

        assert len(websites) == 0

    def test_excludes_reddit(self, extractor):
        """Test that reddit.com is excluded."""
        text = "Posted on reddit.com/r/SEO"
        websites = extractor._extract_websites(text)

        assert len(websites) == 0

    def test_multiple_domains(self, extractor):
        """Test extracting multiple domains."""
        text = "Compare mysite.com with othersite.org"
        websites = extractor._extract_websites(text)

        domains = {w.domain for w in websites}
        assert "mysite.com" in domains
        assert "othersite.org" in domains


class TestEntityExtractorExtract:
    """Tests for the main extract method."""

    @pytest.fixture
    def extractor(self):
        """Create extractor without spaCy."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False
        return extractor

    def test_extract_returns_result(self, extractor):
        """Test that extract returns EntityExtractionResult."""
        result = extractor.extract("Some text here.")
        assert isinstance(result, EntityExtractionResult)

    def test_extract_comprehensive(self, extractor):
        """Test comprehensive extraction."""
        text = """
        Switched from Semrush to Ahrefs and made $5,000 last month.
        Check out mysite.com for my case study.
        """
        result = extractor.extract(text)

        assert len(result.tools) >= 2
        assert len(result.money) >= 1
        assert len(result.websites) >= 1


class TestKnownTools:
    """Tests for KNOWN_TOOLS dictionary."""

    def test_known_tools_structure(self):
        """Test that KNOWN_TOOLS has correct structure."""
        for tool_name, info in KNOWN_TOOLS.items():
            assert "category" in info
            assert "tier" in info
            assert isinstance(tool_name, str)

    def test_get_tool_info(self):
        """Test getting tool info."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False

        info = extractor.get_tool_info("ahrefs")
        assert info is not None
        assert info["category"] == "backlink"
        assert info["tier"] == "enterprise"

    def test_get_tool_info_unknown(self):
        """Test getting info for unknown tool."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False

        info = extractor.get_tool_info("unknown_tool")
        assert info is None

    def test_get_tool_info_case_insensitive(self):
        """Test that tool lookup is case insensitive."""
        extractor = EntityExtractor.__new__(EntityExtractor)
        extractor._nlp = None
        extractor._available = False

        info = extractor.get_tool_info("AHREFS")
        assert info is not None


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_extractor_returns_instance(self):
        """Test that get_extractor returns an EntityExtractor."""
        import signalsift.processing.entities as entities_module

        # Reset module-level instance
        entities_module._default_extractor = None

        extractor = get_extractor()
        assert isinstance(extractor, EntityExtractor)

    def test_get_extractor_caches_instance(self):
        """Test that get_extractor caches the instance."""
        import signalsift.processing.entities as entities_module

        # Reset module-level instance
        entities_module._default_extractor = None

        extractor1 = get_extractor()
        extractor2 = get_extractor()

        assert extractor1 is extractor2

    def test_extract_entities_function(self):
        """Test the extract_entities convenience function."""
        import signalsift.processing.entities as entities_module

        # Reset module-level instance
        entities_module._default_extractor = None

        result = extract_entities("Testing with Ahrefs for $500.")

        assert isinstance(result, EntityExtractionResult)
        assert len(result.tools) >= 1
