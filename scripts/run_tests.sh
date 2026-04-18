#!/bin/bash
# scripts/run_tests.sh

set -e

echo "=== Running Backend Tests ==="
cd backend
pip install -q pytest pytest-asyncio pytest-cov httpx aiosqlite
pytest tests/ -v --tb=short --cov=backend --cov-report=term-missing

echo ""
echo "=== Running Frontend Build ==="
cd ../frontend
npm run build

echo ""
echo "=== All tests passed ==="