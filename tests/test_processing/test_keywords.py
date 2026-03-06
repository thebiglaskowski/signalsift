"""Tests for keyword matching utilities."""

from unittest.mock import patch

import pytest

from signalsift.database.models import Keyword
from signalsift.processing.keywords import KeywordMatch, KeywordMatcher


class TestKeywordMatch:
    """Tests for KeywordMatch dataclass."""

    def test_basic_match(self):
        """Test creating a basic keyword match."""
        match = KeywordMatch(
            keyword="seo",
            category="marketing",
            weight=1.0,
            count=3,
        )
        assert match.keyword == "seo"
        assert match.category == "marketing"
        assert match.weight == 1.0
        assert match.count == 3
        assert match.is_semantic is False
        assert match.original_keyword is None

    def test_semantic_match(self):
        """Test creating a semantic match."""
        match = KeywordMatch(
            keyword="optimization",
            category="marketing",
            weight=0.8,
            count=1,
            is_semantic=True,
            original_keyword="seo",
        )
        assert match.is_semantic is True
        assert match.original_keyword == "seo"


class TestKeywordMatcherInit:
    """Tests for KeywordMatcher initialization."""

    def test_init_without_semantic(self):
        """Test initializing without semantic expansion."""
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=[]):
            matcher = KeywordMatcher(enable_semantic=False)

            assert matcher._enable_semantic is False
            assert matcher.semantic_enabled is False

    def test_init_with_semantic_unavailable(self):
        """Test initializing when semantic module not available."""
        with (
            patch("signalsift.processing.keywords.get_all_keywords", return_value=[]),
            patch.object(KeywordMatcher, "_init_semantic") as mock_init,
        ):
            KeywordMatcher(enable_semantic=True)
            mock_init.assert_called_once()


class TestKeywordMatcherBuildPatterns:
    """Tests for pattern building."""

    @pytest.fixture
    def matcher(self):
        """Create matcher with mocked keywords."""
        keywords = [
            Keyword(keyword="seo", category="marketing", weight=1.0),
            Keyword(keyword="content marketing", category="marketing", weight=0.8),
            Keyword(keyword="keyword research", category="keywords", weight=1.0),
        ]
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=keywords):
            m = KeywordMatcher(enable_semantic=False)
            # Force loading keywords
            _ = m.keywords
            return m

    def test_patterns_created(self, matcher):
        """Test that patterns are created for all keywords."""
        assert "seo" in matcher._patterns
        assert "content marketing" in matcher._patterns
        assert "keyword research" in matcher._patterns

    def test_patterns_are_case_insensitive(self, matcher):
        """Test that patterns are case insensitive."""
        pattern = matcher._patterns["seo"]
        assert pattern.search("SEO") is not None
        assert pattern.search("seo") is not None
        assert pattern.search("Seo") is not None


class TestKeywordMatcherFindMatches:
    """Tests for find_matches method."""

    @pytest.fixture
    def matcher(self):
        """Create matcher with test keywords."""
        keywords = [
            Keyword(keyword="seo", category="marketing", weight=1.0),
            Keyword(keyword="content", category="marketing", weight=0.8),
            Keyword(keyword="backlink", category="links", weight=1.2),
        ]
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=keywords):
            m = KeywordMatcher(enable_semantic=False)
            # Force building patterns by accessing keywords
            _ = m.keywords
            return m

    def test_find_single_match(self, matcher):
        """Test finding a single keyword match."""
        matches = matcher.find_matches("This is about SEO optimization")

        assert len(matches) == 1
        assert matches[0].keyword == "seo"
        assert matches[0].count == 1

    def test_find_multiple_matches(self, matcher):
        """Test finding multiple different keywords."""
        matches = matcher.find_matches("SEO and content marketing with backlink strategy")

        keywords_found = {m.keyword for m in matches}
        assert "seo" in keywords_found
        assert "content" in keywords_found
        assert "backlink" in keywords_found

    def test_count_multiple_occurrences(self, matcher):
        """Test counting multiple occurrences of same keyword."""
        matches = matcher.find_matches("SEO tips for SEO beginners learning SEO")

        seo_match = next(m for m in matches if m.keyword == "seo")
        assert seo_match.count == 3

    def test_no_matches(self, matcher):
        """Test text with no keyword matches."""
        matches = matcher.find_matches("This text has nothing relevant")

        assert len(matches) == 0

    def test_case_insensitive_matching(self, matcher):
        """Test that matching is case insensitive."""
        matches = matcher.find_matches("seo SEO Seo sEo")

        seo_match = next(m for m in matches if m.keyword == "seo")
        assert seo_match.count == 4

    def test_word_boundary_matching(self, matcher):
        """Test that partial words don't match."""
        matches = matcher.find_matches("unseothing and contentious")

        # Should not match "seo" in "unseothing" or "content" in "contentious"
        assert len(matches) == 0


class TestKeywordMatcherRefresh:
    """Tests for refresh method."""

    def test_refresh_clears_cache(self):
        """Test that refresh clears the keyword cache."""
        keywords = [Keyword(keyword="test", category="test", weight=1.0)]
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=keywords):
            matcher = KeywordMatcher(enable_semantic=False)

            # Load keywords
            _ = matcher.keywords
            assert matcher._keywords is not None
            assert len(matcher._patterns) > 0

            # Refresh
            matcher.refresh()
            assert matcher._keywords is None
            assert len(matcher._patterns) == 0


class TestKeywordMatcherGetMatchedKeywords:
    """Tests for get_matched_keywords method."""

    @pytest.fixture
    def matcher(self):
        """Create matcher with test keywords."""
        keywords = [
            Keyword(keyword="seo", category="marketing", weight=1.0),
            Keyword(keyword="content", category="marketing", weight=0.8),
        ]
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=keywords):
            m = KeywordMatcher(enable_semantic=False)
            _ = m.keywords
            return m

    def test_get_matched_keywords_list(self, matcher):
        """Test getting list of matched keyword strings."""
        matches = matcher.find_matches("SEO content tips")
        result = matcher.get_matched_keywords(matches)

        assert isinstance(result, list)
        assert "seo" in result
        assert "content" in result

    def test_get_matched_keywords_empty(self, matcher):
        """Test getting empty list when no matches."""
        matches = []
        result = matcher.get_matched_keywords(matches)

        assert result == []


class TestGetMatcher:
    """Tests for get_matcher function."""

    def test_get_matcher_returns_instance(self):
        """Test that get_matcher returns a KeywordMatcher instance."""
        import signalsift.processing.keywords as keywords_module
        from signalsift.processing.keywords import get_matcher

        # Reset the global matcher
        keywords_module._default_matcher = None

        with patch("signalsift.processing.keywords.get_all_keywords", return_value=[]):
            matcher = get_matcher()
            assert isinstance(matcher, KeywordMatcher)

    def test_get_matcher_caches_instance(self):
        """Test that get_matcher caches the instance."""
        import signalsift.processing.keywords as keywords_module
        from signalsift.processing.keywords import get_matcher

        # Reset the global matcher
        keywords_module._default_matcher = None

        with patch("signalsift.processing.keywords.get_all_keywords", return_value=[]):
            matcher1 = get_matcher()
            matcher2 = get_matcher()

            # Should return same instance
            assert matcher1 is matcher2


class TestKeywordMatcherWithSemanticDisabled:
    """Tests for matcher behavior when semantic is disabled."""

    def test_semantic_patterns_empty(self):
        """Test that semantic patterns are empty when disabled."""
        keywords = [Keyword(keyword="seo", category="marketing", weight=1.0)]
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=keywords):
            matcher = KeywordMatcher(enable_semantic=False)
            _ = matcher.keywords  # Force build

            assert len(matcher._semantic_patterns) == 0

    def test_semantic_enabled_property_false(self):
        """Test semantic_enabled returns False when disabled."""
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=[]):
            matcher = KeywordMatcher(enable_semantic=False)
            assert matcher.semantic_enabled is False


class TestKeywordMatcherWeights:
    """Tests for keyword weight handling."""

    @pytest.fixture
    def matcher(self):
        """Create matcher with weighted keywords."""
        keywords = [
            Keyword(keyword="seo", category="marketing", weight=2.0),
            Keyword(keyword="marketing", category="marketing", weight=1.0),
            Keyword(keyword="tips", category="general", weight=0.5),
        ]
        with patch("signalsift.processing.keywords.get_all_keywords", return_value=keywords):
            m = KeywordMatcher(enable_semantic=False)
            _ = m.keywords
            return m

    def test_weights_preserved(self, matcher):
        """Test that keyword weights are preserved in matches."""
        matches = matcher.find_matches("SEO marketing tips")

        seo_match = next(m for m in matches if m.keyword == "seo")
        marketing_match = next(m for m in matches if m.keyword == "marketing")
        tips_match = next(m for m in matches if m.keyword == "tips")

        assert seo_match.weight == 2.0
        assert marketing_match.weight == 1.0
        assert tips_match.weight == 0.5

    def test_categories_preserved(self, matcher):
        """Test that keyword categories are preserved in matches."""
        matches = matcher.find_matches("SEO tips")

        seo_match = next(m for m in matches if m.keyword == "seo")
        tips_match = next(m for m in matches if m.keyword == "tips")

        assert seo_match.category == "marketing"
        assert tips_match.category == "general"
