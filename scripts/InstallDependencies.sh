#!/bin/bash
python -m pip install --upgrade pip
pip install -r docs/backend_requirements.txt
pip install google-genai google-api-core python-dotenv pytest groq
pip install fastapi uvicorn "python-multipart[standard]"
