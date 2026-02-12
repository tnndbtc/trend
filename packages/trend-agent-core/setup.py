"""
Setup script for Trend Agent Core - Shared library for Trend Intelligence Platform.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="trend-agent-core",
    version="1.0.0",
    description="Core shared library for the Trend Intelligence Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Trend Intelligence Team",
    author_email="dev@trendintelligence.example.com",
    url="https://github.com/yourusername/trend-intelligence-platform",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        # Database drivers
        "asyncpg>=0.29.0",
        "redis>=5.0.0",
        "qdrant-client>=1.7.0",

        # Data processing
        "numpy>=1.24.0",
        "scikit-learn>=1.3.0",
        "hdbscan>=0.8.33",

        # NLP and text processing
        "langdetect>=1.0.9",

        # AI/LLM APIs
        "openai>=1.12.0",

        # HTTP client
        "aiohttp>=3.9.0",

        # Data validation
        "pydantic>=2.5.0",

        # Monitoring and observability
        "prometheus-client>=0.19.0",
        "opentelemetry-api>=1.21.0",
        "opentelemetry-sdk>=1.21.0",
        "opentelemetry-exporter-otlp-proto-http>=1.21.0",

        # Utilities
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "mypy>=1.7.0",
            "ruff>=0.1.8",
        ],
        "storage": [
            "influxdb-client>=1.38.0",
            "aio-pika>=9.3.0",
            "aioboto3>=12.1.0",
        ],
        "instrumentation": [
            "opentelemetry-instrumentation-aiohttp-client>=0.42b0",
            "opentelemetry-instrumentation-redis>=0.42b0",
            "opentelemetry-instrumentation-asyncpg>=0.42b0",
            "psutil>=5.9.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Text Processing :: Linguistic",
    ],
    include_package_data=True,
    zip_safe=False,
)
