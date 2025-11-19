# Use a lightweight Python image
FROM python:3.13-slim

# Set working directory in the container
WORKDIR /app

# Environment settings: no .pyc, unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install build tools if needed (you can drop this if your deps are pure Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (better Docker build cache)
COPY docs/backend_requirements.txt /app/backend_requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend_requirements.txt

# Now copy the rest of the project
COPY src/ /app/src
COPY chat_ui/ /app/chat_ui
COPY README.md /app/README.md

# If you want tests available in the image (optional)
# COPY tests/ /app/tests

# Expose the port Uvicorn will listen on
EXPOSE 8000

# Default command to run the FastAPI app with Uvicorn
# Adjust "src.server:app" if your app is in a different module.
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
