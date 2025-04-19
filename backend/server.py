import io, os, json, uuid, logging, re
from typing import TypedDict, List

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import openai

# LangGraph
from langgraph.graph import StateGraph, END

# ═══ 0. ENV / CONSTANTS ═══════════════════════════════════════════════
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

ASR_MODEL      = "whisper-1"
LLM_PRIMARY    = "gpt-4o-mini"
LLM_FALLBACK   = "gpt-3.5-turbo-0125"   # 0125 supports JSON mode
TTS_MODEL      = "tts-1"
TTS_VOICE      = "alloy"

GREETING = (
    "Hello! I'm your AI English tutor. I'd like to ask you a few questions "
    "to understand your current English level.\n\n"
    "First question: Could you tell me a little about yourself?"
)

# ═══ 1. FastAPI boilerplate ═══════════════════════════════════════════
app = FastAPI(title="AI‑Tutor (English, robust JSON)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ═══ 2. Speech endpoints (Whisper locked to English) ══════════════════
@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    raw = await audio.read()
    buf = io.BytesIO(raw); buf.name = "speech.webm"
    out = openai.audio.transcriptions.create(
        model=ASR_MODEL,
        file=buf,
        response_format="json",
        language="en"
    )
    return {"text": out.text}

@app.post("/speak")
async def speak(request: Request):
    text = (await request.body()).decode()
    wav = openai.audio.speech.create(
        model=TTS_MODEL,
        voice=TTS_VOICE,
        input=text,
        response_format="wav",
    )
    return StreamingResponse(io.BytesIO(wav.content), media_type="audio/wav")

# ═══ 3. Helpers ═══════════════════════════════════════════════════════
class Memory(TypedDict):
    messages: List[dict]
    turns: int
    done: bool
    level: str | None

def llm_text(messages, system) -> str:
    base = [{"role": "system", "content": system}]
    for model in (LLM_PRIMARY, LLM_FALLBACK):
        try:
            r = openai.chat.completions.create(
                model=model,
                messages=base + messages,
                temperature=0.3
            )
            return r.choices[0].message.content
        except Exception as e:
            logging.warning("%s failed → %s", model, e)
    raise RuntimeError("Both models failed")

def llm_json(messages, system) -> dict:
    """
    Ask model in enforced JSON mode. One retry in plain mode + regex fallback.
    """
    base = [{"role": "system", "content": system}]
    # 1st attempt: JSON mode
    for model in (LLM_PRIMARY, LLM_FALLBACK):
        try:
            r = openai.chat.completions.create(
                model=model,
                messages=base + messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
            return json.loads(r.choices[0].message.content)
        except Exception as e:
            logging.warning("%s JSON mode failed → %s", model, e)

    # fallback: plain text, then regex
    raw = llm_text(messages, system + " Respond ONLY with JSON.")
    m = re.search(r'\{.*\}', raw, flags=re.S)
    if m:
        return json.loads(m.group())
    raise RuntimeError("Could not parse JSON from model output")

def meaningful(text: str, min_letters=3) -> bool:
    return len(re.findall(r"[A-Za-z]", text)) >= min_letters

# ═══ 4. LangGraph nodes (single‑step per request) ═════════════════════
def next_step(state: Memory) -> Memory:
    if state["turns"] < 3:
        prompt = (
            "You are assessing a student's English. "
            "Ask ONE open question that explores their grammar/vocabulary. "
            "Do NOT reveal any level yet."
        )
        reply = llm_text(state["messages"][-6:], system=prompt)
        state["messages"].append({"role": "assistant", "content": reply})
        return state

    # -------- assessment --------
    prompt = (
        "Determine the CEFR level (A1,A2,B1,B2,C1,C2) from the conversation. "
        "Return JSON: {\"level\":\"<level>\",\"rationale\":\"<sentence>\"}"
    )
    res = llm_json(state["messages"], system=prompt)
    final = f"Thank you! Based on our chat, I’d place you at **{res['level']}**. {res['rationale']}"
    state["messages"].append({"role": "assistant", "content": final})
    state["done"] = True
    state["level"] = res["level"]
    return state

graph = StateGraph(Memory)
graph.add_node("next", next_step)
graph.set_entry_point("next")
graph.add_edge("next", END)
compiled = graph.compile()

# ═══ 5. Session manager ═══════════════════════════════════════════════
_sessions: dict[str, Memory] = {}

def run(sid: str, user_text: str | None = None):
    st = _sessions.get(sid) or {"messages": [], "turns": 0, "done": False, "level": None}

    if user_text is None:                   # first call → greeting
        if not st["messages"]:
            st["messages"].append({"role": "assistant", "content": GREETING})
            _sessions[sid] = st
        return st["messages"][-1]["content"], st["done"]

    if not meaningful(user_text):
        reply = "I didn’t quite catch that — could you say it again in English?"
        st["messages"].append({"role": "assistant", "content": reply})
        _sessions[sid] = st
        return reply, False

    st["messages"].append({"role": "user", "content": user_text})
    st["turns"] += 1

    new_st = compiled.invoke(st)
    _sessions[sid] = new_st
    return new_st["messages"][-1]["content"], new_st["done"]

# ═══ 6. REST endpoints for front‑end ══════════════════════════════════
@app.post("/start")
async def start():
    sid = uuid.uuid4().hex
    reply, _ = run(sid)
    return {"session": sid, "reply": reply}

class ChatIn(TypedDict):
    session: str
    transcript: str

@app.post("/chat")
async def chat(data: ChatIn):
    sid, text = data["session"], data["transcript"]
    if sid not in _sessions:
        raise HTTPException(404, "session not found")
    reply, done = run(sid, text)
    return {"reply": reply, "done": done}
