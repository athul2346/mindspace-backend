from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import get_db, engine
from models import Base, Session as DBSession, Message, MoodLog, JournalEntry
from groq import Groq
import os
import re
from datetime import datetime

load_dotenv()

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://mindspace-frontend-ivory.vercel.app"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

with open("system_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

# Groq client — initialised once
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Request models ──────────────────────────────────────────

class ChatMessage(BaseModel):
    session_id: str
    message: str
    hour: int = -1

class MoodRequest(BaseModel):
    session_id: str
    score: int
    note: str = ""

class JournalRequest(BaseModel):
    session_id: str
    content: str
    mood: str = ""


# ── Helpers ─────────────────────────────────────────────────

def format_response(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return '\n\n'.join(s for s in sentences if s.strip())

def groq_chat(messages: list, max_tokens: int = 1024) -> str:
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=max_tokens,
    )
    return format_response(response.choices[0].message.content)

def get_or_create_session(session_id: str, db: Session):
    session = db.query(DBSession).filter(DBSession.id == session_id).first()
    if not session:
        session = DBSession(id=session_id)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session

def get_conversation_history(session_id: str, db: Session):
    messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in messages]


# ── Routes ───────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "Mindspace backend is running"}


@app.post("/start")
async def start_session(body: ChatMessage, db: Session = Depends(get_db)):
    session_id = body.session_id
    mood_context = body.message

    get_or_create_session(session_id, db)

    hour = body.hour if body.hour >= 0 else datetime.now().hour
    if hour < 12:
        time_context = "It is morning."
    elif hour < 17:
        time_context = "It is afternoon."
    elif hour < 21:
        time_context = "It is evening."
    else:
        time_context = "It is late at night."

    if mood_context and mood_context != "skip":
        opening_prompt = f"{time_context} {mood_context} Generate a single warm, calm opening response that acknowledges how they are feeling. Be natural and varied. Never ask more than one question. Keep it to 1-2 sentences maximum. Do not mention the time."
    else:
        opening_prompt = f"{time_context} Generate a single warm, calm opening greeting for someone who just opened Mindspace. Be natural and varied. Never ask more than one question. Keep it to 1-2 sentences maximum. Do not mention the time."

    greeting = groq_chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": opening_prompt}
    ])

    db.add(Message(session_id=session_id, role="assistant", content=greeting))
    db.commit()

    return {"greeting": greeting, "session_id": session_id}


@app.post("/chat")
async def chat(body: ChatMessage, db: Session = Depends(get_db)):
    session_id = body.session_id
    user_message = body.message

    get_or_create_session(session_id, db)

    db.add(Message(session_id=session_id, role="user", content=user_message))
    db.commit()

    history = get_conversation_history(session_id, db)

    ai_reply = groq_chat([
        {"role": "system", "content": SYSTEM_PROMPT}
    ] + history)

    db.add(Message(session_id=session_id, role="assistant", content=ai_reply))
    db.commit()

    return {"reply": ai_reply, "session_id": session_id}


@app.delete("/chat/{session_id}")
async def clear_session(session_id: str, db: Session = Depends(get_db)):
    db.query(Message).filter(Message.session_id == session_id).delete()
    db.commit()
    return {"status": "session cleared"}


@app.post("/intention")
async def intention(body: ChatMessage, db: Session = Depends(get_db)):
    intention_context = body.message

    prompt = f"The user just finished a Mindspace session. {intention_context} Write a single warm, closing sentence — 1 sentence only — that affirms their intention and sends them off gently. No questions. No advice. Just a quiet, human send-off."

    message = groq_chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ])

    return {"message": message}


@app.post("/mood")
async def log_mood(body: MoodRequest, db: Session = Depends(get_db)):
    get_or_create_session(body.session_id, db)

    entry = MoodLog(
        session_id=body.session_id,
        score=body.score,
        note=body.note
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"status": "logged", "id": entry.id}


@app.get("/mood/{session_id}")
async def get_mood_history(session_id: str, db: Session = Depends(get_db)):
    logs = (
        db.query(MoodLog)
        .filter(MoodLog.session_id == session_id)
        .order_by(MoodLog.created_at.desc())
        .limit(30)
        .all()
    )
    return {
        "logs": [
            {
                "id": l.id,
                "score": l.score,
                "note": l.note,
                "created_at": l.created_at.isoformat() if l.created_at else None
            }
            for l in logs
        ]
    }


@app.post("/journal")
async def save_journal(body: JournalRequest, db: Session = Depends(get_db)):
    get_or_create_session(body.session_id, db)

    entry = JournalEntry(
        session_id=body.session_id,
        content=body.content,
        mood=body.mood
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {"status": "saved", "id": entry.id}


@app.get("/journal/{session_id}")
async def get_journal_entries(session_id: str, db: Session = Depends(get_db)):
    entries = (
        db.query(JournalEntry)
        .filter(JournalEntry.session_id == session_id)
        .order_by(JournalEntry.created_at.desc())
        .all()
    )
    return {
        "entries": [
            {
                "id": e.id,
                "content": e.content,
                "mood": e.mood,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in entries
        ]
    }