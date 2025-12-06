from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
import os

# 1. Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


if not GOOGLE_API_KEY:
    raise EnvironmentError("Missing GOOGLE_API_KEY in .env")

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# 2. VADER-based sentiment analyzer
class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def analyze(self, text: str) -> dict:
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']
        
        # Determine sentiment
        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Determine severity based on compound score
        severity = "normal"
        if sentiment == "negative":
            if compound <= -0.75:  # Changed from -0.5 (severe threshold)
                severity = "severe"
            elif compound <= -0.4:  # Changed from -0.2 (moderate threshold)
                severity = "moderate"

        return {
            "sentiment": sentiment, 
            "severity": severity,
            "score": compound
        }

# 3. Mental-health keyword detector
def check_mental_health_concerns(user_input: str) -> str:
    """Check for crisis or serious mental health keywords"""
    crisis_keywords = [
        "suicide", "suicidal", "kill myself", "end my life", "want to die",
        "self harm", "self-harm", "cut myself", "hurt myself",
        "no reason to live", "better off dead", "can't go on"
    ]

    serious_keywords = [
        "depressed", "depression", "anxious", "anxiety", "panic attack",
        "can't cope", "overwhelmed", "hopeless", "worthless",
        "hate myself", "severe anxiety", "mental breakdown"
    ]

    user_lower = user_input.lower()
    if any(k in user_lower for k in crisis_keywords):
        return "crisis"
    if any(k in user_lower for k in serious_keywords):
        return "serious"
    return "none"

# 4. Initialize sentiment analyzer
sentiment_analyzer = SentimentAnalyzer()

# 5. Models for routed responses
#positive_model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
positive_model = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.7)
negative_model = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.5)
neutral_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)

# 6. Response templates
positive_prompt = PromptTemplate(
    input_variables=["user_input"],
    template=(
        "The user seems happy! Respond enthusiastically and build on their positive energy.\n"
        "Keep your answer concise: at most 4–6 short sentences. Avoid long lists unless the user explicitly asks.\n\n"
        "User: {user_input}\n\nResponse:"
    ),
)

negative_prompt = PromptTemplate(
    input_variables=["user_input"],
    template=(
        "The user seems upset. Respond with empathy and try to help solve their problem.\n"
        "Be supportive but practical, and keep your answer concise: at most 4–6 short sentences.\n"
        "Avoid over-explaining unless the user asks for more detail.\n\n"
        "User: {user_input}\n\nResponse:"
    ),
)

neutral_prompt = PromptTemplate(
    input_variables=["user_input"],
    template=(
        "Respond to the user's query in a helpful, informative way.\n"
        "Keep it focused and concise: at most 4–6 short sentences unless they request a deep dive.\n\n"
        "User: {user_input}\n\nResponse:"
    ),
)


# 7. Mental health response template
MENTAL_HEALTH_RESPONSE = """I hear that you're going through a difficult time. 
I'm an AI and not a certified mental health professional, so I encourage you to reach out to a qualified specialist who can provide proper support.

If you need immediate help:
• 988 Suicide & Crisis Lifeline: Call or text 988 (24/7)
• Crisis Text Line: Text HOME to 741741

You don't have to go through this alone. Reaching out is a sign of strength."""

# 8. Main routing function
def route_by_sentiment(user_input: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    """
    Main entry point for the chatbot to process user input and return a response.
    Used by chat.py and can be used by frontend applications.
    """
    # Step 1: Check for mental health crisis keywords first
    mental_health_level = check_mental_health_concerns(user_input)
    if mental_health_level in ["crisis", "serious"]:
        print(f"Mental health concern detected: {mental_health_level}")
        return MENTAL_HEALTH_RESPONSE

    # Step 2: Analyze sentiment using VADER
    analysis = sentiment_analyzer.analyze(user_input)
    sentiment = analysis["sentiment"]
    severity = analysis["severity"]
    score = analysis["score"]

    print(f"Detected sentiment: {sentiment} (severity: {severity}, score: {score:.2f})")

    # Step 3: Only trigger mental health response if BOTH severe AND contains concerning language
    # This prevents false positives like "I did bad on my exam"
    if severity == "severe" and sentiment == "negative" and mental_health_level == "serious":
        print("Severe emotional distress detected - providing mental health resources")
        return MENTAL_HEALTH_RESPONSE

    # Step 4: Route to appropriate model based on sentiment
    if sentiment == "positive":
        chain = positive_prompt | positive_model
    elif sentiment == "negative":
        chain = negative_prompt | negative_model
    else:
        chain = neutral_prompt | neutral_model

    # Step 5: Generate and return response
    response = chain.invoke({"user_input": user_input})
    
    # Return the content string (not the response object)
    return response.content