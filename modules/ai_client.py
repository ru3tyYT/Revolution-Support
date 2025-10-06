# modules/ai_client.py
"""
AI client wrapper for calling Gemini (or another LLM).
Simple, robust parsing and concurrency control.
"""
import aiohttp
import asyncio
import logging
from typing import Optional

logger = logging.getLogger("ai_client")

class AIClient:
    def __init__(self, api_key: Optional[str]=None, max_concurrency: int = 2):
        self.api_key = api_key
        self._session = None
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def init_session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def close_session(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def generate_fix(self, prompt: str) -> str:
        """
        Sends the prompt to Gemini API and returns a text output.
        Uses a semaphore to limit concurrency.
        """
        async with self._semaphore:
            return await self._call_api(prompt)

    async def _call_api(self, prompt: str) -> str:
        if not self._session:
            await self.init_session()
        # Example Gemini endpoint. In production you may need to adapt headers/auth.
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-goog-api-key"] = self.api_key
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            async with self._session.post(url, headers=headers, json=body, timeout=60) as resp:
                # prefer JSON parse
                try:
                    data = await resp.json()
                except Exception:
                    text = await resp.text()
                    logger.error("Non-JSON response from AI: %s", text[:500])
                    return text[:4000]
                # parse common shapes
                # shape: { candidates: [ { content: [ { parts: [ { text: "..." } ] } ] } ] }
                text_out = None
                if isinstance(data, dict):
                    candidates = data.get("candidates") or data.get("outputs") or []
                    if candidates:
                        first = candidates[0]
                        # content could be list or dict or string
                        content = first.get("content") if isinstance(first, dict) else None
                        if isinstance(content, list) and content:
                            parts = content[0].get("parts", [])
                            text_out = "".join(p.get("text","") for p in parts)
                        elif isinstance(content, dict):
                            parts = content.get("parts", [])
                            if parts:
                                text_out = parts[0].get("text")
                        elif isinstance(content, str):
                            text_out = content
                    # fallback: top-level text fields
                    if not text_out:
                        for key in ["text", "message", "output"]:
                            if key in data and isinstance(data[key], str):
                                text_out = data[key]
                if not text_out:
                    # final fallback, try to stringify
                    text_out = str(data)
                return text_out
        except asyncio.TimeoutError:
            logger.exception("AI request timed out")
            return "⚠️ AI request timed out."
        except Exception:
            logger.exception("AI request failed")
            return "⚠️ AI request failed."
