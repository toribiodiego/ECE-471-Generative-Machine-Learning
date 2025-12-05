#!/usr/bin/env bash
# Automates: virtual environment creation, dependency installation, and .env scaffolding

echo "Creating Python virtual environment..."
python3.12 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing required Python packages..."
pip install -r requirements.txt

echo "Generating .env file template..."
cat <<EOF > .env
# Google Gemini API key
GEMINI_API_KEY=
EOF

echo ".env file created at $(pwd)/.env"
echo "Please open .env and fill in your API credential."