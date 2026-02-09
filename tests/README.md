# Tests

This directory contains the test suite for the Discord Support Bot.

## Quick Start

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest tests/test_basic.py

# Run tests matching a pattern
pytest -k "test_router"

# Run in parallel (faster)
pytest -x
```

## Running Tests

### Basic Commands

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests |
| `pytest -v` | Run with verbose output |
| `pytest -x` | Stop on first failure |
| `pytest --tb=short` | Shorter traceback format |
| `pytest -s` | Show print statements |
| `pytest --lf` | Run only last failed tests |

### With Coverage

```bash
# Terminal report with missing lines
pytest --cov=bot --cov-report=term-missing

# Generate HTML report
pytest --cov=bot --cov-report=html

# Generate XML report (for CI)
pytest --cov=bot --cov-report=xml
```

### Using Hatch

```bash
# Run tests
hatch run test

# Run with coverage HTML report
hatch run test-cov

# Run all checks (lint, typecheck, test)
hatch run all-checks
```

## Test Structure

```
tests/
├── __init__.py           # Makes tests a package
├── test_basic.py         # Core functionality tests
├── conftest.py          # Shared fixtures (create as needed)
├── unit/                # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_ai/         # AI provider tests
│   ├── test_database/   # Database model tests
│   └── test_bot/        # Bot command tests
├── integration/         # Integration tests (requires services)
│   ├── __init__.py
│   ├── test_database.py
│   └── test_redis.py
└── fixtures/            # Test data and fixtures
    ├── __init__.py
    └── factories.py     # Factory Boy factories
```

## Test Types

### Unit Tests

Fast, isolated tests that don't require external services. These use mocks and stubs.

```python
# tests/unit/test_ai_router.py
import pytest
from unittest.mock import Mock, patch
from ai.router import AIRouter

class TestAIRouter:
    def test_provider_registration(self):
        """Test registering providers."""
        router = AIRouter()
        mock_provider = Mock()
        mock_provider.name = "openai"

        router.register_provider(mock_provider)

        assert "openai" in router.providers
```

**Mark with:** `@pytest.mark.unit`

### Integration Tests

Tests that verify components work together and require real services (database, Redis, etc.).

```python
# tests/integration/test_database.py
import pytest
from database.session import get_db_session

@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    async def test_connection(self):
        """Test actual database connection."""
        async with get_db_session() as session:
            result = await session.execute("SELECT 1")
            assert result.scalar() == 1
```

**Mark with:** `@pytest.mark.integration`

### Async Tests

Most bot code is async. Use `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is True
```

## Writing New Tests

### 1. Create Test File

Name your file `test_<module>.py` in the appropriate directory.

### 2. Use Descriptive Names

```python
# Good
def test_user_creation_saves_to_database():
def test_empty_username_raises_validation_error():

# Bad
def test_user():
def test_1():
```

### 3. Arrange-Act-Assert Pattern

```python
def test_keyword_classifier_scores_complexity():
    # Arrange
    classifier = KeywordClassifier()
    query = "How do I configure the API with OAuth2?"

    # Act
    result = classifier.score_complexity(query)

    # Assert
    assert result["level"] in ["low", "medium", "high"]
    assert isinstance(result["score"], int)
```

### 4. Use Fixtures

```python
import pytest

@pytest.fixture
def mock_provider():
    provider = Mock()
    provider.name = "test_provider"
    provider.generate = AsyncMock(return_value="Test response")
    return provider

@pytest.fixture
def router(mock_provider):
    router = AIRouter()
    router.register_provider(mock_provider)
    return router

def test_router_with_fixture(router):
    assert len(router.providers) == 1
```

### 5. Mock External Services

```python
from unittest.mock import Mock, patch, AsyncMock

# Mock a function
with patch("bot.commands.get_user") as mock_get_user:
    mock_get_user.return_value = {"id": 123, "name": "Test"}
    # ... test code

# Mock an async function
mock_generate = AsyncMock(return_value="AI response")
with patch("ai.providers.openai.OpenAIProvider.generate", mock_generate):
    # ... test code
```

## Test Markers

Use markers to categorize tests:

| Marker | Use For | Run Command |
|--------|---------|-------------|
| `@pytest.mark.unit` | Fast unit tests | `pytest -m unit` |
| `@pytest.mark.integration` | Tests needing services | `pytest -m integration` |
| `@pytest.mark.slow` | Slow tests | `pytest -m "not slow"` |
| `@pytest.mark.ai` | Tests using AI providers | `pytest -m ai` |
| `@pytest.mark.database` | Tests needing database | `pytest -m database` |
| `@pytest.mark.redis` | Tests needing Redis | `pytest -m redis` |

### Example

```python
import pytest

@pytest.mark.unit
@pytest.mark.asyncio
async def test_fast_unit():
    pass

@pytest.mark.integration
@pytest.mark.database
async def test_database_integration():
    pass

@pytest.mark.slow
@pytest.mark.ai
async def test_openai_integration():
    pass
```

## Coverage Reporting

### View Coverage

After running tests with `--cov`, reports are generated:

- **Terminal**: Shows missing lines
- **HTML**: Open `htmlcov/index.html` in browser
- **XML**: `coverage.xml` for CI/CD

### Coverage Configuration

Coverage settings are in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["bot"]
branch = true
omit = [
    "*/tests/*",
    "*/migrations/*",
    "bot/__main__.py",
    "bot/cli.py",
]
```

### Excluding Code from Coverage

```python
def debug_function():  # pragma: no cover
    """This won't count against coverage."""
    pass

if TYPE_CHECKING:  # Automatically excluded
    from typing import Dict
```

## Best Practices

1. **Keep tests fast**: Use mocks for external services
2. **One assertion per test** (when possible)
3. **Test edge cases**: Empty inputs, invalid data, errors
4. **Use parametrize** for multiple similar test cases
5. **Clean up**: Use fixtures for setup/teardown

### Parametrize Example

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("World", "WORLD"),
    ("", ""),
])
def test_uppercase(input, expected):
    assert input.upper() == expected
```

## Troubleshooting

### Tests not discovered?

- Files must be named `test_*.py` or `*_test.py`
- Functions must start with `test_`
- Classes must start with `Test`

### Import errors?

Make sure you're running from the project root:

```bash
cd /Users/masonliang/supportbot/discord-support-bot
pytest
```

### Async tests failing?

Add `@pytest.mark.asyncio` decorator:

```python
@pytest.mark.asyncio
async def test_async():
    pass
```

## CI/CD

Tests run automatically on:
- Pull requests
- Pushes to main

See `.github/workflows/test.yml` for CI configuration.
