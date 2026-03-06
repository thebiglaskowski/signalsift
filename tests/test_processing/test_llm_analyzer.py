"""Tests for LLM analyzer module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from signalsift.processing.llm_analyzer import (
    ContentAnalysis,
    LLMAnalyzer,
    analyze_content,
    get_analyzer,
    is_llm_available,
)


class TestContentAnalysisDataclass:
    """Tests for ContentAnalysis dataclass."""

    def test_content_analysis_creation(self):
        """Test creating a ContentAnalysis instance."""
        analysis = ContentAnalysis(
            summary="This is a test summary.",
            key_insight="Key insight here.",
            feature_suggestion="Add this feature.",
            pain_severity=3,
            takeaway="Main takeaway.",
            strategy_used="Content strategy.",
            monetization_angle="Affiliate opportunity.",
            geo_opportunity="Local SEO focus.",
            keyword_opportunity="Long-tail keywords.",
            content_strategy="Pillar content approach.",
            competitive_angle="Beat competitors with speed.",
            image_opportunity="Add infographics.",
            tech_insight="Improve Core Web Vitals.",
            confidence=0.85,
            relevant_packages=["SeedForge", "KeyForge"],
        )

        assert analysis.summary == "This is a test summary."
        assert analysis.key_insight == "Key insight here."
        assert analysis.pain_severity == 3
        assert analysis.confidence == 0.85
        assert len(analysis.relevant_packages) == 2

    def test_content_analysis_optional_fields(self):
        """Test ContentAnalysis with None optional fields."""
        analysis = ContentAnalysis(
            summary="Summary only.",
            key_insight=None,
            feature_suggestion=None,
            pain_severity=None,
            takeaway=None,
            strategy_used=None,
            monetization_angle=None,
            geo_opportunity=None,
            keyword_opportunity=None,
            content_strategy=None,
            competitive_angle=None,
            image_opportunity=None,
            tech_insight=None,
            confidence=0.5,
            relevant_packages=[],
        )

        assert analysis.summary == "Summary only."
        assert analysis.key_insight is None
        assert analysis.relevant_packages == []


class TestLLMAnalyzerInit:
    """Tests for LLMAnalyzer initialization."""

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            analyzer = LLMAnalyzer(api_key=None)

            assert analyzer._api_key is None
            assert analyzer.is_available is False

    def test_init_with_openai_env_var(self):
        """Test initialization with OPENAI_API_KEY env var."""
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True),
            patch.object(LLMAnalyzer, "_init_client"),
        ):
            analyzer = LLMAnalyzer()

            assert analyzer._api_key == "test-key"
            assert analyzer._provider == "openai"
            assert analyzer._model == "gpt-4o-mini"

    def test_init_with_anthropic_env_var(self):
        """Test initialization with ANTHROPIC_API_KEY env var."""
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=True),
            patch.object(LLMAnalyzer, "_init_client"),
        ):
            analyzer = LLMAnalyzer()

            assert analyzer._api_key == "test-key"
            assert analyzer._provider == "anthropic"
            assert analyzer._model == "claude-3-haiku-20240307"

    def test_init_with_explicit_api_key(self):
        """Test initialization with explicit API key."""
        with patch.object(LLMAnalyzer, "_init_client"):
            analyzer = LLMAnalyzer(api_key="explicit-key")

            assert analyzer._api_key == "explicit-key"

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        with patch.object(LLMAnalyzer, "_init_client"):
            analyzer = LLMAnalyzer(api_key="key", model="gpt-4-turbo")

            assert analyzer._model == "gpt-4-turbo"

    def test_init_with_explicit_provider(self):
        """Test initialization with explicit provider."""
        with patch.object(LLMAnalyzer, "_init_client"):
            analyzer = LLMAnalyzer(api_key="key", provider="anthropic")

            assert analyzer._provider == "anthropic"


class TestLLMAnalyzerInitClient:
    """Tests for _init_client method."""

    def test_init_client_openai_success(self):
        """Test successful OpenAI client initialization."""
        mock_openai_class = MagicMock()
        mock_openai_class.return_value = MagicMock()

        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai_class)}):
            analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
            analyzer._api_key = "test-key"
            analyzer._provider = "openai"
            analyzer._model = "gpt-4o-mini"
            analyzer._client = None
            analyzer._available = False

            analyzer._init_client()

            assert analyzer._available is True
            mock_openai_class.assert_called_once_with(api_key="test-key")

    def test_init_client_anthropic_success(self):
        """Test successful Anthropic client initialization."""
        mock_anthropic_class = MagicMock()
        mock_anthropic_class.return_value = MagicMock()

        with patch.dict("sys.modules", {"anthropic": MagicMock(Anthropic=mock_anthropic_class)}):
            analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
            analyzer._api_key = "test-key"
            analyzer._provider = "anthropic"
            analyzer._model = "claude-3-haiku"
            analyzer._client = None
            analyzer._available = False

            analyzer._init_client()

            assert analyzer._available is True
            mock_anthropic_class.assert_called_once_with(api_key="test-key")

    def test_init_client_import_error_openai(self):
        """Test handling of OpenAI import error."""
        # Remove openai from sys.modules to trigger ImportError
        import sys

        # Clear any cached openai module
        sys.modules.pop("openai", None)

        def raise_import_error(*args, **kwargs):
            raise ImportError("No module named 'openai'")

        with patch("builtins.__import__", side_effect=raise_import_error):
            analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
            analyzer._api_key = "test-key"
            analyzer._provider = "openai"
            analyzer._model = "gpt-4o-mini"
            analyzer._client = None
            analyzer._available = False

            analyzer._init_client()

            assert analyzer._available is False

    def test_init_client_generic_error(self):
        """Test handling of generic error."""
        mock_openai_class = MagicMock()
        mock_openai_class.side_effect = Exception("Connection error")

        with patch.dict("sys.modules", {"openai": MagicMock(OpenAI=mock_openai_class)}):
            analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
            analyzer._api_key = "test-key"
            analyzer._provider = "openai"
            analyzer._model = "gpt-4o-mini"
            analyzer._client = None
            analyzer._available = False

            analyzer._init_client()

            assert analyzer._available is False


class TestLLMAnalyzerProperties:
    """Tests for LLMAnalyzer properties."""

    def test_is_available_true(self):
        """Test is_available when client is ready."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = MagicMock()

        assert analyzer.is_available is True

    def test_is_available_false_no_client(self):
        """Test is_available when no client."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = None

        assert analyzer.is_available is False

    def test_is_available_false_not_available(self):
        """Test is_available when not available."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = False
        analyzer._client = MagicMock()

        assert analyzer.is_available is False

    def test_provider_property(self):
        """Test provider property."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._provider = "openai"

        assert analyzer.provider == "openai"

    def test_provider_property_none(self):
        """Test provider property when None."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._provider = None

        assert analyzer.provider == "none"


class TestLLMAnalyzerCallLLM:
    """Tests for _call_llm method."""

    def test_call_llm_openai(self):
        """Test calling OpenAI API."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._provider = "openai"
        analyzer._model = "gpt-4o-mini"
        analyzer._max_tokens = 1024

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Response text"
        mock_client.chat.completions.create.return_value = mock_response
        analyzer._client = mock_client

        result = analyzer._call_llm("Test prompt")

        assert result == "Response text"
        mock_client.chat.completions.create.assert_called_once()

    def test_call_llm_anthropic(self):
        """Test calling Anthropic API."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._provider = "anthropic"
        analyzer._model = "claude-3-haiku"
        analyzer._max_tokens = 1024

        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content[0].text = "Anthropic response"
        mock_client.messages.create.return_value = mock_message
        analyzer._client = mock_client

        result = analyzer._call_llm("Test prompt")

        assert result == "Anthropic response"
        mock_client.messages.create.assert_called_once()

    def test_call_llm_error(self):
        """Test handling API error."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._provider = "openai"
        analyzer._model = "gpt-4o-mini"
        analyzer._max_tokens = 1024

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        analyzer._client = mock_client

        result = analyzer._call_llm("Test prompt")

        assert result is None


class TestLLMAnalyzerParseJSON:
    """Tests for _parse_json_response method."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        return analyzer

    def test_parse_plain_json(self, analyzer):
        """Test parsing plain JSON response."""
        response = '{"summary": "Test summary", "key_insight": "Insight"}'
        result = analyzer._parse_json_response(response)

        assert result["summary"] == "Test summary"
        assert result["key_insight"] == "Insight"

    def test_parse_json_with_markdown_code_block(self, analyzer):
        """Test parsing JSON wrapped in markdown code block."""
        response = '```json\n{"summary": "Test"}\n```'
        result = analyzer._parse_json_response(response)

        assert result["summary"] == "Test"

    def test_parse_json_with_generic_code_block(self, analyzer):
        """Test parsing JSON wrapped in generic code block."""
        response = '```\n{"summary": "Test"}\n```'
        result = analyzer._parse_json_response(response)

        assert result["summary"] == "Test"

    def test_parse_json_with_surrounding_text(self, analyzer):
        """Test parsing JSON with surrounding text."""
        response = 'Here is the analysis:\n{"summary": "Test"}\nHope this helps!'
        result = analyzer._parse_json_response(response)

        assert result["summary"] == "Test"

    def test_parse_invalid_json(self, analyzer):
        """Test parsing invalid JSON."""
        response = "This is not JSON at all"
        result = analyzer._parse_json_response(response)

        assert result is None


class TestLLMAnalyzerAnalyzeThread:
    """Tests for analyze_thread method."""

    def test_analyze_thread_not_available(self):
        """Test analyze_thread when LLM not available."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = False
        analyzer._client = None

        thread = MagicMock()
        result = analyzer.analyze_thread(thread)

        assert result is None

    def test_analyze_thread_success(self):
        """Test successful thread analysis."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = MagicMock()

        mock_thread = MagicMock()
        mock_thread.selftext = "This is the thread content about SEO."
        mock_thread.title = "SEO Question"

        with patch.object(
            analyzer,
            "_analyze",
            return_value=ContentAnalysis(
                summary="Test summary",
                key_insight="Key insight",
                feature_suggestion=None,
                pain_severity=None,
                takeaway=None,
                strategy_used=None,
                monetization_angle=None,
                geo_opportunity=None,
                keyword_opportunity=None,
                content_strategy=None,
                competitive_angle=None,
                image_opportunity=None,
                tech_insight=None,
                confidence=0.8,
                relevant_packages=[],
            ),
        ):
            result = analyzer.analyze_thread(mock_thread, category="pain_point")

            assert result is not None
            assert result.summary == "Test summary"

    def test_analyze_thread_truncates_content(self):
        """Test that long content is truncated."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = MagicMock()

        mock_thread = MagicMock()
        mock_thread.selftext = "x" * 10000  # Very long content
        mock_thread.title = "Title"

        with patch.object(analyzer, "_analyze") as mock_analyze:
            mock_analyze.return_value = None
            analyzer.analyze_thread(mock_thread)

            # Check that content was truncated
            call_args = mock_analyze.call_args
            content_arg = call_args[0][1]  # Second positional arg is content
            assert len(content_arg) <= 4000


class TestLLMAnalyzerAnalyzeVideo:
    """Tests for analyze_video method."""

    def test_analyze_video_not_available(self):
        """Test analyze_video when LLM not available."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = False
        analyzer._client = None

        video = MagicMock()
        result = analyzer.analyze_video(video)

        assert result is None

    def test_analyze_video_uses_transcript(self):
        """Test that analyze_video prefers transcript."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = MagicMock()

        mock_video = MagicMock()
        mock_video.transcript = "This is the transcript."
        mock_video.description = "This is the description."
        mock_video.title = "Video Title"

        with patch.object(analyzer, "_analyze") as mock_analyze:
            mock_analyze.return_value = None
            analyzer.analyze_video(mock_video)

            call_args = mock_analyze.call_args
            content_arg = call_args[0][1]
            assert "transcript" in content_arg.lower()


class TestLLMAnalyzerSummarizeLongThread:
    """Tests for summarize_long_thread method."""

    def test_summarize_long_thread_not_available(self):
        """Test summarize when not available."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = False
        analyzer._client = None

        result = analyzer.summarize_long_thread(MagicMock())

        assert result is None

    def test_summarize_long_thread_success(self):
        """Test successful thread summarization."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = MagicMock()

        mock_thread = MagicMock()
        mock_thread.selftext = "Long discussion about SEO..."
        mock_thread.title = "SEO Discussion"

        response_json = {
            "summary": "Thread summary",
            "consensus": "Everyone agrees SEO matters",
            "debate_points": ["Point 1", "Point 2"],
            "best_advice": "Focus on content",
            "key_quotes": ["Quote 1"],
        }

        with (
            patch.object(analyzer, "_call_llm", return_value=json.dumps(response_json)),
            patch.object(analyzer, "_parse_json_response", return_value=response_json),
        ):
            result = analyzer.summarize_long_thread(mock_thread)

            assert result is not None
            assert result["summary"] == "Thread summary"


class TestLLMAnalyzerBatchAnalyze:
    """Tests for batch_analyze method."""

    def test_batch_analyze_empty_list(self):
        """Test batch analysis with empty list."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = MagicMock()

        result = analyzer.batch_analyze([])

        assert result == {}

    def test_batch_analyze_not_available(self):
        """Test batch analysis when not available."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = False
        analyzer._client = None

        mock_thread = MagicMock()
        mock_thread.id = "123"

        result = analyzer.batch_analyze([mock_thread])

        assert result == {}

    def test_batch_analyze_respects_max_items(self):
        """Test that max_items is respected."""
        analyzer = LLMAnalyzer.__new__(LLMAnalyzer)
        analyzer._available = True
        analyzer._client = MagicMock()

        threads = [MagicMock() for _ in range(10)]
        for i, t in enumerate(threads):
            t.id = str(i)
            t.selftext = "Content"
            t.title = "Title"
            t.category = None

        with (
            patch.object(analyzer, "analyze_thread", return_value=None),
            patch("time.sleep"),
        ):
            analyzer.batch_analyze(threads, max_items=3)

            # Should only analyze first 3
            assert analyzer.analyze_thread.call_count == 3


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_analyzer_returns_instance(self):
        """Test that get_analyzer returns LLMAnalyzer."""
        import signalsift.processing.llm_analyzer as llm_module

        # Reset module-level instance
        llm_module._default_analyzer = None

        with patch.dict("os.environ", {}, clear=True):
            analyzer = get_analyzer()
            assert isinstance(analyzer, LLMAnalyzer)

    def test_get_analyzer_caches_instance(self):
        """Test that get_analyzer caches the instance."""
        import signalsift.processing.llm_analyzer as llm_module

        # Reset module-level instance
        llm_module._default_analyzer = None

        with patch.dict("os.environ", {}, clear=True):
            analyzer1 = get_analyzer()
            analyzer2 = get_analyzer()

            assert analyzer1 is analyzer2

    def test_is_llm_available_function(self):
        """Test is_llm_available function."""
        import signalsift.processing.llm_analyzer as llm_module

        # Reset module-level instance
        llm_module._default_analyzer = None

        with patch.dict("os.environ", {}, clear=True):
            result = is_llm_available()
            assert result is False

    def test_analyze_content_with_thread(self):
        """Test analyze_content with thread."""
        import signalsift.processing.llm_analyzer as llm_module

        # Reset module-level instance
        llm_module._default_analyzer = None

        mock_thread = MagicMock()

        with patch.dict("os.environ", {}, clear=True):
            result = analyze_content(thread=mock_thread)
            # Without API key, should return None
            assert result is None

    def test_analyze_content_with_video(self):
        """Test analyze_content with video."""
        import signalsift.processing.llm_analyzer as llm_module

        # Reset module-level instance
        llm_module._default_analyzer = None

        mock_video = MagicMock()

        with patch.dict("os.environ", {}, clear=True):
            result = analyze_content(video=mock_video)
            assert result is None

    def test_analyze_content_neither(self):
        """Test analyze_content with neither thread nor video."""
        result = analyze_content()
        assert result is None
