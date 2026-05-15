#!/usr/bin/env bash
set -e


python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip

echo "Setup complete. Activate your environment with:"
echo "source .venv/bin/activate"
