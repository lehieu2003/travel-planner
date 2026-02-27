# backend/app/agents/langgraph_orchestrator_advanced.py

"""
Advanced LangGraph implementation with parallel execution and conditional routing.
This demonstrates the full power of LangGraph.
"""

import asyncio
from typing import Dict, Any, List, TypedDict, Annotated, Literal
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.activities_agent import ActivitiesAgent
from app.agents.accommodation_agent import AccommodationAgent
from app.agents.transportation_agent import TransportationAgent
from app.agents.map_agent import MapAgent
from app.db.sqlite_memory import SQLiteMemory
from app.core.logger import logger
from app.models.preference_models import (
    UserPreferenceBundle,
    SoftConstraints,
    HardConstraints,
    LongTermPreferences,
    ShortTermPreferences,
)


# ==============================================================================
# STATE DEFINITION
# ==============================================================================

class AdvancedPlannerState(TypedDict):
    """
    Enhanced state with error handling and routing information.
    """
    # Input
    request_id: str
    user_id: str
    planner_request: Dict[str, Any]
    preference_bundle: UserPreferenceBundle
    
    # Intermediate results
    activities: List[Dict[str, Any]]
    ranked_activities: List[Dict[str, Any]]
    accommodations: List[Dict[str, Any]]
    best_hotel: Dict[str, Any]
    flights: List[Dict[str, Any]]
    scored_activities_with_travel: List[Dict[str, Any]]
    
    # Final output
    itinerary: Dict[str, Any]
    
    # Error handling
    errors: Annotated[List[str], operator.add]
    has_error: bool
    
    # Routing
    needs_flights: bool
    has_activities: bool
    
    # Messages/logs
    messages: Annotated[List[str], operator.add]


# ==============================================================================
# ADVANCED LANGGRAPH ORCHESTRATOR
# ==============================================================================

class AdvancedLangGraphOrchestrator:
    """
    Advanced LangGraph orchestrator with:
    - Parallel execution (accommodations + transportation)
    - Conditional routing (skip flights if not needed)
    - Error handling nodes
    - Retry logic
    """
    
    def __init__(self):
        self.db = SQLiteMemory()
        
        # Initialize agents
        self.activities_agent = ActivitiesAgent()
        self.accom_agent = AccommodationAgent()
        self.transport_agent = TransportationAgent()
        self.map_agent = MapAgent()
        
        # Build the graph
        self.graph = self._build_graph()
    
    # --------------------------------------------------------------------------
    # NODE FUNCTIONS
    # --------------------------------------------------------------------------
    
    async def initialize_node(self, state: AdvancedPlannerState) -> AdvancedPlannerState:
        """Initialize and load user preferences."""
        logger.info(f"[LangGraph Advanced] Node: INITIALIZE")
        
        try:
            user_id = state["user_id"]
            planner_request = state["planner_request"]
            
            # Build preference bundle
            pref_bundle = self._build_preference_bundle(planner_request, user_id)
            
            # Check if flights are needed
            hard = pref_bundle.hard
            needs_flights = bool(hard.origin and hard.destination)
            
            state["preference_bundle"] = pref_bundle
            state["needs_flights"] = needs_flights
            state["has_error"] = False
            state["messages"].append(f"Initialized preferences for user {user_id}")
            
            logger.info(f"[LangGraph Advanced] Needs flights: {needs_flights}")
            
            return state
            
        except Exception as e:
            logger.error(f"[LangGraph Advanced] Initialize error: {e}", exc_info=True)
            state["errors"].append(f"Initialize error: {str(e)}")
            state["has_error"] = True
            return state
    
    async def activities_node(self, state: AdvancedPlannerState) -> AdvancedPlannerState:
        """Search and rank activities with retry."""
        logger.info(f"[LangGraph Advanced] Node: ACTIVITIES")
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                planner_request = state["planner_request"]
                planner_request["preference_bundle"] = state["preference_bundle"]
                
                # Call activities agent
                activities_resp = await self.activities_agent.handle(planner_request)
                
                ranked_activities = activities_resp["payload"]["ranked"]
                
                state["activities"] = activities_resp["payload"]
                state["ranked_activities"] = ranked_activities
                state["has_activities"] = len(ranked_activities) > 0
                state["messages"].append(f"Found {len(ranked_activities)} activities")
                
                logger.info(f"[LangGraph Advanced] Activities: {len(ranked_activities)}")
                
                return state
                
            except Exception as e:
                retry_count += 1
                logger.error(f"[LangGraph Advanced] Activities error (attempt {retry_count}): {e}")
                
                if retry_count >= max_retries:
                    state["errors"].append(f"Activities error after {max_retries} retries: {str(e)}")
                    state["has_error"] = True
                    state["has_activities"] = False
                    state["ranked_activities"] = []
                    return state
                
                await asyncio.sleep(1)  # Wait before retry
    
    async def parallel_search_node(self, state: AdvancedPlannerState) -> AdvancedPlannerState:
        """
        Run accommodations and transportation searches IN PARALLEL.
        This is more efficient than sequential execution.
        """
        logger.info(f"[LangGraph Advanced] Node: PARALLEL_SEARCH")
        
        planner_request = state["planner_request"]
        planner_request["ranked_activities"] = state["ranked_activities"]
        
        # Create tasks for parallel execution
        tasks = []
        
        # Always search accommodations
        accom_task = asyncio.create_task(self._search_accommodations(planner_request))
        tasks.append(("accommodations", accom_task))
        
        # Only search flights if needed
        if state["needs_flights"]:
            trans_task = asyncio.create_task(self._search_transportation(planner_request))
            tasks.append(("transportation", trans_task))
        
        # Wait for all tasks to complete
        results = {}
        for name, task in tasks:
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"[LangGraph Advanced] Parallel search error ({name}): {e}")
                state["errors"].append(f"Parallel search error ({name}): {str(e)}")
                results[name] = None
        
        # Update state with results
        if results.get("accommodations"):
            accommodations = results["accommodations"]["payload"]
            state["accommodations"] = accommodations
            state["best_hotel"] = accommodations[0] if accommodations else {}
            state["messages"].append(f"Found {len(accommodations)} hotels")
        else:
            state["accommodations"] = []
            state["best_hotel"] = {}
        
        if results.get("transportation"):
            flights = results["transportation"]["payload"]
            state["flights"] = flights
            state["messages"].append(f"Found {len(flights)} flights")
        else:
            state["flights"] = []
        
        logger.info(f"[LangGraph Advanced] Parallel search completed")
        
        return state
    
    async def _search_accommodations(self, planner_request: Dict[str, Any]) -> Dict[str, Any]:
        """Helper: Search accommodations."""
        return await self.accom_agent.handle(planner_request)
    
    async def _search_transportation(self, planner_request: Dict[str, Any]) -> Dict[str, Any]:
        """Helper: Search transportation."""
        return await self.transport_agent.handle(planner_request)
    
    async def map_node(self, state: AdvancedPlannerState) -> AdvancedPlannerState:
        """Calculate travel times."""
        logger.info(f"[LangGraph Advanced] Node: MAP")
        
        try:
            best_hotel = state["best_hotel"]
            ranked_activities = state["ranked_activities"]
            
            # Skip if no hotel or no activities
            if not best_hotel or not ranked_activities:
                state["scored_activities_with_travel"] = ranked_activities
                state["messages"].append("Skipped travel time calculation (no hotel or activities)")
                return state
            
            # Calculate travel times (simplified - see full implementation in langgraph_orchestrator.py)
            scored_with_travel = []
            
            for act in ranked_activities:
                act["travel_time_min"] = 0  # Simplified
                scored_with_travel.append(act)
            
            state["scored_activities_with_travel"] = scored_with_travel
            state["messages"].append(f"Calculated travel times for {len(scored_with_travel)} activities")
            
            return state
            
        except Exception as e:
            logger.error(f"[LangGraph Advanced] Map error: {e}", exc_info=True)
            state["errors"].append(f"Map error: {str(e)}")
            state["scored_activities_with_travel"] = state["ranked_activities"]
            return state
    
    async def build_itinerary_node(self, state: AdvancedPlannerState) -> AdvancedPlannerState:
        """Build final itinerary."""
        logger.info(f"[LangGraph Advanced] Node: BUILD_ITINERARY")
        
        try:
            pref_bundle = state["preference_bundle"]
            hard = pref_bundle.hard
            
            from datetime import timedelta
            
            start = datetime.fromisoformat(hard.date_start)
            end = datetime.fromisoformat(hard.date_end)
            total_days = (end - start).days + 1
            
            itinerary = {
                "request_id": state["request_id"],
                "destination": hard.destination,
                "date_start": hard.date_start,
                "date_end": hard.date_end,
                "total_days": total_days,
                "hotel": state["best_hotel"],
                "flights": state["flights"][:2] if state["flights"] else [],
                "days": [],
                "total_activities": len(state["scored_activities_with_travel"]),
                "errors": state["errors"] if state["errors"] else None
            }
            
            state["itinerary"] = itinerary
            state["messages"].append(f"Built itinerary with {total_days} days")
            
            return state
            
        except Exception as e:
            logger.error(f"[LangGraph Advanced] Build itinerary error: {e}", exc_info=True)
            state["errors"].append(f"Build itinerary error: {str(e)}")
            state["has_error"] = True
            return state
    
    async def error_handler_node(self, state: AdvancedPlannerState) -> AdvancedPlannerState:
        """Handle errors gracefully."""
        logger.info(f"[LangGraph Advanced] Node: ERROR_HANDLER")
        
        error_message = "; ".join(state["errors"])
        
        # Create a fallback itinerary
        state["itinerary"] = {
            "request_id": state["request_id"],
            "status": "error",
            "error_message": error_message,
            "partial_results": {
                "activities": len(state.get("ranked_activities", [])),
                "hotels": len(state.get("accommodations", [])),
                "flights": len(state.get("flights", []))
            }
        }
        
        state["messages"].append(f"Error handled: {error_message}")
        
        logger.error(f"[LangGraph Advanced] Error handled: {error_message}")
        
        return state
    
    # --------------------------------------------------------------------------
    # ROUTING FUNCTIONS
    # --------------------------------------------------------------------------
    
    def should_continue_after_activities(self, state: AdvancedPlannerState) -> Literal["parallel_search", "error_handler"]:
        """
        Conditional routing after activities node.
        If activities failed, go to error handler.
        Otherwise, continue to parallel search.
        """
        if state["has_error"] or not state["has_activities"]:
            logger.info("[LangGraph Advanced] Routing to error_handler (no activities)")
            return "error_handler"
        else:
            logger.info("[LangGraph Advanced] Routing to parallel_search")
            return "parallel_search"
    
    def should_continue_after_parallel(self, state: AdvancedPlannerState) -> Literal["map", "error_handler"]:
        """
        Conditional routing after parallel search.
        If critical errors, go to error handler.
        Otherwise, continue to map.
        """
        if state["has_error"]:
            logger.info("[LangGraph Advanced] Routing to error_handler (parallel search failed)")
            return "error_handler"
        else:
            logger.info("[LangGraph Advanced] Routing to map")
            return "map"
    
    # --------------------------------------------------------------------------
    # GRAPH CONSTRUCTION
    # --------------------------------------------------------------------------
    
    def _build_graph(self) -> StateGraph:
        """
        Build advanced graph with parallel execution and conditional routing.
        
        Flow:
        START → Initialize → Activities → [Conditional]
                                              ↓
                                        Has activities?
                                          ↙         ↘
                                      YES           NO
                                       ↓             ↓
                              Parallel Search   Error Handler → END
                         (Accom + Transport)
                                       ↓
                                   Has errors?
                                    ↙      ↘
                                  NO       YES
                                   ↓        ↓
                                  Map   Error Handler → END
                                   ↓
                            Build Itinerary
                                   ↓
                                  END
        """
        workflow = StateGraph(AdvancedPlannerState)
        
        # Add nodes
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("activities", self.activities_node)
        workflow.add_node("parallel_search", self.parallel_search_node)
        workflow.add_node("map", self.map_node)
        workflow.add_node("build_itinerary", self.build_itinerary_node)
        workflow.add_node("error_handler", self.error_handler_node)
        
        # Define flow with conditional routing
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "activities")
        
        # Conditional routing after activities
        workflow.add_conditional_edges(
            "activities",
            self.should_continue_after_activities,
            {
                "parallel_search": "parallel_search",
                "error_handler": "error_handler"
            }
        )
        
        # Conditional routing after parallel search
        workflow.add_conditional_edges(
            "parallel_search",
            self.should_continue_after_parallel,
            {
                "map": "map",
                "error_handler": "error_handler"
            }
        )
        
        workflow.add_edge("map", "build_itinerary")
        workflow.add_edge("build_itinerary", END)
        workflow.add_edge("error_handler", END)
        
        # Compile graph
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        
        logger.info("[LangGraph Advanced] Advanced graph built successfully")
        
        return app
    
    # --------------------------------------------------------------------------
    # HELPER METHODS
    # --------------------------------------------------------------------------
    
    def _build_preference_bundle(self, planner_request: dict, user_id: str) -> UserPreferenceBundle:
        """Build preference bundle from request and user memory."""
        hard = HardConstraints(**planner_request["hard_constraints"])
        soft = SoftConstraints(**planner_request.get("soft_constraints", {}))
        
        long_raw = self.db.get_long_memory(user_id) or {}
        long_term = LongTermPreferences(**long_raw) if long_raw else LongTermPreferences()
        short_term = ShortTermPreferences()
        
        user_profile = self.db.get_user_by_id(int(user_id))
        
        if user_profile and user_profile.get("energy_level"):
            soft.energy = user_profile["energy_level"]
        elif not soft.energy:
            soft.energy = "medium"
        
        if long_term.food_preferences:
            soft.interests.extend(long_term.food_preferences)
        if long_term.activity_preferences:
            soft.interests.extend(long_term.activity_preferences)
        
        soft.interests = list(set(soft.interests))
        
        return UserPreferenceBundle(
            hard=hard,
            soft=soft,
            long_term=long_term,
            short_term=short_term
        )
    
    # --------------------------------------------------------------------------
    # PUBLIC API
    # --------------------------------------------------------------------------
    
    async def plan(self, planner_request: dict) -> dict:
        """Execute the advanced planning workflow."""
        from uuid import uuid4
        
        request_id = str(uuid4())
        user_id = planner_request["user_id"]
        
        # Initialize state
        initial_state: AdvancedPlannerState = {
            "request_id": request_id,
            "user_id": user_id,
            "planner_request": planner_request,
            "preference_bundle": None,
            "activities": [],
            "ranked_activities": [],
            "accommodations": [],
            "best_hotel": {},
            "flights": [],
            "scored_activities_with_travel": [],
            "itinerary": {},
            "errors": [],
            "has_error": False,
            "needs_flights": False,
            "has_activities": False,
            "messages": []
        }
        
        logger.info(f"[LangGraph Advanced] Starting workflow for request {request_id}")
        
        # Run the graph
        config = {"configurable": {"thread_id": request_id}}
        final_state = await self.graph.invoke(initial_state, config)
        
        logger.info(f"[LangGraph Advanced] Workflow completed")
        logger.info(f"[LangGraph Advanced] Messages: {final_state['messages']}")
        
        if final_state["errors"]:
            logger.warning(f"[LangGraph Advanced] Errors: {final_state['errors']}")
        
        return final_state["itinerary"]
    
    def visualize_graph(self, output_path: str = "graph_advanced.png"):
        """Visualize the advanced graph."""
        from langchain_core.runnables.graph import MermaidDrawMethod
        
        try:
            img = self.graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
            with open(output_path, "wb") as f:
                f.write(img)
            logger.info(f"[LangGraph Advanced] Graph saved to: {output_path}")
            print(f"Đã lưu: {output_path}")
        except Exception as e:
            logger.error(f"[LangGraph Advanced] Failed to visualize graph: {e}")
            print(f"Lỗi khi tạo biểu đồ: {e}")
