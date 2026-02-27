# backend/app/api/routes_langgraph.py

"""
API routes for LangGraph-based planner.
"""

from fastapi import APIRouter, HTTPException, Header, status
from typing import Dict, Any, Optional

from app.agents.langgraph_orchestrator import LangGraphPlannerOrchestrator
from app.core.security import decode_token
from app.core.logger import logger
from pydantic import BaseModel


router = APIRouter(prefix="/langgraph", tags=["LangGraph Planner"])


# Pydantic models for request/response
class PlanRequest(BaseModel):
    """Request model for planning."""
    hard_constraints: Dict[str, Any]
    soft_constraints: Dict[str, Any] = {}


class PlanResponse(BaseModel):
    """Response model for planning."""
    request_id: str
    itinerary: Dict[str, Any]
    status: str = "success"


# Global orchestrator instance
orchestrator = LangGraphPlannerOrchestrator()


# --------------------------
# Extract user ID from token
# --------------------------
def get_user_id(authorization: Optional[str]) -> int:
    """Extract and validate user ID from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid token")
    payload = decode_token(authorization.split(" ")[1])
    if not payload:
        raise HTTPException(401, "Invalid token")
    return int(payload["sub"])


@router.post("/plan", response_model=PlanResponse)
async def create_plan_langgraph(
    request: PlanRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Create a travel plan using LangGraph orchestrator.
    
    **LangGraph Workflow:**
    1. Initialize - Load user preferences
    2. Activities - Search and rank activities
    3. Accommodations - Find hotels based on activity zones
    4. Transportation - Search flights
    5. Map - Calculate travel times
    6. Build Itinerary - Create day-by-day plan
    
    Args:
        request: Planning request with constraints
        authorization: JWT token in Authorization header (Bearer token)
    
    Returns:
        Complete itinerary with hotels, flights, and activities
    """
    try:
        user_id = get_user_id(authorization)
        
        logger.info(f"[LangGraph API] Plan request from user {user_id}")
        
        # Build planner request
        planner_request = {
            "user_id": str(user_id),
            "hard_constraints": request.hard_constraints,
            "soft_constraints": request.soft_constraints
        }
        
        # Execute LangGraph workflow
        itinerary = await orchestrator.plan(planner_request)
        
        logger.info(f"[LangGraph API] Plan created: {itinerary['request_id']}")
        
        return PlanResponse(
            request_id=itinerary["request_id"],
            itinerary=itinerary,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"[LangGraph API] Plan failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create plan: {str(e)}"
        )


@router.get("/graph/visualize")
async def visualize_graph(authorization: Optional[str] = Header(None)):
    """
    Generate and return the LangGraph workflow visualization.
    
    Args:
        authorization: JWT token in Authorization header (Bearer token)
    
    Returns:
        Message with graph visualization status
    """
    # Validate user is authenticated
    get_user_id(authorization)
    
    try:
        logger.info(f"[LangGraph API] Graph visualization requested")
        
        # Generate graph visualization
        orchestrator.visualize_graph("graph.png")
        
        return {
            "status": "success",
            "message": "Graph visualization generated",
            "file": "graph.png"
        }
        
    except Exception as e:
        logger.error(f"[LangGraph API] Graph visualization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to visualize graph: {str(e)}"
        )


@router.get("/info")
async def get_langgraph_info():
    """
    Get information about the LangGraph workflow.
    
    Returns:
        Information about nodes, edges, and workflow structure
    """
    try:
        graph_info = {
            "workflow_name": "Travel Planner LangGraph",
            "version": "1.0.0",
            "nodes": [
                {
                    "name": "initialize",
                    "description": "Load user preferences and build preference bundle"
                },
                {
                    "name": "activities",
                    "description": "Search and rank activities using ActivitiesAgent"
                },
                {
                    "name": "accommodations",
                    "description": "Find hotels based on activity zones using AccommodationAgent"
                },
                {
                    "name": "transportation",
                    "description": "Search flights using TransportationAgent"
                },
                {
                    "name": "map",
                    "description": "Calculate travel times from hotel to activities using MapAgent"
                },
                {
                    "name": "build_itinerary",
                    "description": "Build day-by-day itinerary with activities"
                }
            ],
            "flow": [
                "START → initialize",
                "initialize → activities",
                "activities → accommodations",
                "accommodations → transportation",
                "transportation → map",
                "map → build_itinerary",
                "build_itinerary → END"
            ],
            "state_schema": {
                "request_id": "str",
                "user_id": "str",
                "planner_request": "Dict",
                "preference_bundle": "UserPreferenceBundle",
                "activities": "List[Dict]",
                "ranked_activities": "List[Dict]",
                "accommodations": "List[Dict]",
                "best_hotel": "Dict",
                "flights": "List[Dict]",
                "scored_activities_with_travel": "List[Dict]",
                "itinerary": "Dict",
                "messages": "List[str]"
            }
        }
        
        return {
            "status": "success",
            "data": graph_info
        }
        
    except Exception as e:
        logger.error(f"[LangGraph API] Info request failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get graph info: {str(e)}"
        )
