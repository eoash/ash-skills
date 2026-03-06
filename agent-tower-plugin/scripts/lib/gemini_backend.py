"""Google Gemini API backend (direct API, not CLI)."""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from base import AgentBackend, StatusCallback
from response import AgentResponse, AgentRole

logger = logging.getLogger(__name__)


def _load_api_key() -> str:
    """Load GEMINI_API_KEY from env or .env file."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    # Walk up from this file to find .env
    here = Path(__file__).resolve()
    for parent in here.parents:
        env_file = parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return ""


class GeminiBackend(AgentBackend):
    """Backend for Google Gemini via direct API (google-genai SDK).

    Uses google.genai Python SDK for reliable non-interactive invocation.
    The Gemini CLI is a coding agent and refuses general analysis prompts;
    direct API access has no such restriction.
    """

    name = "gemini"

    def __init__(
        self,
        model: str = "gemini-2.5-flash-lite",
        timeout: int = 600,
        verbose: bool = False,
    ):
        """Initialize Gemini backend.

        Args:
            model: Gemini model ID (default: gemini-2.5-flash)
            timeout: Timeout in seconds
            verbose: Whether to print status to stderr
        """
        # gemini-1.5-flash: 1500 RPD 무료 / gemini-2.5-flash: 20 RPD 무료 (미리보기)
        self.model = model
        self.timeout = timeout
        self.verbose = verbose

    async def invoke(
        self,
        prompt: str,
        context: Optional[dict] = None,
        role: AgentRole = AgentRole.COUNCIL_MEMBER,
        status_callback: Optional[StatusCallback] = None,
    ) -> AgentResponse:
        """Invoke Gemini API with the given prompt."""
        if status_callback:
            status_callback(self.name, "Thinking...")

        try:
            content = await asyncio.wait_for(
                self._call_api(prompt),
                timeout=self.timeout,
            )

            if status_callback:
                status_callback(self.name, "Complete")

            return AgentResponse(
                agent_id=self.name,
                role=role,
                content=content,
                raw_output=content,
                metadata={"model": self.model},
            )

        except asyncio.TimeoutError:
            return AgentResponse(
                agent_id=self.name,
                role=role,
                content="[Error: Timeout]",
                metadata={"error": "timeout", "timeout_seconds": self.timeout},
            )
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return AgentResponse(
                agent_id=self.name,
                role=role,
                content=f"[Error: {str(e)}]",
                metadata={"error": str(e)},
            )

    async def _call_api(self, prompt: str) -> str:
        """Call Gemini API in a thread pool (SDK is synchronous)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_call, prompt)

    def _sync_call(self, prompt: str) -> str:
        """Synchronous Gemini API call."""
        try:
            from google import genai
        except ImportError:
            raise RuntimeError(
                "google-genai not installed. Run: pip install google-genai"
            )

        api_key = _load_api_key()
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Add it to .env or environment."
            )

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
        )
        return response.text or ""

    async def health_check(self) -> bool:
        """Check if Gemini API is configured (without consuming quota)."""
        try:
            from google import genai  # noqa: F401
            key = _load_api_key()
            return bool(key)
        except ImportError:
            return False
        except Exception:
            return False
