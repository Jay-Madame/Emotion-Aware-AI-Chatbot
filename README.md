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

## 5. Run the front end integration with Backend API

```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload
In another Terminal
python -m http.server 5173

```
