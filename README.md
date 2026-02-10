# TravelBuddy – Multi‑Agent Travel Planner

TravelBuddy is a multi‑agent AI travel planner with a FastAPI backend and a React (Vite) frontend. It uses LLMs, Google Maps and SerpAPI to generate itineraries, suggest hotels and activities, and store user profiles and conversations.

## Project structure

- `backend/`: FastAPI API, multi‑agent orchestration, integration with OpenAI, Google Maps, SerpAPI, and SQLite persistence.
- `frontend/`: React + Vite + Tailwind app, chat UI, itinerary view/save, profile management.

## Prerequisites

- **Python**: 3.10+ (virtualenv recommended)
- **Node.js**: 18+ and **npm**

---

## 1. Backend setup (FastAPI)

```bash
cd backend

# Create virtualenv (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Required environment variables

Create a `.env` file in the `backend/` directory (do not commit it) with at least:

- `OPENAI_API_KEY` – OpenAI API key
- `GOOGLE_MAPS_API_KEY` – Google Maps / Places key
- `SERPAPI_KEY` – SerpAPI key (flights, hotels, etc.)
- `JWT_SECRET_KEY`, `JWT_ALGORITHM` – JWT configuration
- `DB_PATH` – SQLite file path (default: `data.sqlite3`)
- `ENVIRONMENT` – `development` or `production`

### Run backend

```bash
cd backend

# Option 1: run with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Option 2: run the main.py script
python main.py
```

By default the backend is available at `http://localhost:8000`.

---

## 2. Frontend setup (React + Vite)

```bash
cd frontend
npm install
```

Optional: create a `.env` file in `frontend/` if you want to override the backend URL:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

### Run frontend

```bash
cd frontend
npm run dev
```

Open the URL shown by Vite in your browser (typically `http://localhost:3000`).

---

## 3. Running the full system

1. **Start backend**  
   - Terminal 1:
     ```bash
     cd backend
     source .venv/bin/activate  # if using virtualenv
     uvicorn main:app --reload --port 8000
     ```
2. **Start frontend**  
   - Terminal 2:
     ```bash
     cd frontend
     npm run dev
     ```
3. Open the UI in your browser, register / log in, then start chatting and generating travel plans.

