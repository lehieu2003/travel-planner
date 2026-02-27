# backend/test_langgraph.py

"""
Test script for LangGraph-based planner orchestrator.
Run: python test_langgraph.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.langgraph_orchestrator import LangGraphPlannerOrchestrator
from app.agents.langgraph_orchestrator_advanced import AdvancedLangGraphOrchestrator
from app.core.logger import logger


async def test_langgraph_workflow():
    """Test the LangGraph workflow with a sample request."""
    
    orchestrator = LangGraphPlannerOrchestrator()
    
    # Sample request
    planner_request = {
        "user_id": "1",
        "hard_constraints": {
            "destination": "Hà Nội",
            "date_start": "2026-03-15T00:00:00",
            "date_end": "2026-03-18T00:00:00",
            "budget_vnd": 10_000_000,
            "origin": "Hồ Chí Minh"
        },
        "soft_constraints": {
            "interests": ["food", "museum", "temple", "coffee"],
            "energy": "medium",
            "spending_style": "balanced",
            "pace": "moderate"
        }
    }
    
    logger.info("=" * 80)
    logger.info("Testing LangGraph Workflow")
    logger.info("=" * 80)
    
    try:
        # Run the workflow
        itinerary = await orchestrator.plan(planner_request)
        
        logger.info("\n" + "=" * 80)
        logger.info("WORKFLOW COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        print("\n✅ Workflow completed!")
        print(f"📍 Destination: {itinerary['destination']}")
        print(f"📅 Duration: {itinerary['total_days']} days")
        print(f"🏨 Hotel: {itinerary.get('hotel', {}).get('name', 'N/A')}")
        print(f"✈️  Flights: {len(itinerary['flights'])} found")
        print(f"🎯 Activities: {itinerary['total_activities']} total")
        print(f"📆 Days planned: {len(itinerary['days'])}")
        
        # Show first day activities
        if itinerary['days']:
            first_day = itinerary['days'][0]
            print(f"\n📍 Day 1 activities ({len(first_day['activities'])} items):")
            for i, act in enumerate(first_day['activities'][:3]):
                print(f"   {i+1}. {act.get('name', 'N/A')}")
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
        print(f"\n❌ Workflow failed: {e}")
        return False
    
    return True


def test_graph_visualization():
    """Test graph visualization for both basic and advanced versions."""
    
    logger.info("\n" + "=" * 80)
    logger.info("Testing Graph Visualization")
    logger.info("=" * 80)
    
    success_basic = False
    success_advanced = False
    
    # Test basic version
    try:
        print("\n📊 Visualizing BASIC graph...")
        orchestrator = LangGraphPlannerOrchestrator()
        orchestrator.visualize_graph("graph_basic.png")
        success_basic = True
        print("✅ Basic graph saved to: graph_basic.png")
    except Exception as e:
        logger.error(f"Basic graph visualization failed: {e}", exc_info=True)
        print(f"❌ Basic graph failed: {e}")
    
    # Test advanced version
    try:
        print("\n📊 Visualizing ADVANCED graph...")
        orchestrator_advanced = AdvancedLangGraphOrchestrator()
        orchestrator_advanced.visualize_graph("graph_advanced.png")
        success_advanced = True
        print("✅ Advanced graph saved to: graph_advanced.png")
    except Exception as e:
        logger.error(f"Advanced graph visualization failed: {e}", exc_info=True)
        print(f"❌ Advanced graph failed: {e}")
    
    if success_basic and success_advanced:
        print("\n✅ Both graphs created successfully!")
    
    return success_basic and success_advanced


async def main():
    """Main test function."""
    
    print("\n" + "=" * 80)
    print("🚀 LANGGRAPH PLANNER ORCHESTRATOR TEST")
    print("=" * 80)
    
    # Test 1: Graph visualization (doesn't require API calls)
    print("\n📊 Test 1: Graph Visualization")
    print("-" * 80)
    viz_success = test_graph_visualization()
    
    # Test 2: Full workflow (requires API keys and services)
    print("\n\n🔄 Test 2: Full Workflow")
    print("-" * 80)
    print("⚠️  Note: This test requires API keys and may take some time...")
    
    # Uncomment to test full workflow
    # workflow_success = await test_langgraph_workflow()
    workflow_success = True  # Skip for now
    print("⏭️  Skipped (requires API keys)")
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)
    print(f"Graph Visualization: {'✅ PASSED' if viz_success else '❌ FAILED'}")
    print(f"Full Workflow: {'⏭️  SKIPPED' if workflow_success else '❌ FAILED'}")
    print("=" * 80)
    
    if viz_success:
        print("\n🎉 LangGraph setup successful!")
        print("📊 Check these files to see the workflow visualizations:")
        print("   - graph_basic.png (Basic workflow)")
        print("   - graph_advanced.png (Advanced workflow with parallel execution)")
        print("\n💡 To test the full workflow, uncomment the workflow test in main()")
    else:
        print("\n❌ Some tests failed. Check logs for details.")


if __name__ == "__main__":
    asyncio.run(main())
