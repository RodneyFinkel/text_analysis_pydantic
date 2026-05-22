from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from graph_core.state import AgentState
from graph_core.nodes import agent_node, supervisor_node, writer_node, researcher_node


def build_graph():
    """Build LangGraph workflow"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("db_agent", agent_node)
    workflow.add_node("researcher_agent", researcher_node)
    workflow.add_node("writer_agent", writer_node)
    
    workflow.add_edge(START, "supervisor")
    
    # Conditional routing based on the supervisor's output
    def route(state: AgentState):
        return state.get("next_node", "FINISH")

    workflow.add_conditional_edges("supervisor", route, {
        "db_agent": "db_agent",
        "researcher_agent": "researcher_agent",
        "writer_agent": "writer_agent",
        "FINISH": END
    })
    
    # All agents return to supervisor after finishing
    workflow.add_edge("db_agent", "supervisor")
    workflow.add_edge("researcher_agent", "supervisor")
    workflow.add_edge("writer_agent", "supervisor")
    
    return workflow.compile(checkpointer=MemorySaver())

# fopr easy import 
graph=build_graph()