from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from langgraph.graph import StateGraph
from typing import TypedDict, Optional
import os
from dotenv import load_dotenv

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TutorState(TypedDict):
    user_messages: list[str]
    system_messages: list[str]
    level: Optional[str]
    num_questions_asked: int

def greet_node(state: TutorState) -> TutorState:
    state["system_messages"].append("Hello! Let's have a short chat so I can understand your English level. How are you today?")
    return state

def ask_node(state: TutorState) -> TutorState:
    questions = [
        "Can you tell me a little bit about your day?",
        "Why are you learning English?",
        "What do you find most difficult about learning English?"
    ]
    idx = state["num_questions_asked"]
    if idx < len(questions):
        state["system_messages"].append(questions[idx])
        state["num_questions_asked"] += 1
    return state

def assess_node(state: TutorState) -> TutorState:
    conversation = "\n".join(f"User: {u}\nAI: {s}" for u, s in zip(state["user_messages"], state["system_messages"][1:]))
    prompt = f"""
You are an expert English teacher. Based on the following conversation with a student, determine their CEFR level (A1 to C2).

Conversation:
{conversation}

Only respond with the CEFR level (e.g., A2, B1, C1).
"""
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    state["level"] = response.choices[0].message.content.strip()
    return state

builder = StateGraph(TutorState)
builder.add_node("greet", greet_node)
builder.add_node("ask", ask_node)
builder.add_node("assess", assess_node)

builder.set_entry_point("greet")
builder.add_edge("greet", "ask")
builder.add_conditional_edges(
    "ask", 
    lambda s: "assess" if s["num_questions_asked"] >= 3 else "ask"
)
builder.set_finish_point("assess")

graph = builder.compile()

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_msg = data.get("message")
    state = data.get("state")

    if state is None:
        state = {
            "user_messages": [],
            "system_messages": [],
            "level": None,
            "num_questions_asked": 0
        }
        return graph.invoke(state)

    if user_msg:
        state["user_messages"].append(user_msg)

    updated_state = graph.invoke(state)
    return updated_state
