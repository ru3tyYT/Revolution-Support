"""Intent classification using semantic similarity and AI."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import re
import asyncio
from difflib import SequenceMatcher


@dataclass
class IntentClassification:
    """Result of intent classification."""

    intent: str
    confidence: float
    method: str  # 'semantic', 'ai', 'fuzzy', 'exact'
    matched_keywords: List[str]
    category: Optional[str] = None
    metadata: Dict[str, Any] = None


class IntentClassifier:
    """Classifies user intent using multiple methods."""

    def __init__(
        self,
        use_semantic: bool = True,
        use_ai: bool = True,
        semantic_threshold: float = 0.75,
        ai_threshold: float = 0.8,
        fuzzy_threshold: float = 0.85,
    ):
        self.use_semantic = use_semantic
        self.use_ai = use_ai
        self.semantic_threshold = semantic_threshold
        self.ai_threshold = ai_threshold
        self.fuzzy_threshold = fuzzy_threshold

        # Intent patterns for rule-based matching
        self.intent_patterns: Dict[str, List[str]] = {
            "help": [
                r"help",
                r"assist",
                r"support",
                r"how do i",
                r"how to",
                r"how can i",
            ],
            "billing": [
                r"bill",
                r"payment",
                r"charge",
                r"subscription",
                r"price",
                r"cost",
                r"refund",
            ],
            "technical": [
                r"error",
                r"bug",
                r"issue",
                r"problem",
                r"crash",
                r"broken",
                r"not working",
            ],
            "account": [
                r"account",
                r"login",
                r"password",
                r"reset",
                r"signup",
                r"register",
            ],
            "feature": [
                r"feature",
                r"add",
                r"implement",
                r"suggest",
                r"request",
                r"idea",
            ],
        }

        # pgvector connection (initialized later)
        self._pgvector_conn = None
        self._embedding_model = None
        self._ai_client = None

    async def classify(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> IntentClassification:
        """
        Classify the intent of a user message.

        Tries multiple methods in order of cost:
        1. Exact/regex matching (cheapest)
        2. Fuzzy matching
        3. Semantic similarity (pgvector)
        4. AI classification (most expensive, edge cases only)
        """
        message_lower = message.lower().strip()

        # 1. Try exact/regex matching first
        result = self._rule_based_classify(message_lower)
        if result and result.confidence >= 0.9:
            return result

        # 2. Try fuzzy matching
        fuzzy_result = self._fuzzy_classify(message_lower)
        if fuzzy_result and fuzzy_result.confidence >= self.fuzzy_threshold:
            return fuzzy_result

        # Keep best result so far
        best_result = result or fuzzy_result

        # 3. Try semantic similarity if enabled
        if self.use_semantic and self._pgvector_conn:
            semantic_result = await self._semantic_classify(message)
            if (
                semantic_result
                and semantic_result.confidence >= self.semantic_threshold
            ):
                if (
                    not best_result
                    or semantic_result.confidence > best_result.confidence
                ):
                    best_result = semantic_result

        # 4. Try AI classification for edge cases if enabled and confidence is low
        if self.use_ai and self._ai_client:
            if not best_result or best_result.confidence < self.ai_threshold:
                ai_result = await self._ai_classify(message, context)
                if ai_result and ai_result.confidence >= self.ai_threshold:
                    if not best_result or ai_result.confidence > best_result.confidence:
                        best_result = ai_result

        # Return best result or unknown
        if best_result:
            return best_result

        return IntentClassification(
            intent="unknown",
            confidence=0.0,
            method="none",
            matched_keywords=[],
        )

    def _rule_based_classify(self, message: str) -> Optional[IntentClassification]:
        """Classify intent using regex patterns."""
        matched_intents = []

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    matched_intents.append(intent)
                    break

        if matched_intents:
            # Return the first matched intent with high confidence
            return IntentClassification(
                intent=matched_intents[0],
                confidence=0.9,
                method="exact",
                matched_keywords=matched_intents,
            )

        return None

    def _fuzzy_classify(self, message: str) -> Optional[IntentClassification]:
        """Classify intent using fuzzy string matching."""
        best_match = None
        best_score = 0.0

        # Check against intent keywords
        intent_keywords = {
            "help": ["help", "assist", "support", "guide", "how to"],
            "billing": ["billing", "payment", "charge", "price", "cost", "money"],
            "technical": ["error", "bug", "issue", "problem", "crash", "broken"],
            "account": ["account", "login", "sign in", "password", "auth"],
            "feature": ["feature", "suggestion", "idea", "request", "add"],
        }

        for intent, keywords in intent_keywords.items():
            for keyword in keywords:
                # Use sequence matcher for fuzzy matching
                matcher = SequenceMatcher(None, message, keyword)
                score = matcher.ratio()

                # Also check individual words
                for word in message.split():
                    word_matcher = SequenceMatcher(None, word, keyword)
                    word_score = word_matcher.ratio()
                    score = max(score, word_score)

                if score > best_score and score >= self.fuzzy_threshold:
                    best_score = score
                    best_match = intent

        if best_match:
            return IntentClassification(
                intent=best_match,
                confidence=best_score,
                method="fuzzy",
                matched_keywords=[best_match],
            )

        return None

    async def _semantic_classify(self, message: str) -> Optional[IntentClassification]:
        """Classify intent using semantic similarity with pgvector."""
        if not self._pgvector_conn:
            return None

        try:
            # Generate embedding for the message
            embedding = await self._generate_embedding(message)

            # Query pgvector for similar intents
            query = """
                SELECT intent, category, embedding <=> %s as distance
                FROM intent_embeddings
                ORDER BY embedding <=> %s
                LIMIT 1
            """

            # This would be async pg query in production
            # result = await self._pgvector_conn.fetch(query, embedding, embedding)

            # Placeholder for actual implementation
            # if result and result[0]['distance'] < (1 - self.semantic_threshold):
            #     return IntentClassification(
            #         intent=result[0]['intent'],
            #         confidence=1 - result[0]['distance'],
            #         method="semantic",
            #         matched_keywords=[result[0]['intent']],
            #         category=result[0]['category'],
            #     )

            return None
        except Exception:
            return None

    async def _ai_classify(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[IntentClassification]:
        """Classify intent using AI/LLM for edge cases."""
        if not self._ai_client:
            return None

        try:
            # Build prompt with context
            prompt = self._build_classification_prompt(message, context)

            # Call AI model
            # response = await self._ai_client.complete(prompt)
            # Parse response to get intent and confidence

            # Placeholder for actual implementation
            # intent = parse_intent_from_response(response)
            # confidence = parse_confidence_from_response(response)

            # For now, return None (implement when AI client is available)
            return None
        except Exception:
            return None

    def _build_classification_prompt(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build a prompt for AI classification."""
        base_prompt = f"""Classify the intent of the following user message.

Available intents:
- help: User needs assistance or guidance
- billing: Questions about payments, charges, or subscriptions
- technical: Technical issues, bugs, or errors
- account: Account-related questions (login, password, etc.)
- feature: Feature requests or suggestions
- general: General inquiries

User message: "{message}"

Respond with:
Intent: <intent_name>
Confidence: <0.0-1.0>
Reasoning: <brief explanation>"""

        if context:
            base_prompt += f"\n\nContext: {context}"

        return base_prompt

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using the embedding model."""
        if not self._embedding_model:
            # Return empty embedding if model not available
            return []

        # Implement actual embedding generation
        # return await self._embedding_model.embed(text)
        return []

    def set_pgvector_connection(self, conn):
        """Set the pgvector database connection."""
        self._pgvector_conn = conn

    def set_embedding_model(self, model):
        """Set the embedding model for semantic search."""
        self._embedding_model = model

    def set_ai_client(self, client):
        """Set the AI client for classification."""
        self._ai_client = client

    def add_intent_pattern(self, intent: str, patterns: List[str]):
        """Add custom intent patterns."""
        if intent not in self.intent_patterns:
            self.intent_patterns[intent] = []
        self.intent_patterns[intent].extend(patterns)

    def batch_classify(
        self,
        messages: List[str],
    ) -> List[IntentClassification]:
        """Classify multiple messages (synchronous version)."""
        results = []
        for message in messages:
            result = asyncio.run(self.classify(message))
            results.append(result)
        return results
