# backend/app/agents/langgraph_orchestrator.py

import asyncio
from typing import Dict, Any, List, TypedDict, Annotated
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

class PlannerState(TypedDict):
    """
    State object for LangGraph workflow.
    All agents share this state and can read/write to it.
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
    
    # Messages/logs (accumulate over time)
    messages: Annotated[List[str], operator.add]


# ==============================================================================
# LANGGRAPH ORCHESTRATOR
# ==============================================================================

class LangGraphPlannerOrchestrator:
    """
    LangGraph-based orchestrator for travel planning agents.
    
    Workflow:
    1. Initialize → Load user preferences
    2. Activities → Search and rank activities
    3. Accommodations → Search hotels based on activity zones
    4. Transportation → Search flights
    5. Map → Calculate travel times from hotel to activities
    6. Build Itinerary → Construct day-by-day plan
    7. End
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
    # NODE FUNCTIONS (Each represents a step in the workflow)
    # --------------------------------------------------------------------------
    
    async def initialize_node(self, state: PlannerState) -> PlannerState:
        """
        Node 1: Initialize and load user preferences.
        """
        logger.info(f"[LangGraph] Node: INITIALIZE - Request ID: {state['request_id']}")
        
        user_id = state["user_id"]
        planner_request = state["planner_request"]
        
        # Build preference bundle
        pref_bundle = self._build_preference_bundle(planner_request, user_id)
        
        state["preference_bundle"] = pref_bundle
        state["messages"].append(f"Initialized preferences for user {user_id}")
        
        logger.info(f"[LangGraph] Preferences loaded: hard={pref_bundle.hard}, soft={pref_bundle.soft}")
        
        return state
    
    async def activities_node(self, state: PlannerState) -> PlannerState:
        """
        Node 2: Search and rank activities.
        """
        logger.info(f"[LangGraph] Node: ACTIVITIES")
        
        planner_request = state["planner_request"]
        planner_request["preference_bundle"] = state["preference_bundle"]
        
        # Call activities agent
        activities_resp = await self.activities_agent.handle(planner_request)
        
        ranked_activities = activities_resp["payload"]["ranked"]
        
        state["activities"] = activities_resp["payload"]
        state["ranked_activities"] = ranked_activities
        state["messages"].append(f"Found {len(ranked_activities)} activities")
        
        logger.info(f"[LangGraph] Activities agent returned {len(ranked_activities)} activities")
        
        return state
    
    async def accommodations_node(self, state: PlannerState) -> PlannerState:
        """
        Node 3: Search accommodations based on activity zones.
        """
        logger.info(f"[LangGraph] Node: ACCOMMODATIONS")
        
        planner_request = state["planner_request"]
        planner_request["ranked_activities"] = state["ranked_activities"]
        
        # Call accommodation agent
        accom_resp = await self.accom_agent.handle(planner_request)
        
        accommodations = accom_resp["payload"]
        best_hotel = accommodations[0] if accommodations else None
        
        state["accommodations"] = accommodations
        state["best_hotel"] = best_hotel
        state["messages"].append(f"Found {len(accommodations)} hotels")
        
        logger.info(f"[LangGraph] Best hotel: {best_hotel.get('name') if best_hotel else 'None'}")
        
        return state
    
    async def transportation_node(self, state: PlannerState) -> PlannerState:
        """
        Node 4: Search flights.
        """
        logger.info(f"[LangGraph] Node: TRANSPORTATION")
        
        planner_request = state["planner_request"]
        
        # Call transportation agent
        trans_resp = await self.transport_agent.handle(planner_request)
        
        flights = trans_resp["payload"]
        
        state["flights"] = flights
        state["messages"].append(f"Found {len(flights)} flights")
        
        logger.info(f"[LangGraph] Transportation agent returned {len(flights)} flights")
        
        return state
    
    async def map_node(self, state: PlannerState) -> PlannerState:
        """
        Node 5: Calculate travel times from hotel to activities.
        """
        logger.info(f"[LangGraph] Node: MAP")
        
        best_hotel = state["best_hotel"]
        ranked_activities = state["ranked_activities"]
        
        scored_with_travel = []
        
        if best_hotel and best_hotel.get("coordinates"):
            # Separate activities with and without coordinates
            activities_with_coords = []
            activities_without_coords = []
            
            for act in ranked_activities[:10]:
                if act.get("coordinates") and act["coordinates"].get("lat") and act["coordinates"].get("lng"):
                    activities_with_coords.append(act)
                else:
                    act["travel_time_min"] = 0
                    activities_without_coords.append(act)
            
            # Calculate travel times
            if activities_with_coords:
                legs = []
                for act in activities_with_coords:
                    legs.append({
                        "origin": best_hotel["coordinates"],
                        "dest": act["coordinates"],
                        "mode": "driving"
                    })
                
                directions = await self.map_agent.handle({
                    "request_id": state["request_id"],
                    "params": {"legs": legs}
                })
                
                legs_info = directions["payload"]["legs"]
                
                # Add travel times to activities
                for act, leg in zip(activities_with_coords, legs_info):
                    travel_time_min = leg["duration_min"]
                    act["travel_time_min"] = travel_time_min
                    scored_with_travel.append(act)
            
            # Add activities without coordinates
            scored_with_travel.extend(activities_without_coords)
            
            # Add remaining activities
            for act in ranked_activities[10:]:
                act["travel_time_min"] = 0
                scored_with_travel.append(act)
        else:
            # No hotel, so no travel time calculation
            for act in ranked_activities:
                act["travel_time_min"] = 0
            scored_with_travel = ranked_activities
        
        state["scored_activities_with_travel"] = scored_with_travel
        state["messages"].append(f"Calculated travel times for {len(scored_with_travel)} activities")
        
        logger.info(f"[LangGraph] Map agent calculated {len(scored_with_travel)} activities with travel times")
        
        return state
    
    async def build_itinerary_node(self, state: PlannerState) -> PlannerState:
        """
        Node 6: Build day-by-day itinerary.
        """
        logger.info(f"[LangGraph] Node: BUILD_ITINERARY")
        
        pref_bundle = state["preference_bundle"]
        hard = pref_bundle.hard
        soft = pref_bundle.soft
        scored_with_travel = state["scored_activities_with_travel"]
        best_hotel = state["best_hotel"]
        flights = state["flights"]
        
        # Build itinerary (simplified version - you can port the full logic from planner_orchestrator.py)
        start = datetime.fromisoformat(hard.date_start)
        end = datetime.fromisoformat(hard.date_end)
        total_days = (end - start).days + 1
        
        days = []
        
        # Simple day-by-day allocation (you can enhance this with the full logic)
        activities_per_day = len(scored_with_travel) // total_days if total_days > 0 else len(scored_with_travel)
        
        for day_num in range(total_days):
            current_date = start + timedelta(days=day_num)
            day_activities = scored_with_travel[day_num * activities_per_day:(day_num + 1) * activities_per_day]
            
            days.append({
                "day": day_num + 1,
                "date": current_date.isoformat(),
                "activities": day_activities[:5]  # Max 5 activities per day
            })
        
        itinerary = {
            "request_id": state["request_id"],
            "destination": hard.destination,
            "date_start": hard.date_start,
            "date_end": hard.date_end,
            "total_days": total_days,
            "hotel": best_hotel,
            "flights": flights[:2] if flights else [],  # Outbound + return
            "days": days,
            "total_activities": len(scored_with_travel)
        }
        
        state["itinerary"] = itinerary
        state["messages"].append(f"Built itinerary with {total_days} days")
        
        logger.info(f"[LangGraph] Itinerary built: {total_days} days, {len(scored_with_travel)} activities")
        
        return state
    
    # --------------------------------------------------------------------------
    # GRAPH CONSTRUCTION
    # --------------------------------------------------------------------------
    
    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph StateGraph.
        
        Flow:
        START → Initialize → Activities → [Accommodations + Transportation] → Map → Build Itinerary → END
        """
        workflow = StateGraph(PlannerState)
        
        # Add nodes
        workflow.add_node("initialize", self.initialize_node)
        workflow.add_node("activities", self.activities_node)
        workflow.add_node("accommodations", self.accommodations_node)
        workflow.add_node("transportation", self.transportation_node)
        workflow.add_node("map", self.map_node)
        workflow.add_node("build_itinerary", self.build_itinerary_node)
        
        # Define edges (flow)
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "activities")
        workflow.add_edge("activities", "accommodations")
        workflow.add_edge("accommodations", "transportation")
        workflow.add_edge("transportation", "map")
        workflow.add_edge("map", "build_itinerary")
        workflow.add_edge("build_itinerary", END)
        
        # Compile graph
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        
        logger.info("[LangGraph] Graph built successfully")
        
        return app
    
    # --------------------------------------------------------------------------
    # HELPER METHODS
    # --------------------------------------------------------------------------
    
    def _build_preference_bundle(self, planner_request: dict, user_id: str) -> UserPreferenceBundle:
        """
        Build preference bundle from request and user memory.
        """
        hard = HardConstraints(**planner_request["hard_constraints"])
        soft = SoftConstraints(**planner_request.get("soft_constraints", {}))
        
        # Load user memory
        long_raw = self.db.get_long_memory(user_id) or {}
        long_term = LongTermPreferences(**long_raw) if long_raw else LongTermPreferences()
        short_term = ShortTermPreferences()
        
        # Get user profile
        user_profile = self.db.get_user_by_id(int(user_id))
        
        # Set energy level
        energy_explicitly_set = (
            soft.energy and 
            soft.energy != "medium" and 
            soft.energy in ["low", "high"]
        )
        
        if not energy_explicitly_set and user_profile and user_profile.get("energy_level"):
            db_energy = user_profile["energy_level"]
            if db_energy in ["low", "medium", "high"]:
                soft.energy = db_energy
        elif not soft.energy:
            soft.energy = "medium"
        
        # Merge long-term preferences
        if long_term.food_preferences:
            soft.interests.extend(long_term.food_preferences)
        if long_term.activity_preferences:
            soft.interests.extend(long_term.activity_preferences)
        
        soft.interests = list(set(soft.interests))  # dedupe
        
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
        """
        Execute the planning workflow using LangGraph.
        
        Args:
            planner_request: Dictionary containing:
                - user_id: User ID
                - hard_constraints: Required constraints (destination, dates, budget)
                - soft_constraints: Optional preferences (interests, energy, spending_style)
        
        Returns:
            Dictionary containing the complete itinerary
        """
        from uuid import uuid4
        from datetime import timedelta
        
        request_id = str(uuid4())
        user_id = planner_request["user_id"]
        
        # Initialize state
        initial_state: PlannerState = {
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
            "messages": []
        }
        
        logger.info(f"[LangGraph] Starting workflow for request {request_id}")
        
        # Run the graph
        config = {"configurable": {"thread_id": request_id}}
        final_state = await self.graph.invoke(initial_state, config)
        
        logger.info(f"[LangGraph] Workflow completed for request {request_id}")
        logger.info(f"[LangGraph] Messages: {final_state['messages']}")
        
        return final_state["itinerary"]
    
    def visualize_graph(self, output_path: str = "graph.png"):
        """
        Visualize the graph and save to file.
        
        Args:
            output_path: Path to save the graph image (default: "graph.png")
        """
        from langchain_core.runnables.graph import MermaidDrawMethod
        
        try:
            img = self.graph.get_graph().draw_mermaid_png(draw_method=MermaidDrawMethod.API)
            with open(output_path, "wb") as f:
                f.write(img)
            logger.info(f"[LangGraph] Graph saved to: {output_path}")
            print(f"Đã lưu: {output_path}")
        except Exception as e:
            logger.error(f"[LangGraph] Failed to visualize graph: {e}")
            print(f"Lỗi khi tạo biểu đồ: {e}")
