from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from graph_core.state import AgentState
from graph_core.nodes import agent_node


def build_graph():
    """Build LangGraph workflow"""
    workflow = StateGraph(AgentState)
    # react agent as a node
    workflow.add_node("agent", agent_node)
    
    # Simple flow for now
    workflow.add_edge(START, 'agent')
    workflow.add_edge('agent', END)
    
    # Add memory (persistent conversation memory)
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

# fopr easy import 
graph=build_graph()