"""Embedding generation utilities for vector search."""

import os
import asyncio
from typing import List, Optional
import aiohttp
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential


class EmbeddingGenerator:
    """Generate embeddings for text using OpenAI or compatible APIs."""

    # Default embedding model
    DEFAULT_MODEL = "text-embedding-3-small"
    EMBEDDING_DIM = 1536

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        api_base: Optional[str] = None,
    ):
        """Initialize the embedding generator.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use for embeddings
            api_base: Custom API base URL for compatible services
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self.api_base = api_base or os.getenv(
            "OPENAI_API_BASE", "https://api.openai.com/v1"
        )

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        text: str,
        dimensions: Optional[int] = None,
    ) -> List[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed
            dimensions: Optional dimensions to reduce to

        Returns:
            List of floats representing the embedding
        """
        results = await self.generate_batch([text], dimensions)
        return results[0]

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate_batch(
        self,
        texts: List[str],
        dimensions: Optional[int] = None,
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed
            dimensions: Optional dimensions to reduce to

        Returns:
            List of embeddings
        """
        if not texts:
            return []

        # Clean texts
        texts = [t.replace("\n", " ").strip() for t in texts if t and t.strip()]

        if not texts:
            return []

        payload = {
            "model": self.model,
            "input": texts,
        }

        if dimensions:
            payload["dimensions"] = dimensions

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_base}/embeddings",
                headers=headers,
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(
                        f"Embedding API error: {response.status} - {error_text}"
                    )

                data = await response.json()

                # Sort by index to maintain order
                embeddings = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in embeddings]

    def sync_generate(
        self,
        text: str,
        dimensions: Optional[int] = None,
    ) -> List[float]:
        """Synchronous wrapper for generate.

        Args:
            text: Text to embed
            dimensions: Optional dimensions to reduce to

        Returns:
            List of floats representing the embedding
        """
        return asyncio.get_event_loop().run_until_complete(
            self.generate(text, dimensions)
        )

    def sync_generate_batch(
        self,
        texts: List[str],
        dimensions: Optional[int] = None,
    ) -> List[List[float]]:
        """Synchronous wrapper for generate_batch.

        Args:
            texts: List of texts to embed
            dimensions: Optional dimensions to reduce to

        Returns:
            List of embeddings
        """
        return asyncio.get_event_loop().run_until_complete(
            self.generate_batch(texts, dimensions)
        )

    @staticmethod
    def cosine_similarity(
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score between -1 and 1
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))


# Global embedding generator instance
_embedding_generator: Optional[EmbeddingGenerator] = None


def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create the global embedding generator instance."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
    return _embedding_generator
