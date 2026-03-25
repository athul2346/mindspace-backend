# Mindspace Backend

FastAPI backend for Mindspace — a free, anonymous mental health companion app.

## Tech Stack

- **Python 3.14** — core language
- **FastAPI** — API framework
- **SQLAlchemy** — ORM
- **PostgreSQL** — database (Supabase in production)
- **Groq** — AI inference (llama-3.3-70b-versatile)
- **Uvicorn** — ASGI server
- **Docker** — local database setup

## Project Structure
```
mindspace-backend/
├── main.py              # API routes and application logic
├── models.py            # Database models
├── database.py          # Database connection and session
├── system_prompt.txt    # AI personality and behaviour rules
├── requirements.txt     # Python dependencies
├── docker-compose.yml   # Local PostgreSQL setup
└── .env                 # Environment variables (never commit)
```

## API Routes

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Health check |
| POST | `/start` | Start a session and get AI greeting |
| POST | `/chat` | Send a message and get AI reply |
| DELETE | `/chat/{session_id}` | Clear session messages |
| POST | `/intention` | Generate exit intention message |
| POST | `/mood` | Log a mood entry |
| GET | `/mood/{session_id}` | Get mood history |
| POST | `/journal` | Save a journal entry |
| GET | `/journal/{session_id}` | Get journal entries |
| POST | `/feedback` | Save session feedback |

## Database Schema
```
sessions          — anonymous session records
messages          — chat history per session
mood_logs         — mood scores and notes
journal_entries   — private journal entries
feedback_logs     — session quality feedback
```

## Local Development

**Prerequisites:**
- Python 3.14+
- Docker Desktop
- Groq API key (free at console.groq.com)

**Setup:**
```bash
# Clone the repo
git clone https://github.com/athul2346/mindspace-backend
cd mindspace-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Add your GROQ_API_KEY and DATABASE_URL

# Start local database
docker-compose up -d

# Create tables
python -c "from database import engine; from models import Base; Base.metadata.create_all(bind=engine)"

# Start server
uvicorn main:app --reload
```

Server runs at `http://localhost:8000`

## Environment Variables
```
GROQ_API_KEY=your_groq_api_key
DATABASE_URL=postgresql://user:password@host:port/dbname
```

## Deployment

Backend is deployed on **Render** (free tier).

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Database: Supabase PostgreSQL (connection pooler URL)

## AI Model

Currently using `llama-3.3-70b-versatile` via Groq.

The AI personality is defined in `system_prompt.txt` — it is designed to respond like a caring friend, not a therapist. Plain language, short responses that match the user's energy, emotional support first.

## Privacy

- All sessions are anonymous by default
- No personally identifying information is collected
- Chat messages are processed by Groq to generate responses
- Mood logs and journal entries are stored in Supabase
- No data is sold or shared with advertisers

## License

MIT
