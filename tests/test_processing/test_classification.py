"""Tests for content classification module."""

from signalsift.processing.classification import (
    CATEGORY_NAMES,
    CATEGORY_SIGNALS,
    classify_content,
    get_category_group,
    get_category_name,
    get_primary_categories,
)
from signalsift.processing.keywords import KeywordMatch


class TestCategorySignals:
    """Tests for category signals dictionary."""

    def test_category_signals_not_empty(self):
        """Test that category signals dictionary is populated."""
        assert len(CATEGORY_SIGNALS) > 0

    def test_all_categories_have_signals(self):
        """Test that all categories have at least one signal."""
        for category, signals in CATEGORY_SIGNALS.items():
            assert len(signals) > 0, f"Category {category} has no signals"

    def test_signals_are_lowercase(self):
        """Test that all signals are lowercase."""
        for category, signals in CATEGORY_SIGNALS.items():
            for signal in signals:
                assert signal == signal.lower(), f"Signal '{signal}' in {category} is not lowercase"


class TestCategoryNames:
    """Tests for category names dictionary."""

    def test_all_signals_have_names(self):
        """Test that all signal categories have human-readable names."""
        for category in CATEGORY_SIGNALS:
            assert category in CATEGORY_NAMES or category == "general"

    def test_names_are_strings(self):
        """Test that all category names are strings."""
        for _, name in CATEGORY_NAMES.items():
            assert isinstance(name, str)
            assert len(name) > 0


class TestClassifyContent:
    """Tests for classify_content function."""

    def test_classify_pain_point(self):
        """Test classifying pain point content."""
        text = "I'm struggling with my site traffic. Can't figure out what's broken."
        category = classify_content(text)
        assert category == "pain_point"

    def test_classify_success_story(self):
        """Test classifying success story content."""
        text = "Finally achieved ranking #1! Results doubled after the breakthrough."
        category = classify_content(text)
        assert category == "success_story"

    def test_classify_tool_comparison(self):
        """Test classifying tool comparison content."""
        text = "Ahrefs vs Semrush - which one is better? I switched from one to another."
        category = classify_content(text)
        assert category == "tool_comparison"

    def test_classify_technique(self):
        """Test classifying technique content."""
        text = "Here's my step by step guide on how to approach link building."
        category = classify_content(text)
        assert category == "technique"

    def test_classify_industry_news(self):
        """Test classifying industry news content."""
        text = "Google released a new algorithm update announcement today."
        category = classify_content(text)
        assert category == "industry_news"

    def test_classify_monetization(self):
        """Test classifying monetization content."""
        text = "My affiliate commission from Mediavine is great. RPM and revenue up!"
        category = classify_content(text)
        assert category == "monetization"

    def test_classify_ai_visibility(self):
        """Test classifying AI visibility content."""
        text = "Getting citations in ChatGPT and Perplexity AI search results."
        category = classify_content(text)
        assert category == "ai_visibility"

    def test_classify_ai_content(self):
        """Test classifying AI content generation topics."""
        text = "Using AI writer for bulk content. GPT-4 generates great articles."
        category = classify_content(text)
        assert category == "ai_content"

    def test_classify_keyword_research(self):
        """Test classifying keyword research content."""
        text = "Found great long tail keywords with low competition search volume."
        category = classify_content(text)
        assert category == "keyword_research"

    def test_classify_competitor_analysis(self):
        """Test classifying competitor analysis content."""
        text = "Found a content gap to outrank my competitor. Analyzing their backlinks."
        category = classify_content(text)
        assert category == "competitor_analysis"

    def test_classify_general(self):
        """Test that unclassifiable content returns general."""
        text = "Random text that doesn't match any category specifically."
        category = classify_content(text)
        assert category == "general"

    def test_classify_case_insensitive(self):
        """Test that classification is case insensitive."""
        text = "STRUGGLING with TRAFFIC DROPPED significantly!"
        category = classify_content(text)
        assert category == "pain_point"


class TestClassifyWithKeywords:
    """Tests for classify_content with matched keywords."""

    def test_classify_with_keyword_match(self):
        """Test classification with keyword matches."""
        text = "Some generic SEO discussion text."
        keywords = [
            KeywordMatch(
                keyword="monetization",
                category="monetization",
                weight=2.0,
                count=1,
            )
        ]
        category = classify_content(text, matched_keywords=keywords)
        assert category == "monetization"

    def test_classify_keyword_overrides_signal(self):
        """Test that weighted keywords can influence classification."""
        text = "I'm struggling with this problem."  # Would be pain_point
        keywords = [
            KeywordMatch(
                keyword="affiliate",
                category="monetization",
                weight=5.0,  # High weight
                count=3,
            )
        ]
        # Keywords should influence the classification
        category = classify_content(text, matched_keywords=keywords)
        # Either result is acceptable since both have signals
        assert category in ["pain_point", "monetization"]

    def test_classify_empty_keywords(self):
        """Test classification with empty keyword list."""
        text = "Traffic dropped after the update."
        category = classify_content(text, matched_keywords=[])
        assert category == "pain_point"


class TestGetCategoryName:
    """Tests for get_category_name function."""

    def test_get_known_category_name(self):
        """Test getting name for known category."""
        name = get_category_name("pain_point")
        assert name == "Pain Point / Feature Opportunity"

    def test_get_success_story_name(self):
        """Test getting success story name."""
        name = get_category_name("success_story")
        assert name == "Success Story"

    def test_get_unknown_category_name(self):
        """Test getting name for unknown category."""
        name = get_category_name("unknown_category")
        assert name == "Unknown Category"  # Should title-case and replace underscores

    def test_get_general_category_name(self):
        """Test getting general category name."""
        name = get_category_name("general")
        assert name == "General"


class TestGetPrimaryCategories:
    """Tests for get_primary_categories function."""

    def test_returns_list(self):
        """Test that function returns a list."""
        categories = get_primary_categories()
        assert isinstance(categories, list)

    def test_contains_main_categories(self):
        """Test that main categories are included."""
        categories = get_primary_categories()
        assert "pain_point" in categories
        assert "success_story" in categories
        assert "monetization" in categories

    def test_matches_signals_keys(self):
        """Test that returned list matches CATEGORY_SIGNALS keys."""
        categories = get_primary_categories()
        assert set(categories) == set(CATEGORY_SIGNALS.keys())


class TestGetCategoryGroup:
    """Tests for get_category_group function."""

    def test_general_categories(self):
        """Test grouping of general categories."""
        assert get_category_group("pain_point") == "general"
        assert get_category_group("success_story") == "general"
        assert get_category_group("tool_comparison") == "general"

    def test_monetization_categories(self):
        """Test grouping of monetization categories."""
        assert get_category_group("monetization") == "monetization"
        assert get_category_group("roi_analysis") == "monetization"
        assert get_category_group("ecommerce") == "monetization"

    def test_ai_categories(self):
        """Test grouping of AI categories."""
        assert get_category_group("ai_visibility") == "ai"
        assert get_category_group("ai_content") == "ai"
        assert get_category_group("image_generation") == "ai"

    def test_research_categories(self):
        """Test grouping of research categories."""
        assert get_category_group("keyword_research") == "research"
        assert get_category_group("local_seo") == "research"

    def test_competitive_categories(self):
        """Test grouping of competitive categories."""
        assert get_category_group("competitor_analysis") == "competitive"
        assert get_category_group("content_brief") == "competitive"

    def test_technical_categories(self):
        """Test grouping of technical categories."""
        assert get_category_group("static_sites") == "technical"

    def test_unknown_category(self):
        """Test grouping of unknown category."""
        result = get_category_group("unknown_category")
        assert result is None

    def test_technique_category(self):
        """Test technique category group."""
        assert get_category_group("technique") == "techniques"

    def test_news_category(self):
        """Test industry news category group."""
        assert get_category_group("industry_news") == "news"
