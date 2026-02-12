"""
Setup script for Trend Agent Collectors - Collector plugins for data sources.
"""

from setuptools import setup, find_packages

setup(
    name="trend-agent-collectors",
    version="1.0.0",
    description="Collector plugins for the Trend Intelligence Platform",
    author="Trend Intelligence Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "aiohttp>=3.9.0",
        "pytrends>=4.9.0",
        "feedparser>=6.0.10",
        "beautifulsoup4>=4.12.0",
        "trafilatura>=1.6.0",
        "langdetect>=1.0.9",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
)
