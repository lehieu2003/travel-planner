# Travel Planner — Multi-Agent System (FastAPI)

This repo implements a multi-agent travel planner with:
- Google Maps API (Places & Directions)
- SerpAPI (Flights & Hotels)
- Redis-backed memory (short-term & long-term)
- Algorithm 1 scoring (travel time–aware attraction scoring)

Uploaded design paper used: `/mnt/data/AITravelAgent.pdf`

## Quick start (dev)
1. Copy `.env.example` -> `.env` and fill keys.
2. Install:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

3. Start Redis (required for memory):
    docker run -p 6379:6379 redis

4. Run:
    uvicorn app.main:app --reload --port 8000

