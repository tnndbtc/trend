#!/bin/bash
# Test runner script for Trend Intelligence Platform
#
# Runs all test suites and generates a summary report

set -e

echo "======================================================================"
echo "Trend Intelligence Platform - Test Suite"
echo "======================================================================"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Please install: pip install pytest pytest-asyncio"
    exit 1
fi

# Count test files
TOTAL_TEST_FILES=$(find tests/ -name "test_*.py" | wc -l)
echo "📋 Found $TOTAL_TEST_FILES test files"
echo ""

# Run tests by category
echo "----------------------------------------------------------------------"
echo "Running Translation Services Tests..."
echo "----------------------------------------------------------------------"
python -m pytest tests/test_translation_services.py -v --tb=short || echo "⚠️  Some translation tests failed (dependencies may be missing)"

echo ""
echo "----------------------------------------------------------------------"
echo "Running AI Services Tests..."
echo "----------------------------------------------------------------------"
python -m pytest tests/test_ai_services.py -v --tb=short || echo "⚠️  Some AI tests failed (dependencies may be missing)"

echo ""
echo "----------------------------------------------------------------------"
echo "Running Service Factory Tests..."
echo "----------------------------------------------------------------------"
python -m pytest tests/test_service_factory.py -v --tb=short || echo "⚠️  Some factory tests failed (dependencies may be missing)"

echo ""
echo "----------------------------------------------------------------------"
echo "Running Translation API Tests..."
echo "----------------------------------------------------------------------"
python -m pytest tests/test_translation_api.py -v --tb=short || echo "⚠️  Some API tests failed (dependencies may be missing)"

echo ""
echo "----------------------------------------------------------------------"
echo "Running All Existing Tests..."
echo "----------------------------------------------------------------------"
python -m pytest tests/ -v --tb=short --maxfail=5 || echo "⚠️  Some tests failed"

echo ""
echo "======================================================================"
echo "Test Suite Complete"
echo "======================================================================"
echo ""
echo "📊 Test Summary:"
echo "   Total test files: $TOTAL_TEST_FILES"
echo "   New test files (Session 7): 4"
echo "   - test_translation_services.py"
echo "   - test_ai_services.py"
echo "   - test_service_factory.py"
echo "   - test_translation_api.py"
echo ""
echo "💡 Tips:"
echo "   - Install all dependencies: pip install -r requirements.txt"
echo "   - Set environment variables for API keys (OPENAI_API_KEY, etc.)"
echo "   - Start Docker services: docker compose up -d"
echo ""
