# graph_core/nodes.py
import os
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from graph_core.state import AgentState
from langchain_agent4 import AIAgent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_community.tools import TavilySearchResults

_agent = None


def get_agent(working_dir: str = "."):
    global _agent
    if _agent is None or _agent.working_dir != os.path.abspath(working_dir):
        api_key = os.getenv('GROQ_API_KEY')
        _agent = AIAgent(api_key=api_key, working_dir=working_dir) # Initialize ReAct DB & FileSystem Agent
    return _agent

# DB and FILESYSTEM WORKER NODE
def agent_node(state: AgentState) -> AgentState:
    """Main LangGraph node wrapping the original ReAct agent"""
    agent = get_agent(state["working_dir"])
    
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Call original ReAct agent
    result = agent.chat(user_input)
    
    updates = {"messages": [], "db_results": []}
    
    if result["type"] == "db_result":
        db_result = result["result"]
        updates["db_results"].append(db_result)
        
        # Build clean user-facing response
        if db_result.error:
            response_text = f"❌ Database Error: {db_result.error}"
        else:
            response_text = f"""✅ **Query successful** — {db_result.row_count} row(s) returned.\n\n"""
            
            if db_result.sql:
                response_text += f"**Generated SQL:**\n```sql\n{db_result.sql}\n```\n\n"
            
            response_text += "**Results:**\n"
            
            if db_result.rows and len(db_result.rows) > 0:
                for i, row in enumerate(db_result.rows[:10], 1):
                    response_text += f"{i}. {row}\n"
                if len(db_result.rows) > 10:
                    response_text += f"\n... and {len(db_result.rows)-10} more rows."
            else:
                response_text += "No rows returned."

        # Add final response for user
        updates["messages"].append(AIMessage(content=response_text))
        
        # Add minimal tool message for agent memory
        # state["messages"].append(
        #     ToolMessage(
        #         content=f"Query executed. {db_result.row_count} rows with SQL: {db_result.sql} and {db_result.rows}",
        #         tool_call_id="db_tool_call"
        #     )
        # )
        
    else:
        # Normal response (list files, read file, etc.)
        content = result.get("content", "I processed your request.")
        updates["messages"].append(AIMessage(content=content))
    
    # Return ONLY the state updates to avoid duplicating arrays through operator.add
    return updates

# SUPERVISOR NODE
class Route(BaseModel):
    next_node: str = Field(description="The next agent to route to: 'db_agent', 'writer_agent', 'researcher_agent', or 'FINISH'.")
    
def supervisor_node(state: AgentState) -> AgentState:
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(Route)
    
    prompt = ChatPromptTemplate.from_messages([(
        "system", "You are a supervisor. Route the user input to the correct agent: "
                   "db_agent (DB/Files), researcher_agent (Web search/API), "
                   "writer_agent (Drafting content). If finished, route to FINISH."),
        MessagesPlaceholder(variable_name="messages")
    ])
    chain = prompt | structured_llm
    result = chain.invoke({"messages": state["messages"]})
    return {"next_node": result.next_node}

# WRITER NODE
def writer_node(state: AgentState) -> AgentState:
    # Logic to summarize db_results or research_results into a final doc
    # Append to state["messages"]
    return {"messages": [AIMessage(content="[Drafted professional response...]")]}

# RESEARCHER NODE
def researcher_node(state: AgentState) -> AgentState:
    pass

