#!/bin/bash
set -e

echo "🔍 Verifying rateMyCode Installation (v2.0 - Audit Fixes applied)..."

# 1. Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 2. Activate venv
source venv/bin/activate

# 3. Install package
echo "Installing package..."
pip install .

# 4. Run Tests
echo "Running Unit Tests..."
python -m unittest discover tests

echo "✅ Verification Complete! You can now run 'ratemycode' to start the tool."
