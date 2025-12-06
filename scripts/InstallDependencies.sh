#!/bin/bash
source .venv/bin/activate

pip install --upgrade pip
pip install -r docs/backend_requirements.txt
pip install pytest
pip install google-genai google-api-core python-dotenv groq