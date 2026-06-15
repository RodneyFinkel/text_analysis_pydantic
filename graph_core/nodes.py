# graph_core/nodes.py
import os
from typing import Optional
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from graph_core.state import AgentState, DbQueryResult
from langchain_agent4 import AIAgent
from agent5_async import ShortResearchAgent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from email_service import send_pipeline_email
import asyncio

_agent = None
_research_agent = None

# Helper Functions
def get_agent(working_dir: str = "."):
    global _agent
    if _agent is None or _agent.working_dir != os.path.abspath(working_dir):
        api_key = os.getenv('GROQ_API_KEY')
        _agent = AIAgent(api_key=api_key, working_dir=working_dir) # Initialize ReAct DB & FileSystem Agent
    return _agent

def get_research_agent(working_dir: str = "."):
    global _research_agent
    if _research_agent is None:
        print("Loading ShortResearchAgent and embedding model...")
        _research_agent = ShortResearchAgent()
    return _research_agent

# DB and FILESYSTEM WORKER NODE
def agent_node(state: AgentState) -> AgentState:
    """Main LangGraph node wrapping the original ReACT agent"""
    print("Initializing ReACT Agent")
    agent = get_agent(state["working_dir"])
    
    # Patch for malformed tool function call
    # Filter the history: Only pass HumanMessages and relevant AIMessages
    # Drop previous massive DB readouts or unrelated research lo
    filtered_messages = [
        msg for msg in state["messages"]
        if isinstance(msg, HumanMessage) or (isinstance(msg, AIMessage) and "Database" in str(msg.content))
    ]
    
    result = agent.chat(filtered_messages)
    
    # Import your state model to update state metrics
    
    db_res_list = []
    content = ""
    
    # 1. Parse the ReACT agent's custom dictionary structure 
    # to inject into DbQueryResult state and then that is injected into the AgentState
    if isinstance(result, dict) and result.get("type") == "db_result":
        res = result.get("result")
        if res:
            db_res_list.append(DbQueryResult(
                sql=getattr(res, "sql", "Unknown SQL"),
                columns=getattr(res, "columns", []),
                rows=getattr(res, "rows", []),
                row_count=getattr(res, "row_count", 0),
                file_path=getattr(res, "file_path", None),
                error=getattr(res, "error", None)
            ))
        content = f"Database query complete. Results compiled into parquet asset: {getattr(res, 'row_count', 0)}"
    else:
        content = result.get("content", str(result))
   
        
    # 2. Guard Fallback: If it executed successfully but didn't return type='db_result'
    # we still append a marker entry so len_db > 0, breaking any potential infinite loops.
    if not db_res_list:
        db_res_list.append(DbQueryResult(sql="Executed ReACT file/DB task", row_count=1))
        
    print("Database worker execution recorded in state metrics.")
    
    # Return both updates back to the central graph state
    return {
        "messages": [AIMessage(content=content)],
        "db_results": db_res_list
    }
    
    
    # updates: AgentState = {"messages": [], "db_results": []}
    
    # if result["type"] == "db_result":
    #     db_result = result["result"]
    #     updates["db_results"].append(db_result)
        
    #     # Build clean user-facing response
    #     if db_result.error:
    #         response_text = f"❌ Database Error: {db_result.error}"
    #     else:
    #         response_text = f"""✅ **Query successful** — {db_result.row_count} row(s) returned.\n\n"""
            
    #         if db_result.sql:
    #             response_text += f"**Generated SQL:**\n```sql\n{db_result.sql}\n```\n\n"
            
    #         response_text += "**Results:**\n"
            
    #         if db_result.rows and len(db_result.rows) > 0:
    #             for i, row in enumerate(db_result.rows[:10], 1):
    #                 response_text += f"{i}. {row}\n"
    #             if len(db_result.rows) > 10:
    #                 response_text += f"\n... and {len(db_result.rows)-10} more rows."
    #         else:
    #             response_text += "No rows returned."

    #     # Add final response for user
    #     updates["messages"].append(AIMessage(content=response_text))

        
    # else:
    #     # Normal response (list files, read file, etc.)
    #     content = result.get("content", "I processed your request.")
    #     updates["messages"].append(AIMessage(content=content))
    
    # # Return ONLY the state updates to avoid duplicating arrays through operator.add
    # return updates

# SUPERVISOR NODE
class Route(BaseModel):
    next_node: str = Field(description="The next agent to route to: 'db_agent', 'writer_agent', 'researcher_agent', 'email_agent', or 'FINISH'.")
    topic: Optional[str] = Field(None, description="Extracted main topic if relevant")
    
def supervisor_node(state: AgentState) -> AgentState:
    print("Supervisor Node activated")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
    #llm = ChatOllama(model="llama3", temperature=0)
    structured_llm = llm.with_structured_output(Route)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a supervisor routing agent responsible for orchestrating a multi-agent workflow.
        
        Available agents:
        - db_agent: For file system operations or database queries (list files, read file, SQL, etc.)
        - researcher_agent: When fresh web research is needed.
        - writer_agent: When the user wants a blog post or written summary based on research data.
        - email_agent: Selected ONLY when the user's intent requires sending an email out, OR if an asset is fully completed and ready to be dispatched according to the explicit email target type requested.
        - FINISH: When the tasks are completely done or an email has already been successfully dispatched.
        
        Strict Routing Matrix & Termination Rules:
        1. If email_sent_status is True, you MUST route to FINISH immediately.
        2. If the user explicitly asks to email database findings or query outputs -> route to db_agent first, then route directly to email_agent.
        3. If the user asks for raw research data or web information sent directly to email WITHOUT a write-up -> route to researcher_agent first, then route directly to email_agent (SKIPPING the writer_agent completely). Do NOT select researcher_agent again,
        4. If research data has already been fetched (len_research > 0) but NO blog post has been drafted yet (has_blog_post = False), you MUST route to writer_agent to draft the post. Do NOT select researcher_agent again.
        5. If the user asks for a blog post or formal writeup to be emailed -> route to researcher_agent, then writer_agent, then email_agent.
        6. If a blog post or summary has already been drafted, and the user did NOT request an email, select FINISH.
        7. CRITICAL PRE-EMPTION: Look closely at the last message in the conversation history. If it contains words like 'Error', 'failed to complete', or 'not a valid RFC 5321 address', an operation has broken down. You MUST select FINISH immediately to prevent an infinite loop.
        8. ANTI-LOOP GUARD: If research data is already present (len_research > 0), you are strictly FORBIDDEN from choosing researcher_agent. Do not repeat web data collection.
        9. ANTI-LOOP GUARD (DB): If database metrics indicate results are already present (len_db > 0), you are strictly FORBIDDEN from choosing db_agent again. Route to email_agent or FINISH instead.
        
        
        Current workflow metrics:
        - research_data length = {len_research}
        - db_results length = {len_db}
        - blog_post drafted = {has_blog_post}
        - explicit email target = {email_target}
        - email sent status = {email_sent}"""),
        MessagesPlaceholder(variable_name="messages")
    ])
    
    
    chain = prompt | structured_llm
    # Dynamically evaluate metrics from the real-time graph state
    len_research = len(state.get("research_data", []))
    has_blog_post = bool(state.get("blog_post"))
    
    result = chain.invoke({
        "messages": state["messages"],
        "len_research": len_research,
        "len_db": len(state.get("db_results", [])),
        "has_blog_post": has_blog_post,
        "email_target": state.get("email_target_type", "None"),
        "email_sent": state.get("email_sent_status", False)
    })

    print(f"Supervisor decision: {result.next_node} | topic: {result.topic}")
    
    updates: AgentState = {"next_node": result.next_node}
    if result.topic:
        updates["topic"] = result.topic
        
    return updates
    #return {"next_node": result.next_node, "topic": result.topic}

# WRITER NODE
def writer_node(state: AgentState):
    """ A node that writes a blog post based on the research data."""
    print("writer node is drafting the post")
    
    topic = state.get("topic") or "the given topic"
    data = state.get("research_data", [])[-1] if state.get("research_data") else "No research data available."    
    #llm = ChatOllama(model="llama3", temperature=0.1)
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.1)
    prompt = ChatPromptTemplate.from_template((
        """You are a tech blog writer. Write a short, engaging blog post about "{topic}" based ONLY on the following research data:
        {research_data}
        Return just the blog post content. No extra commentary."""
    )
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"topic": topic, "research_data":data})
    print("Drafting complete.")
    return {"blog_post": response,
            "messages": [AIMessage(content=f"Drafted blog post on {topic}:\n {response}")]
            }


# RESEARCHER NODE NOW ASYNC
async def researcher_node(state: AgentState) -> AgentState:
    """A node that performs research on the given topic."""
    topic = state.get("topic")
    if not topic:
        topic = "how langGraph agents fail and succeed"
    print(f"Researcher node is looking up: {topic}")
        
    try:
        research_agent = get_research_agent()
        #clean await prevents prevents loop collision errors
        research_output = await research_agent.run(topic)
        results = research_output.get("summary", "No summary could be generated.") # not sure this extra step is needed, but it allows us to control what we return to the supervisor and avoid overwhelming it with too much text
    except Exception as e:
        results = f"Error during semantic web research: {str(e)}"
        
    print("Research complete,")
    
     # Only return the keys you want to update
    return {"research_data": state.get("research_data", []) + [results],
            "messages": [AIMessage(content=f"✅  Research completed on: {topic}")]
            }
    

# EMAIL ASSEMBLY & DISPATCH
async def email_node(state: AgentState) -> dict:
    """Asynchronous orchestrator node that offloads network I/O to a clean service layer."""
    print("Email Node activated - delegating execution to service layer")
    if not state.get("recipient_email"):
        return {
            "email_sent_status": False,
            "messages": [AIMessage(content="Email skipped: No recipient provided.")]
        }
        
    # Offload the external service script executio to an internal woker thread
    success = await asyncio.to_thread(send_pipeline_email, state)
    status_msg = f"✉️ Notification payload successfully emailed to {state['recipient_email']}." if success else "❌ System failed to complete email transmission."
    
    return {
        "email_sent_status": success,
        "messages": [AIMessage(content=status_msg)],
        "next_node": "FINISH"
    }