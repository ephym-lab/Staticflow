#!/usr/bin/env bash
set -e

echo "Setting up StaticFlow development environment..."

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install package in editable mode with test dependencies
pip install --upgrade pip
pip install -e ".[test]"

echo ""
echo "Setup complete. To start developing, activate your environment:"
echo "source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "pytest tests/"
