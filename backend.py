from fastapi import FastAPI
from groq import Groq
from dotenv import load_dotenv
import os
import random
from pydantic import BaseModel

load_dotenv()

app = FastAPI()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

state = {
    "child_mode": "Neutral",
    "brightness_threshold": 50,
    "noise_threshold": 40,
    "brightness": 40,
    "noise": 25
}

SYSTEM_PROMPT = (
    "You are a calm, empathetic NeuroLens companion. "
    "Keep responses brief (1-2 sentences), reassuring, and offer one simple coping strategy or question."
)


class ChatRequest(BaseModel):
    message: str | None = None


class StudyRequest(BaseModel):
    text: str | None = None


class StudyChatRequest(BaseModel):
    question: str | None = None
    text: str | None = None


def generate_local_reply(message: str) -> str:
    m = (message or "").lower()
    if any(k in m for k in ("sad", "upset", "unhappy", "depressed")):
        return random.choice([
            "I'm sorry you're feeling sad. Would you like a breathing exercise?",
            "That sounds hard. Try taking a slow breath in and out."
        ])
    if any(k in m for k in ("angry", "mad", "annoyed")):
        return random.choice([
            "It's okay to feel angry. Try counting to ten slowly.",
            "I hear your frustration — a short walk might help."
        ])
    if any(k in m for k in ("scared", "afraid", "nervous", "anxious")):
        return random.choice([
            "I'm here with you. Try placing your hand over your heart and breathe.",
            "You're safe here. Take a deep breath with me."
        ])
    if any(k in m for k in ("happy", "great", "good")):
        return random.choice([
            "That's wonderful — enjoy the feeling!",
            "So glad to hear that — keep smiling!"
        ])
    return random.choice([
        "I hear you. Would you like a short breathing exercise?",
        "Thanks for sharing — try taking three slow breaths.",
        "I'm here for you. Want a calming activity suggestion?"
    ])

def extract_key_points_locally(text: str, max_points: int = 5) -> list[str]:
    cleaned = (text or "").replace("\n", " ").strip()
    if not cleaned:
        return []

    raw_sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
    if not raw_sentences:
        return []

    keywords = ("important", "key", "must", "should", "therefore", "because", "definition")
    scored = []
    for sentence in raw_sentences:
        score = 0
        lower = sentence.lower()
        if any(k in lower for k in keywords):
            score += 2
        score += min(len(sentence) // 80, 2)
        scored.append((score, sentence))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [s for _, s in scored[:max_points]]
    if not selected:
        selected = raw_sentences[:max_points]
    return [p[:220] + ("..." if len(p) > 220 else "") for p in selected]


def study_fallback_answer(question: str, text: str) -> str:
    q = (question or "").lower()
    points = extract_key_points_locally(text, max_points=4)
    if "summar" in q:
        if points:
            return "Quick summary:\n- " + "\n- ".join(points)
        return "I need more study material to summarize. Please upload a document or paste text."
    if "explain" in q:
        if points:
            return f"Here is a simple explanation based on your material: {points[0]}"
        return "Share the topic text and I can explain it step by step."
    if points:
        return "From your material, focus on these points:\n- " + "\n- ".join(points[:3])
    return "Upload or paste study text and ask me to summarize, explain, or quiz you."


def generate_environment():

    base_brightness = random.randint(35, 75)
    base_noise = random.randint(20, 60)

    if state["child_mode"] == "Calm":
        brightness = base_brightness - 20
        noise = base_noise - 20

    elif state["child_mode"] == "Focus":
        brightness = min(65, base_brightness)
        noise = base_noise - 10

    else:
        brightness = base_brightness
        noise = base_noise

    state["brightness"] = max(10, brightness)
    state["noise"] = max(10, noise)


@app.post("/detect-thresholds")
def detect_thresholds():
    # Mock detection: pick thresholds based on current child mode and vary readings
    mode = state.get("child_mode", "Neutral")
    base_b = state.get("brightness", 50)
    base_n = state.get("noise", 40)

    if mode == "Calm":
        b = max(10, base_b - random.randint(10, 20))
        n = max(10, base_n - random.randint(5, 15))
    elif mode == "Focus":
        b = min(85, base_b + random.randint(0, 10))
        n = max(10, base_n - random.randint(5, 10))
    else:
        b = max(10, base_b - random.randint(0, 10))
        n = max(10, base_n - random.randint(0, 5))

    state["brightness_threshold"] = b
    state["noise_threshold"] = n

    # Simulate current sensor readings that vary around thresholds
    state["brightness"] = min(100, b + random.randint(-5, 15))
    state["noise"] = max(0, n + random.randint(-5, 10))

    return {"brightness": b, "noise": n}


@app.get("/thresholds")
def get_thresholds():
    return {
        "brightness": state.get("brightness_threshold", 50),
        "noise": state.get("noise_threshold", 40),
    }


@app.post("/set-environment")
def set_environment(brightness: int, noise: int):
    state["brightness"] = brightness
    state["noise"] = noise
    return {"status": "environment updated"}

@app.post("/set-child-mode")
def set_child_mode(mode: str):
    state["child_mode"] = mode
    return {"child_mode": mode}

@app.post("/set-thresholds")
def set_thresholds(brightness: int, noise: int):
    state["brightness_threshold"] = brightness
    state["noise_threshold"] = noise
    return {"status": "thresholds updated"}

@app.post("/auto-adjust")
def auto_adjust():
    # Actively reduce environment values to slightly below thresholds for comfort
    bt = state.get("brightness_threshold", 50)
    nt = state.get("noise_threshold", 40)

    # target values: a small margin below threshold
    target_b = max(10, bt - 5)
    target_n = max(10, nt - 3)

    state["brightness"] = min(state.get("brightness", target_b), target_b)
    state["noise"] = min(state.get("noise", target_n), target_n)

    return {
        "status": "adjusted",
        "brightness": state["brightness"],
        "noise": state["noise"]
    }

@app.get("/state")
def get_state():

    generate_environment()

    exceeded = (
        state["brightness"] > state["brightness_threshold"] or
        state["noise"] > state["noise_threshold"]
    )

    return {
        "brightness": state["brightness"],
        "noise": state["noise"],
        "brightness_threshold": state["brightness_threshold"],
        "noise_threshold": state["noise_threshold"],
        "child_mode": state["child_mode"],
        "exceeded": exceeded
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.post("/chat")
async def chat(payload: ChatRequest | None = None, message: str | None = None):
    # Accept message as query param or JSON body {"message": "..."}
    body_message = (payload.message if payload else None)
    final_message = (message or body_message or "").strip()

    if not final_message:
        return {"reply": "I didn't receive a message."}

    try:
        if client is None:
            raise RuntimeError("GROQ_API_KEY is not configured")

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": final_message}
            ]
        )
        reply = completion.choices[0].message.content

        if not reply or not reply.strip():
            reply = generate_local_reply(final_message)

    except Exception:
        # Use local fallback generator so responses vary and are helpful offline
        reply = generate_local_reply(final_message)

    return {"reply": reply}


@app.post("/study/highlights")
async def study_highlights(payload: StudyRequest):
    text = (payload.text or "").strip()
    if not text:
        return {"highlights": [], "message": "No study text provided."}

    local_points = extract_key_points_locally(text)

    try:
        if client is None:
            raise RuntimeError("GROQ_API_KEY is not configured")
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Extract the 5 most important study points as short bullet lines."
                },
                {"role": "user", "content": text[:8000]},
            ],
        )
        reply = (completion.choices[0].message.content or "").strip()
        ai_points = [p.strip("- ").strip() for p in reply.splitlines() if p.strip()][:5]
        points = ai_points or local_points
    except Exception:
        points = local_points

    return {"highlights": points}


@app.post("/study/chat")
async def study_chat(payload: StudyChatRequest):
    question = (payload.question or "").strip()
    study_text = (payload.text or "").strip()

    if not question:
        return {"reply": "Please ask a study question."}

    try:
        if client is None:
            raise RuntimeError("GROQ_API_KEY is not configured")

        context = study_text[:12000] if study_text else ""
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a patient study assistant for children. "
                        "Explain clearly, keep structure simple, and stay grounded in provided material."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Study Material:\n{context}\n\n"
                        f"Question: {question}\n\n"
                        "If material is missing for the answer, say what is missing."
                    ),
                },
            ],
        )
        reply = (completion.choices[0].message.content or "").strip()
        if not reply:
            reply = study_fallback_answer(question, study_text)
    except Exception:
        reply = study_fallback_answer(question, study_text)

    return {"reply": reply}
