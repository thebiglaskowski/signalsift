"""LLM-powered content analysis for SignalSift.

This module uses OpenAI (or Anthropic) to pre-analyze content and extract
structured insights, filling in the report fields that would otherwise
require manual analysis.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from signalsift.utils.logging import get_logger

if TYPE_CHECKING:
    from signalsift.database.models import RedditThread, YouTubeVideo

logger = get_logger(__name__)


@dataclass
class ContentAnalysis:
    """Structured analysis result from LLM."""

    # Universal fields
    summary: str
    key_insight: str | None

    # Pain point fields
    feature_suggestion: str | None
    pain_severity: int | None  # 1-5

    # Success story fields
    takeaway: str | None
    strategy_used: str | None

    # Package-specific fields
    monetization_angle: str | None
    geo_opportunity: str | None
    keyword_opportunity: str | None
    content_strategy: str | None
    competitive_angle: str | None
    image_opportunity: str | None
    tech_insight: str | None

    # Metadata
    confidence: float
    relevant_packages: list[str]


# Analysis prompts for different content types
PAIN_POINT_PROMPT = """Analyze this SEO-related discussion that appears to be a pain point or problem.

Title: {title}
Content: {content}

Extract the following in JSON format:
{{
    "summary": "1-2 sentence summary of the problem",
    "feature_suggestion": "Specific feature that could solve this problem (or null if unclear)",
    "pain_severity": 1-5 rating of how severe/urgent this problem is,
    "key_insight": "The most important takeaway for a tool developer",
    "relevant_categories": ["list of relevant categories: keyword_research, monetization, competitive_analysis, content_creation, ai_tools, technical_seo, local_seo"],
    "monetization_angle": "Any monetization insight (or null)",
    "keyword_opportunity": "Any keyword research opportunity mentioned (or null)",
    "content_strategy": "Any content strategy insight (or null)",
    "competitive_angle": "Any competitive analysis insight (or null)",
    "tech_insight": "Any technical/performance insight (or null)",
    "geo_opportunity": "Any AI/GEO visibility insight (or null)"
}}

Be concise. If a field doesn't apply, use null."""

SUCCESS_STORY_PROMPT = """Analyze this SEO-related success story or case study.

Title: {title}
Content: {content}

Extract the following in JSON format:
{{
    "summary": "1-2 sentence summary of the success",
    "takeaway": "The key actionable takeaway",
    "strategy_used": "The main strategy or technique that worked",
    "key_insight": "The most important lesson for other SEOs",
    "relevant_categories": ["list of relevant categories"],
    "monetization_angle": "Revenue/monetization insight (or null)",
    "keyword_opportunity": "Keyword strategy that worked (or null)",
    "content_strategy": "Content approach that worked (or null)",
    "competitive_angle": "How they beat competition (or null)",
    "tech_insight": "Technical optimization that helped (or null)",
    "geo_opportunity": "AI visibility insight (or null)"
}}

Focus on extracting replicable strategies. Be concise."""

GENERAL_PROMPT = """Analyze this SEO-related content for actionable insights.

Title: {title}
Content: {content}

Extract the following in JSON format:
{{
    "summary": "1-2 sentence summary",
    "key_insight": "The most valuable insight from this content",
    "relevant_categories": ["list of relevant categories: keyword_research, monetization, competitive_analysis, content_creation, ai_tools, technical_seo, local_seo"],
    "monetization_angle": "Monetization insight (or null)",
    "keyword_opportunity": "Keyword research insight (or null)",
    "content_strategy": "Content strategy insight (or null)",
    "competitive_angle": "Competitive insight (or null)",
    "tech_insight": "Technical insight (or null)",
    "geo_opportunity": "AI/GEO visibility insight (or null)",
    "image_opportunity": "Visual content insight (or null)"
}}

Be concise and focus on actionable insights."""

THREAD_SUMMARY_PROMPT = """Summarize this long Reddit thread discussion about SEO.

Title: {title}
Content: {content}

Provide a JSON response:
{{
    "summary": "3-4 sentence summary of the entire discussion",
    "consensus": "What does the community generally agree on?",
    "debate_points": ["Points where people disagree"],
    "best_advice": "The most upvoted/agreed upon advice",
    "key_quotes": ["1-3 most insightful quotes from the discussion"]
}}

Focus on extracting the collective wisdom from the discussion."""


class LLMAnalyzer:
    """Analyze content using OpenAI or Anthropic API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 1024,
        provider: str | None = None,
    ) -> None:
        """
        Initialize the LLM analyzer.

        Args:
            api_key: API key. Auto-detects from env vars if not provided.
            model: Model to use. Defaults based on provider.
            max_tokens: Maximum tokens in response.
            provider: "openai" or "anthropic". Auto-detects if not specified.
        """
        self._max_tokens = max_tokens
        self._client = None
        self._available = False
        self._provider = provider

        # Auto-detect provider and API key
        if api_key:
            self._api_key = api_key
        elif os.environ.get("OPENAI_API_KEY"):
            self._api_key = os.environ.get("OPENAI_API_KEY")
            self._provider = self._provider or "openai"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            self._api_key = os.environ.get("ANTHROPIC_API_KEY")
            self._provider = self._provider or "anthropic"
        else:
            self._api_key = None

        # Set default model based on provider
        if model:
            self._model = model
        elif self._provider == "anthropic":
            self._model = "claude-3-haiku-20240307"
        else:
            # Default to OpenAI
            self._provider = self._provider or "openai"
            self._model = "gpt-4o-mini"  # Fast and cost-effective

        if self._api_key:
            self._init_client()

    def _init_client(self) -> None:
        """Initialize the API client based on provider."""
        try:
            if self._provider == "anthropic":
                from anthropic import Anthropic

                self._client = Anthropic(api_key=self._api_key)
                self._available = True
                logger.info(f"LLM analyzer initialized (Anthropic): {self._model}")
            else:
                # OpenAI
                from openai import OpenAI

                self._client = OpenAI(api_key=self._api_key)
                self._available = True
                logger.info(f"LLM analyzer initialized (OpenAI): {self._model}")

        except ImportError as e:
            if self._provider == "anthropic":
                logger.warning(
                    "Anthropic SDK not installed - LLM analysis unavailable. "
                    "Install with: pip install anthropic"
                )
            else:
                logger.warning(
                    "OpenAI SDK not installed - LLM analysis unavailable. "
                    "Install with: pip install openai"
                )
            self._available = False
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}")
            self._available = False

    @property
    def is_available(self) -> bool:
        """Check if LLM analysis is available."""
        return self._available and self._client is not None

    @property
    def provider(self) -> str:
        """Get the current provider name."""
        return self._provider or "none"

    def _call_llm(self, prompt: str) -> str | None:
        """Call the LLM API and return the response text."""
        try:
            if self._provider == "anthropic":
                message = self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message.content[0].text
            else:
                # OpenAI
                response = self._client.chat.completions.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content

        except Exception as e:
            logger.warning(f"LLM API call failed: {e}")
            return None

    def analyze_thread(
        self,
        thread: RedditThread,
        category: str | None = None,
    ) -> ContentAnalysis | None:
        """
        Analyze a Reddit thread and extract structured insights.

        Args:
            thread: The Reddit thread to analyze.
            category: Content category (pain_point, success_story, etc.).

        Returns:
            ContentAnalysis with extracted insights, or None if unavailable.
        """
        if not self.is_available:
            return None

        # Prepare content (truncate if too long)
        content = (thread.selftext or "")[:4000]
        title = thread.title or ""

        # Select appropriate prompt
        if category == "pain_point":
            prompt = PAIN_POINT_PROMPT
        elif category == "success_story":
            prompt = SUCCESS_STORY_PROMPT
        else:
            prompt = GENERAL_PROMPT

        return self._analyze(title, content, prompt)

    def analyze_video(
        self,
        video: YouTubeVideo,
        category: str | None = None,
    ) -> ContentAnalysis | None:
        """
        Analyze a YouTube video and extract structured insights.

        Args:
            video: The YouTube video to analyze.
            category: Content category.

        Returns:
            ContentAnalysis with extracted insights, or None if unavailable.
        """
        if not self.is_available:
            return None

        # Use transcript if available, otherwise description
        content = (video.transcript or video.description or "")[:6000]
        title = video.title or ""

        # Select appropriate prompt
        if category == "pain_point":
            prompt = PAIN_POINT_PROMPT
        elif category == "success_story":
            prompt = SUCCESS_STORY_PROMPT
        else:
            prompt = GENERAL_PROMPT

        return self._analyze(title, content, prompt)

    def summarize_long_thread(
        self,
        thread: RedditThread,
    ) -> dict | None:
        """
        Summarize a long thread with multiple perspectives.

        Args:
            thread: The Reddit thread to summarize.

        Returns:
            Dict with summary, consensus, debate points, etc.
        """
        if not self.is_available:
            return None

        content = (thread.selftext or "")[:8000]
        title = thread.title or ""

        prompt = THREAD_SUMMARY_PROMPT.format(title=title, content=content)
        response_text = self._call_llm(prompt)

        if response_text:
            return self._parse_json_response(response_text)
        return None

    def _analyze(
        self,
        title: str,
        content: str,
        prompt_template: str,
    ) -> ContentAnalysis | None:
        """Run analysis with given prompt."""
        prompt = prompt_template.format(title=title, content=content)
        response_text = self._call_llm(prompt)

        if not response_text:
            return None

        data = self._parse_json_response(response_text)

        if data is None:
            return None

        return ContentAnalysis(
            summary=data.get("summary", ""),
            key_insight=data.get("key_insight"),
            feature_suggestion=data.get("feature_suggestion"),
            pain_severity=data.get("pain_severity"),
            takeaway=data.get("takeaway"),
            strategy_used=data.get("strategy_used"),
            monetization_angle=data.get("monetization_angle"),
            geo_opportunity=data.get("geo_opportunity"),
            keyword_opportunity=data.get("keyword_opportunity"),
            content_strategy=data.get("content_strategy"),
            competitive_angle=data.get("competitive_angle"),
            image_opportunity=data.get("image_opportunity"),
            tech_insight=data.get("tech_insight"),
            confidence=0.8,  # Could be calculated based on response quality
            relevant_packages=data.get("relevant_packages", []),
        )

    def _parse_json_response(self, response: str) -> dict | None:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Try to find JSON in the response
        response = response.strip()

        # Handle markdown code blocks
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON object in response
            try:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass

            logger.warning(f"Failed to parse JSON from response: {response[:200]}...")
            return None

    def batch_analyze(
        self,
        threads: list[RedditThread],
        max_items: int = 20,
    ) -> dict[str, ContentAnalysis]:
        """
        Analyze multiple threads (with rate limiting).

        Args:
            threads: Threads to analyze.
            max_items: Maximum items to analyze (for cost control).

        Returns:
            Dict mapping thread IDs to analysis results.
        """
        import time

        results: dict[str, ContentAnalysis] = {}

        for i, thread in enumerate(threads[:max_items]):
            if not self.is_available:
                break

            analysis = self.analyze_thread(thread, thread.category)
            if analysis:
                results[thread.id] = analysis

            # Rate limiting - 1 request per second
            if i < len(threads) - 1:
                time.sleep(1)

        logger.info(f"Analyzed {len(results)} threads with LLM")
        return results


# Module-level instance
_default_analyzer: LLMAnalyzer | None = None


def get_analyzer() -> LLMAnalyzer:
    """Get the default LLM analyzer instance."""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = LLMAnalyzer()
    return _default_analyzer


def analyze_content(
    thread: RedditThread | None = None,
    video: YouTubeVideo | None = None,
    category: str | None = None,
) -> ContentAnalysis | None:
    """Convenience function to analyze content."""
    analyzer = get_analyzer()

    if thread:
        return analyzer.analyze_thread(thread, category)
    elif video:
        return analyzer.analyze_video(video, category)
    return None


def is_llm_available() -> bool:
    """Check if LLM analysis is available."""
    return get_analyzer().is_available
