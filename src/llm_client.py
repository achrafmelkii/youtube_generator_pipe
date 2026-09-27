"""
LLM client wrapper for the documentary generator.
Handles Claude/GPT prompting, retries, structured JSON output, and caching.
"""

import json
import os
import hashlib
from typing import Any, Dict, Optional
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Wrapper around Claude or OpenAI API for structured generation with caching.
    Supports retry logic, caching to disk, and structured JSON output.
    """

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: Optional[str] = None,
        cache_dir: str = ".llm_cache",
        max_retries: int = 3,
        retry_delay: float = 2.0,
        use_anthropic: bool = True,
    ):
        """
        Initialize LLM client.
        
        Args:
            model: Model identifier
            api_key: API key (uses env var if not provided)
            cache_dir: Directory for caching responses
            max_retries: Number of retry attempts for API calls
            retry_delay: Delay between retries in seconds
            use_anthropic: If True, use Anthropic; if False, use OpenAI
        """
        self.model = model
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.use_anthropic = use_anthropic

        if use_anthropic:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            import openai
            self.client = openai.OpenAI(api_key=api_key)

    def _get_cache_path(self, prompt_hash: str) -> Path:
        """Get cache file path for a prompt hash."""
        return self.cache_dir / f"{prompt_hash}.json"

    def _hash_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """Generate a hash of the prompt for caching."""
        combined = f"{system_prompt}||{user_prompt}".encode()
        return hashlib.md5(combined).hexdigest()

    def _load_cached_response(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """Load cached response if available."""
        cache_path = self._get_cache_path(prompt_hash)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    logger.info(f"Cache hit for {prompt_hash}")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache {cache_path}: {e}")
        return None

    def _save_cached_response(self, prompt_hash: str, response: Dict[str, Any]) -> None:
        """Save response to cache."""
        cache_path = self._get_cache_path(prompt_hash)
        try:
            with open(cache_path, 'w') as f:
                json.dump(response, f, indent=2)
                logger.info(f"Cached response to {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_path}: {e}")

    def prompt(
        self,
        user_prompt: str,
        system_prompt: str = "",
        json_mode: bool = True,
        use_cache: bool = True,
    ) -> str:
        """
        Send a prompt to the LLM and get a response.

        Args:
            user_prompt: The main prompt
            system_prompt: System/context prompt
            json_mode: If True, request JSON-formatted output
            use_cache: If True, check cache before calling API

        Returns:
            The LLM response text
        """
        prompt_hash = self._hash_prompt(system_prompt, user_prompt)

        # Check cache
        if use_cache:
            cached = self._load_cached_response(prompt_hash)
            if cached:
                return cached.get("response", "")

        # Call API with retries
        for attempt in range(self.max_retries):
            try:
                if self.use_anthropic:
                    response = self._call_anthropic(
                        user_prompt, system_prompt, json_mode
                    )
                else:
                    response = self._call_openai(user_prompt, system_prompt, json_mode)

                # Cache success
                if use_cache:
                    self._save_cached_response(
                        prompt_hash, {"response": response, "model": self.model}
                    )

                return response

            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise

    def _call_anthropic(
        self, user_prompt: str, system_prompt: str, json_mode: bool
    ) -> str:
        """Call Anthropic Claude API."""
        messages = [{"role": "user", "content": user_prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt or None,
            "messages": messages,
        }

        # Remove None system prompt
        if kwargs["system"] is None:
            del kwargs["system"]

        if json_mode:
            kwargs["temperature"] = 0  # More deterministic for JSON
        
        message = self.client.messages.create(**kwargs)
        return message.content[0].text

    def _call_openai(
        self, user_prompt: str, system_prompt: str, json_mode: bool
    ) -> str:
        """Call OpenAI API."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        kwargs = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
            kwargs["temperature"] = 0

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def prompt_structured(
        self,
        user_prompt: str,
        system_prompt: str = "",
        expected_schema: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Send a prompt expecting JSON response and parse it.

        Args:
            user_prompt: The main prompt (should ask for JSON)
            system_prompt: System context
            expected_schema: Optional JSON schema for validation
            use_cache: Use caching

        Returns:
            Parsed JSON as dict
        """
        response_text = self.prompt(
            user_prompt, system_prompt, json_mode=True, use_cache=use_cache
        )

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response_text}")
            raise ValueError(f"LLM did not return valid JSON: {e}")
