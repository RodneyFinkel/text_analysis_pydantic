# graph_core/nodes.py
import os
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from graph_core.state import AgentState
from langchain_agent4 import AIAgent

_agent = None


def get_agent(working_dir: str = "."):
    global _agent
    if _agent is None or _agent.working_dir != os.path.abspath(working_dir):
        api_key = os.getenv('GROQ_API_KEY')
        _agent = AIAgent(api_key=api_key, working_dir=working_dir)
    return _agent


def agent_node(state: AgentState) -> AgentState:
    """Main LangGraph node wrapping the original ReAct agent"""
    agent = get_agent(state["working_dir"])
    
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Call original agent
    result = agent.chat(user_input)
    
    if result["type"] == "db_result":
        db_result = result["result"]
        state["db_results"].append(db_result)
        
        # Build clean user-facing response
        if db_result.error:
            response_text = f"❌ Database Error: {db_result.error}"
        else:
            response_text = f"""✅ **Query successful** — {db_result.row_count} row(s) returned.\n\n"""
            
            if db_result.sql:
                response_text += f"""**Generated SQL:**
```sql
{db_result.sql}
```\n\n"""
            
            response_text += "**Results:**\n"
            
            if db_result.rows and len(db_result.rows) > 0:
                for i, row in enumerate(db_result.rows[:10], 1):
                    response_text += f"{i}. {row}\n"
                if len(db_result.rows) > 10:
                    response_text += f"\n... and {len(db_result.rows)-10} more rows."
            else:
                response_text += "No rows returned."

        # Add final response for user
        state["messages"].append(AIMessage(content=response_text))
        
        # Add minimal tool message for agent memory
        state["messages"].append(
            ToolMessage(
                content=f"Query executed. {db_result.row_count} rows with SQL: {db_result.sql} and {db_result.rows}",
                tool_call_id="db_tool_call"
            )
        )
        
    else:
        # Normal response (list files, read file, etc.)
        content = result.get("content", "I processed your request.")
        state["messages"].append(AIMessage(content=content))
    
    return state