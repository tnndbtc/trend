# Testing Guide

## Overview

The Trend Intelligence Platform includes comprehensive test coverage across all layers, including unit tests, integration tests, and end-to-end tests.

## 📋 Test Structure

```
tests/
├── test_translation_services.py      # Translation provider tests (NEW)
├── test_ai_services.py                # AI service tests (NEW)
├── test_service_factory.py            # Service factory tests (NEW)
├── test_translation_api.py            # Translation API tests (NEW)
├── test_storage_unit.py               # Storage layer unit tests
├── test_storage_integration.py        # Storage integration tests
├── test_processing_pipeline.py        # Processing pipeline tests
├── test_ingestion_plugins.py          # Plugin system tests
├── test_celery_tasks.py               # Celery task tests
├── test_api_endpoints.py              # API endpoint tests
├── test_observability.py              # Monitoring tests
├── fixtures.py                        # Test fixtures and sample data
└── mocks/                             # Mock implementations
    ├── __init__.py
    ├── storage.py
    ├── processing.py
    └── intelligence.py
```

## 🧪 Test Categories

### 1. Unit Tests

**Purpose**: Test individual components in isolation

**Files**:
- `test_translation_services.py` - Translation providers (OpenAI, LibreTranslate, DeepL)
- `test_ai_services.py` - AI services (embeddings, LLM, search)
- `test_service_factory.py` - Service factory and DI
- `test_storage_unit.py` - Storage repositories

**Run**:
```bash
pytest tests/test_translation_services.py -v
pytest tests/test_ai_services.py -v
pytest tests/test_service_factory.py -v
```

### 2. Integration Tests

**Purpose**: Test component interactions with real dependencies

**Files**:
- `test_translation_api.py` - Translation API endpoints
- `test_storage_integration.py` - Database operations
- `test_api_endpoints.py` - All API endpoints

**Prerequisites**:
- Docker services running (PostgreSQL, Redis, Qdrant)
- Environment variables configured

**Run**:
```bash
# Start services first
docker compose up -d

# Run integration tests
pytest tests/test_translation_api.py -v
pytest tests/test_storage_integration.py -v
```

### 3. End-to-End Tests

**Purpose**: Test complete workflows

**Files**:
- `test_processing_pipeline.py` - Full pipeline execution
- `test_celery_tasks.py` - Task execution
- `scripts/test_integration_flow.py` - Manual E2E test

**Run**:
```bash
# Run pipeline tests
pytest tests/test_processing_pipeline.py -v

# Run manual E2E test
python scripts/test_integration_flow.py
```

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=trend_agent --cov-report=html

# Run specific test file
pytest tests/test_translation_services.py -v

# Run specific test class
pytest tests/test_translation_services.py::TestTranslationCache -v

# Run specific test
pytest tests/test_translation_services.py::TestTranslationCache::test_cache_get_hit -v
```

### Run by Category

```bash
# Translation tests only
pytest tests/test_translation_services.py tests/test_translation_api.py -v

# AI services tests only
pytest tests/test_ai_services.py tests/test_service_factory.py -v

# All new Session 7 tests
pytest tests/test_translation_services.py tests/test_ai_services.py \
       tests/test_service_factory.py tests/test_translation_api.py -v
```

### Run with Different Verbosity

```bash
# Minimal output
pytest tests/ -q

# Standard output
pytest tests/ -v

# Very verbose (show all output)
pytest tests/ -vv -s
```

### Run with Markers

```bash
# Run only async tests
pytest tests/ -m asyncio

# Skip slow tests
pytest tests/ -m "not slow"
```

## 🛠️ Test Configuration

### Environment Variables

```bash
# AI Services
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Translation
export LIBRETRANSLATE_HOST=http://localhost:5000
export DEEPL_API_KEY=your-key

# Database
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_DB=trends
export POSTGRES_USER=trend_user
export POSTGRES_PASSWORD=trend_password

# Redis
export REDIS_HOST=localhost
export REDIS_PORT=6380

# Qdrant
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
```

### pytest.ini

```ini
[tool:pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --tb=short
markers =
    asyncio: async tests
    slow: slow running tests
    integration: integration tests
    unit: unit tests
```

## 📝 Writing Tests

### Test Template

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
class TestYourComponent:
    """Tests for YourComponent."""

    async def test_basic_functionality(self):
        """Test basic functionality."""
        # Arrange
        component = YourComponent()

        # Act
        result = await component.do_something()

        # Assert
        assert result is not None

    async def test_with_mocks(self):
        """Test with mocked dependencies."""
        # Arrange
        mock_service = MagicMock()
        mock_service.method = AsyncMock(return_value="mocked")
        component = YourComponent(service=mock_service)

        # Act
        result = await component.do_something()

        # Assert
        assert result == "mocked"
        assert mock_service.method.called
```

### Testing Async Code

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Using Fixtures

```python
import pytest

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

def test_with_fixture(sample_data):
    """Test using fixture."""
    assert sample_data["key"] == "value"
```

### Mocking External Services

```python
from unittest.mock import patch, AsyncMock

@patch("openai.AsyncOpenAI")
async def test_with_mocked_openai(mock_openai_class):
    """Test with mocked OpenAI client."""
    # Setup mock
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(
        return_value=MagicMock(data=[MagicMock(embedding=[0.1]*1536)])
    )
    mock_openai_class.return_value = mock_client

    # Test
    service = OpenAIEmbeddingService(api_key="test")
    result = await service.embed("test")

    assert len(result) == 1536
```

## 📊 Coverage

### Generate Coverage Report

```bash
# Run with coverage
pytest tests/ --cov=trend_agent --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Goals

- **Overall**: >80% coverage
- **Critical paths**: >90% coverage
- **New features**: 100% coverage

## 🐛 Debugging Tests

### Run with Debug Output

```bash
# Show all output (including print statements)
pytest tests/test_translation_services.py -v -s

# Show full traceback
pytest tests/test_translation_services.py -v --tb=long

# Stop on first failure
pytest tests/test_translation_services.py -x

# Drop into debugger on failure
pytest tests/test_translation_services.py --pdb
```

### Using Logging in Tests

```python
import logging

def test_with_logging(caplog):
    """Test with log capture."""
    with caplog.at_level(logging.INFO):
        # Your test code
        pass

    assert "Expected log message" in caplog.text
```

## 🔍 Test Examples

### Translation Services Test

```python
@pytest.mark.asyncio
async def test_translation_with_cache():
    """Test translation with caching."""
    mock_redis = MockRedisCache()
    cache = TranslationCache(redis_repository=mock_redis)
    provider = MockTranslationService(name="test")

    manager = TranslationManager(
        providers={"test": provider},
        cache=cache,
    )

    # First call - cache miss
    result1 = await manager.translate("Hello", "es", "en")
    assert provider.call_count == 1

    # Second call - cache hit
    result2 = await manager.translate("Hello", "es", "en")
    assert provider.call_count == 1  # Not incremented
    assert result1 == result2
```

### AI Services Test

```python
@patch("openai.AsyncOpenAI")
async def test_embedding_service(mock_openai_class):
    """Test embedding service."""
    # Setup mock
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1]*1536)]
    mock_response.usage = MagicMock(total_tokens=100)
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_openai_class.return_value = mock_client

    # Test
    service = OpenAIEmbeddingService(api_key="test-key")
    result = await service.embed("test text")

    assert len(result) == 1536
    assert mock_client.embeddings.create.called
```

### API Test

```python
def test_translation_endpoint(client, mock_translation_manager):
    """Test translation API endpoint."""
    response = client.post(
        "/api/v1/translation/translate",
        json={
            "text": "Hello",
            "target_language": "es",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "translated_text" in data
```

## 📚 Best Practices

### 1. Test Independence

✅ **Good**: Each test is independent
```python
def test_feature_a():
    data = create_test_data()
    # Test feature A

def test_feature_b():
    data = create_test_data()
    # Test feature B
```

❌ **Bad**: Tests depend on each other
```python
shared_data = None

def test_setup():
    global shared_data
    shared_data = create_test_data()

def test_feature():
    # Relies on test_setup running first
    assert shared_data is not None
```

### 2. Clear Test Names

✅ **Good**: Descriptive names
```python
def test_translation_returns_cached_result_when_available():
    pass

def test_translation_calls_provider_on_cache_miss():
    pass
```

❌ **Bad**: Unclear names
```python
def test_1():
    pass

def test_cache():
    pass
```

### 3. Arrange-Act-Assert

```python
async def test_translation():
    # Arrange
    manager = create_translation_manager()
    text = "Hello"

    # Act
    result = await manager.translate(text, "es")

    # Assert
    assert result is not None
    assert isinstance(result, str)
```

### 4. Mock External Dependencies

```python
# Mock API calls
@patch("openai.AsyncOpenAI")
async def test_with_mocked_api(mock_client):
    # Test without making real API calls
    pass

# Mock database
@patch("trend_agent.storage.postgres.PostgreSQLTrendRepository")
async def test_with_mocked_db(mock_repo):
    # Test without database
    pass
```

### 5. Test Error Conditions

```python
async def test_handles_api_error_gracefully():
    """Test error handling."""
    mock_service = MagicMock()
    mock_service.translate = AsyncMock(
        side_effect=Exception("API Error")
    )

    manager = TranslationManager(providers={"mock": mock_service})

    with pytest.raises(Exception, match="API Error"):
        await manager.translate("text", "es")
```

## 🎯 Test Metrics

### Current Test Coverage

| Component | Test File | Tests | Coverage |
|-----------|-----------|-------|----------|
| Translation Services | test_translation_services.py | 25+ | ~90% |
| AI Services | test_ai_services.py | 20+ | ~85% |
| Service Factory | test_service_factory.py | 15+ | ~90% |
| Translation API | test_translation_api.py | 15+ | ~95% |
| **New Tests Total** | **4 files** | **75+** | **~90%** |

### Test Execution Time

- **Unit tests**: <1 second each
- **Integration tests**: 1-5 seconds each
- **E2E tests**: 10-30 seconds
- **Full suite**: ~2-5 minutes

## 🔧 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_PASSWORD: test
      redis:
        image: redis:7-alpine
      qdrant:
        image: qdrant/qdrant:latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run tests
        run: pytest tests/ --cov=trend_agent --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 📖 Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)

## 🆘 Troubleshooting

### Common Issues

**Issue**: ModuleNotFoundError
```bash
# Solution: Ensure PYTHONPATH is set
export PYTHONPATH=/path/to/trend:$PYTHONPATH
```

**Issue**: Database connection errors
```bash
# Solution: Start Docker services
docker compose up -d postgres redis qdrant
```

**Issue**: Tests hang
```bash
# Solution: Check for unclosed async resources
# Ensure all services use context managers
async with ServiceFactory() as factory:
    # Test code
```

**Issue**: Slow tests
```bash
# Solution: Use mocks for external services
@patch("openai.AsyncOpenAI")
async def test_fast(mock_client):
    # Fast test with mocked API
```

## ✅ Test Checklist

Before submitting code:

- [ ] All new code has tests
- [ ] Tests pass locally
- [ ] Coverage is maintained (>80%)
- [ ] No flaky tests
- [ ] External APIs are mocked
- [ ] Tests are independent
- [ ] Error cases are tested
- [ ] Documentation is updated
