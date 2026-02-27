# LangGraph Travel Planner

## Tổng quan

Hệ thống agents đã được chuyển đổi sang **LangGraph** - một framework mạnh mẽ để xây dựng multi-agent workflows với state management và visualization.

## Kiến trúc LangGraph

### Workflow Graph

```
START
  ↓
Initialize (Load user preferences)
  ↓
Activities (Search & rank activities)
  ↓
Accommodations (Find hotels based on activity zones)
  ↓
Transportation (Search flights)
  ↓
Map (Calculate travel times)
  ↓
Build Itinerary (Create day-by-day plan)
  ↓
END
```

### State Schema

LangGraph sử dụng một state object chung được chia sẻ giữa các agents:

```python
class PlannerState(TypedDict):
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

    # Messages/logs
    messages: List[str]
```

## Files

### Core Files

1. **`langgraph_orchestrator.py`**
   - LangGraph implementation chính
   - Định nghĩa các nodes và edges
   - State management
   - Workflow execution

2. **`routes_langgraph.py`**
   - API endpoints cho LangGraph planner
   - `/langgraph/plan` - Tạo plan mới
   - `/langgraph/graph/visualize` - Tạo biểu đồ workflow
   - `/langgraph/info` - Thông tin về workflow

3. **`test_langgraph.py`**
   - Test script để verify LangGraph workflow
   - Tạo graph visualization

## So sánh với implementation cũ

### Implementation cũ (PlannerOrchestrator)

```python
# Gọi agents theo thứ tự với asyncio
act_task = asyncio.create_task(self.activities_agent.handle(planner_request))
activities = await act_task

accom_task = asyncio.create_task(self.accom_agent.handle(planner_request))
trans_task = asyncio.create_task(self.transport_agent.handle(planner_request))
accom_resp, trans_resp = await asyncio.gather(accom_task, trans_task)
```

### Implementation mới (LangGraph)

```python
# Định nghĩa workflow graph
workflow = StateGraph(PlannerState)

# Add nodes
workflow.add_node("initialize", self.initialize_node)
workflow.add_node("activities", self.activities_node)
workflow.add_node("accommodations", self.accommodations_node)

# Define flow
workflow.set_entry_point("initialize")
workflow.add_edge("initialize", "activities")
workflow.add_edge("activities", "accommodations")

# Run workflow
app = workflow.compile()
final_state = await app.ainvoke(initial_state)
```

## Ưu điểm của LangGraph

### 1. **State Management**

- State được quản lý tự động giữa các nodes
- Dễ dàng debug và trace execution
- Hỗ trợ checkpointing và resume

### 2. **Visualization**

- Tạo biểu đồ workflow tự động
- Dễ hiểu và document

### 3. **Modularity**

- Mỗi node là một hàm độc lập
- Dễ dàng thêm/xóa/thay đổi nodes
- Reusable và testable

### 4. **Error Handling**

- Có thể thêm error nodes
- Retry và fallback logic
- Conditional routing

### 5. **Monitoring**

- Track messages và logs trong state
- Performance metrics
- Execution history

## Cài đặt

```bash
pip install -U langgraph langchain-core langchain-openai
```

## Sử dụng

### 1. Test LangGraph

```bash
cd backend
python test_langgraph.py
```

Kết quả:

- ✅ Tạo file `graph.png` với biểu đồ workflow
- ✅ Test workflow (nếu có API keys)

### 2. API Endpoints

#### Tạo plan với LangGraph

```bash
POST /langgraph/plan
Authorization: Bearer <token>

{
  "hard_constraints": {
    "destination": "Hà Nội",
    "date_start": "2026-03-15T00:00:00",
    "date_end": "2026-03-18T00:00:00",
    "budget_vnd": 10000000,
    "origin": "Hồ Chí Minh"
  },
  "soft_constraints": {
    "interests": ["food", "museum", "temple"],
    "energy": "medium",
    "spending_style": "balanced"
  }
}
```

#### Tạo biểu đồ workflow

```bash
GET /langgraph/graph/visualize
Authorization: Bearer <token>
```

#### Xem thông tin workflow

```bash
GET /langgraph/info
```

### 3. Python Code

```python
from app.agents.langgraph_orchestrator import LangGraphPlannerOrchestrator

orchestrator = LangGraphPlannerOrchestrator()

# Run workflow
itinerary = await orchestrator.plan(planner_request)

# Visualize graph
orchestrator.visualize_graph("graph.png")
```

## Graph Visualization

File `graph.png` được tạo tự động khi chạy test. Biểu đồ này hiển thị:

- Tất cả các nodes (agents)
- Flow giữa các nodes
- Entry và exit points
- State transitions

## Mở rộng

### Thêm node mới

```python
async def new_node(self, state: PlannerState) -> PlannerState:
    """Your new node logic here."""
    # Process state
    state["new_field"] = "value"
    state["messages"].append("New node executed")
    return state

# Add to graph
workflow.add_node("new_node", self.new_node)
workflow.add_edge("previous_node", "new_node")
workflow.add_edge("new_node", "next_node")
```

### Thêm conditional routing

```python
def should_proceed(state: PlannerState) -> str:
    """Decide which path to take."""
    if state["some_condition"]:
        return "path_a"
    else:
        return "path_b"

workflow.add_conditional_edges(
    "decision_node",
    should_proceed,
    {
        "path_a": "node_a",
        "path_b": "node_b"
    }
)
```

### Thêm error handling

```python
async def error_handler_node(self, state: PlannerState) -> PlannerState:
    """Handle errors gracefully."""
    try:
        # Try operation
        result = await some_operation()
        state["result"] = result
    except Exception as e:
        logger.error(f"Error: {e}")
        state["error"] = str(e)
        state["messages"].append(f"Error handled: {e}")

    return state
```

## Migration từ code cũ

Để chuyển từ `PlannerOrchestrator` sang `LangGraphPlannerOrchestrator`:

### 1. Update import

```python
# Cũ
from app.agents.planner_orchestrator import PlannerOrchestrator

# Mới
from app.agents.langgraph_orchestrator import LangGraphPlannerOrchestrator
```

### 2. Update usage

```python
# Cũ
orchestrator = PlannerOrchestrator()
itinerary = await orchestrator.plan(planner_request)

# Mới (GIỐNG NHAU!)
orchestrator = LangGraphPlannerOrchestrator()
itinerary = await orchestrator.plan(planner_request)
```

Interface giữ nguyên 100%! Chỉ cần thay đổi class import.

## Testing

### Unit tests

```python
# Test individual nodes
state = {
    "request_id": "test",
    "user_id": "1",
    # ... other fields
}

result = await orchestrator.activities_node(state)
assert len(result["ranked_activities"]) > 0
```

### Integration tests

```python
# Test full workflow
itinerary = await orchestrator.plan(planner_request)
assert itinerary["total_days"] == 3
assert len(itinerary["days"]) == 3
```

## Performance

LangGraph có thể chậm hơn một chút so với implementation cũ vì:

- State serialization/deserialization
- Graph traversal overhead
- Checkpointing (nếu enabled)

Nhưng đổi lại có:

- Better debugging
- State persistence
- Resume capabilities
- Better error handling

## Roadmap

- [ ] Thêm conditional routing cho different user types
- [ ] Implement error recovery nodes
- [ ] Add parallel execution cho independent nodes
- [ ] Integrate with LangSmith cho monitoring
- [ ] Add human-in-the-loop nodes cho user confirmations
- [ ] Implement streaming responses

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Core](https://python.langchain.com/docs/get_started/introduction)
- [State Management Best Practices](https://langchain-ai.github.io/langgraph/concepts/low_level/)

## Support

Nếu có vấn đề:

1. Check logs trong `logs/` folder
2. Run test với `python test_langgraph.py`
3. Verify API keys trong `.env`
4. Check graph visualization `graph.png`
