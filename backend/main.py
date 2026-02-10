import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_plan import router as plan_router
from app.api.routes_conversation import router as conversation_router
from app.api.routes_chat import router as chat_router
from app.api.routes_itinerary import router as itinerary_router
from app.api.routes_profile import router as profile_router

from app.core.config_loader import settings


app = FastAPI(
    title="Travel Planner GPT",
    description="AI multi-agent travel planning system using GPT + Google Maps + SerpAPI",
    version="1.0.0"
)

# -------------------------------------------------------------
# CORS
# -------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # update to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# ROUTES
# -------------------------------------------------------------
app.include_router(auth_router)
app.include_router(plan_router)
app.include_router(conversation_router)
app.include_router(chat_router)
app.include_router(itinerary_router)
app.include_router(profile_router)


# -------------------------------------------------------------
# ROOT ENDPOINT
# -------------------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Travel Planner GPT backend is running",
        "env": settings.environment
    }


# -------------------------------------------------------------
# RUN LOCAL
# -------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
