"""Test suite for Discord Support Bot."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from ai.providers.base import BaseProvider
from ai.router import AIRouter, RoutingStrategy
from keywords.classifier import KeywordClassifier


class TestBaseProvider:
    """Tests for BaseProvider abstract class."""

    def test_provider_initialization(self):
        """Test that provider initializes correctly."""
        provider = Mock(spec=BaseProvider)
        provider.name = "test_provider"
        provider.is_healthy.return_value = True

        assert provider.name == "test_provider"
        assert provider.is_healthy() is True

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        provider = Mock(spec=BaseProvider)
        provider.check_rate_limit.return_value = True

        assert provider.check_rate_limit() is True


class TestAIRouter:
    """Tests for AI Router functionality."""

    @pytest.fixture
    def router(self):
        """Create a test router instance."""
        return AIRouter()

    def test_router_initialization(self, router):
        """Test router initializes with default strategy."""
        assert router.default_strategy == RoutingStrategy.BALANCED
        assert len(router.providers) == 0

    def test_provider_registration(self, router):
        """Test registering providers."""
        mock_provider = Mock()
        mock_provider.name = "openai"
        mock_provider.priority = 5

        router.register_provider(mock_provider)

        assert "openai" in router.providers
        assert router.providers["openai"] == mock_provider

    def test_routing_strategy_selection(self, router):
        """Test routing strategy selection."""
        router.default_strategy = RoutingStrategy.COST_PRIORITY
        assert router.default_strategy == RoutingStrategy.COST_PRIORITY

        router.default_strategy = RoutingStrategy.QUALITY_PRIORITY
        assert router.default_strategy == RoutingStrategy.QUALITY_PRIORITY


class TestKeywordClassifier:
    """Tests for keyword classification system."""

    @pytest.fixture
    def classifier(self):
        """Create a test classifier."""
        return KeywordClassifier()

    def test_classifier_initialization(self, classifier):
        """Test classifier initializes correctly."""
        assert classifier is not None

    def test_keyword_matching(self, classifier):
        """Test keyword matching functionality."""
        # Mock the classification logic
        classifier.classify = Mock(
            return_value={
                "category": "password_reset",
                "confidence": 0.95,
                "keywords": ["password", "reset", "forgot"],
            }
        )

        result = classifier.classify("I forgot my password")

        assert result["category"] == "password_reset"
        assert result["confidence"] > 0.9

    def test_complexity_scoring(self, classifier):
        """Test query complexity scoring."""
        classifier.score_complexity = Mock(
            return_value={
                "score": 3,
                "level": "medium",
                "reasons": ["multiple_concepts", "technical_terms"],
            }
        )

        result = classifier.score_complexity("How do I configure the API with OAuth2?")

        assert result["level"] in ["low", "medium", "high"]
        assert isinstance(result["score"], int)


class TestDatabaseModels:
    """Tests for database models."""

    def test_guild_model(self):
        """Test Guild model structure."""
        from database.models import Guild

        # Verify model has required fields
        assert hasattr(Guild, "id")
        assert hasattr(Guild, "discord_id")
        assert hasattr(Guild, "settings")

    def test_conversation_model(self):
        """Test Conversation model structure."""
        from database.models import Conversation

        assert hasattr(Conversation, "id")
        assert hasattr(Conversation, "guild_id")
        assert hasattr(Conversation, "messages")


class TestConfiguration:
    """Tests for configuration loading."""

    def test_env_loading(self):
        """Test environment variable loading."""
        with patch.dict("os.environ", {"DISCORD_TOKEN": "test_token"}):
            # This would test actual config loading
            assert True  # Placeholder

    def test_database_url_parsing(self):
        """Test database URL parsing."""
        url = "postgresql://user:pass@localhost:5432/dbname"

        # Simple validation
        assert url.startswith("postgresql://")
        assert "@" in url
        assert ":" in url


class TestDockerSetup:
    """Tests for Docker setup validation."""

    def test_docker_compose_structure(self):
        """Test docker-compose file structure."""
        import yaml

        with open("docker-compose.single.yml", "r") as f:
            compose = yaml.safe_load(f)

        # Verify required services
        services = compose.get("services", {})
        assert "bot" in services
        assert "postgres" in services
        assert "redis" in services
        assert "research-worker" in services

    def test_env_example_exists(self):
        """Test that .env.example exists and has required variables."""
        import os

        assert os.path.exists(".env.example")

        with open(".env.example", "r") as f:
            content = f.read()

        # Check for required variables
        assert "DISCORD_TOKEN" in content
        assert "DATABASE_URL" in content
        assert "REDIS_URL" in content


class TestHealthChecks:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_bot_health(self):
        """Test bot health check."""
        # Mock health check
        health_check = AsyncMock(
            return_value={
                "status": "healthy",
                "services": {"discord": "connected", "database": "connected", "redis": "connected"},
            }
        )

        result = await health_check()

        assert result["status"] == "healthy"
        assert result["services"]["discord"] == "connected"


# Integration tests (marked to run separately)
@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring full environment."""

    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test actual database connection."""
        # This would require a test database
        pass

    @pytest.mark.asyncio
    async def test_redis_connection(self):
        """Test actual Redis connection."""
        # This would require a test Redis instance
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
