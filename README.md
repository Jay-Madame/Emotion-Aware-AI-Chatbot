# Emotion-Aware AI Chatbot Backend Setup

Follow these steps to set up the virtual environment for the backend:

## 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Emotion-Aware-AI-Chatbot
```

## 2. Create a Virtual Environment

```bash
python3 -m venv backend_venv
```

## 3. Activate the Virtual Environment

**For macOS/Linux:**
```bash
source backend_venv/bin/activate
```

**For Windows:**
```bash
backend_venv\Scripts\activate
```

## 4. Install Dependencies

```bash
pip install -r docs/backend_requirements.txt
```

## 5. Integration with Backend API and Frontend web server

```bash
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A `.env` file in the project root
In Project root as well, to build the stack:
docker compose up --build

Open the fronten at:  http://localhost:8090
When ctrl - c to end operation also:
docker compose down
```
