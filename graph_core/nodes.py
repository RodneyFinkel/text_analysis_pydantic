# graph_core/nodes.py
import os
from typing import Optional
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from graph_core.state import AgentState, DbQueryResult
from langchain_agent5 import AIAgent
from agent5_async import ShortResearchAgent
from utils.llm_utils import get_resilient_llm
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
        content = f"""Database query complete. 
                        Results compiled into parquet asset. 
                        Row count: {getattr(res, 'row_count', 0)}
                        [TASK COMPLETE - DB OPERATION FINISHED]
                    """
    else:
        content = result.get("content", str(result))
   
        
    # 2. Guard Fallback: If it executed successfully but didn't return type='db_result'
    # we still append a marker entry so len_db > 0, breaking any potential infinite loops.
    if not db_res_list:
        db_res_list.append(DbQueryResult(sql="Executed ReACT file/DB task", row_count=1))
        
    print("Database worker execution recorded in state metrics.")
    
    # Return both updates back to the central graph state
    return {
        "messages": [AIMessage(content=content + "\n[TASK COMPLETE - DB/FILE OPERATION FINISHED]")],
        "db_results": db_res_list
    }
    
   
class Route(BaseModel):
    next_node: str = Field(description="The next agent to route to: 'db_agent', 'writer_agent', 'researcher_agent', 'email_agent', or 'FINISH'.")
    topic: Optional[str] = Field(None, description="Extracted main topic if relevant")

def supervisor_node(state: AgentState) -> AgentState:
    print("--- Supervisor Node activated ---")
    
    # 1. Diagnostics
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None
    
    print(f"DEBUG: Last message type: {type(last_msg).__name__}")
   

    
    # 2. Data Extraction for Routing
    len_db = len(state.get("db_results", []))
    len_research = len(state.get("research_data", []))
    has_blog_post = bool(state.get("blog_post"))
    email_sent = state.get("email_sent_status", False)
    
    # Get last intent
    last_user_msg = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_msg = str(msg.content).lower()
            break
        
    # PHASE 1: PIPELINE CHECK (An Agent just finished)
    # ==========================================
    if isinstance(last_msg, AIMessage):
        print("🔍 AI Worker finished a task. Checking if more pipeline steps are needed...")
        
        # Chain 1: User wanted a blog, but we only have research so far
        if any(kw in last_user_msg for kw in ["write", "blog", "draft"]):
            if len_research > 0 and not has_blog_post:
                print("➡️ Pipeline Step: Research found, routing to writer_agent.")
                return {"next_node": "writer_agent"}
                
        # Chain 2: User wanted an email, but we haven't sent it yet
        if "email" in last_user_msg and not email_sent:
            # Ensure prerequisites are met before emailing
            if ("write" in last_user_msg or "blog" in last_user_msg) and not has_blog_post:
                pass # Still needs writing, wait for next loop
            elif "research" in last_user_msg and len_research == 0:
                pass # Still needs research, wait for next loop
            else:
                print("➡️ Pipeline Step: Prerequisite data ready, routing to email_agent.")
                return {"next_node": "email_agent"}

        # If no further pipeline steps are required, we are officially done.
        print("✅ Pipeline complete. Transitioning to FINISH.")
        return {"next_node": "FINISH"}


    # ==========================================
    # PHASE 2: NEW REQUEST ROUTING (User just typed)
    # ==========================================
    print("➡️ New user input detected. Evaluating intent...")
    
    # Reset ephemeral flags so new requests don't get blocked by old state
    state_updates = {}
    if "email" in last_user_msg:
        state_updates["email_sent_status"] = False
        email_sent = False # update local var for the LLM

    # Fast-Path Keyword Routing
    if any(kw in last_user_msg for kw in ["schema", "database", "db", "stocks", "query", "table", "sql"]):
        return {**state_updates, "next_node": "db_agent"}
        
    if any(kw in last_user_msg for kw in ["research", "news", "find", "search", "latest"]):
        return {**state_updates, "next_node": "researcher_agent"}
        
    if any(kw in last_user_msg for kw in ["write", "blog", "draft", "report"]):
        # If we already have research data, go straight to writing. 
        # If not, go to researcher first (the Pipeline will auto-route to writer next loop).
        if len_research > 0:
            return {**state_updates, "next_node": "writer_agent"}
        else:
            return {**state_updates, "next_node": "researcher_agent"}

    # 6. LLM Fallback (Complex Decisioning)
    llm = get_resilient_llm(model_name="llama-3.3-70b-versatile", temperature=0)
    structured_llm = llm.with_structured_output(Route)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a strict supervisor. Follow priority order:
            1. If asking about data, databases, or files -> db_agent
            2. If asking for news/research -> researcher_agent
            3. If asking to write content -> writer_agent
            4. If asking to email -> email_agent
            5. Otherwise FINISH

            Current context:
            - db_results count: {len_db}
            - research_data count: {len_research}
            - has_blog_post: {has_blog_post}
            - email_sent: {email_sent}"""),
        MessagesPlaceholder(variable_name="messages")
    ])
    
    chain = prompt | structured_llm
    result = chain.invoke({
        "messages": messages[-10:],
        "len_db": len_db,
        "len_research": len_research,
        "has_blog_post": has_blog_post,
        "email_sent": email_sent
    })

    print(f"Supervisor decision: {result.next_node}")
    return {"next_node": result.next_node}
   
   
   
   
    
####NEW SUPRVISOR NODE######
# class Route(BaseModel):
#     next_node: str = Field(description="The next agent to route to: 'db_agent', 'writer_agent', 'researcher_agent', 'email_agent', or 'FINISH'.")
#     topic: Optional[str] = Field(None, description="Extracted main topic if relevant")

    
    
# def supervisor_node(state: AgentState) -> AgentState:
#     print("Supervisor Node activated")
    
#     # --- DIAGNOSTIC BLOCK ---
#     msgs = state.get("messages", [])
#     last_msg = msgs[-1].content if msgs else "EMPTY"
    
#     print(f"\nDEBUG: Supervisor Node triggered.")
#     print(f"DEBUG: Last 2 message types: {[type(m).__name__ for m in msgs[-2:]]}")
#     print(f"DEBUG: Last message content preview: {str(last_msg)[:50]}")
#     print(f"DEBUG: Current next_node state: {state.get('next_node')}")
#     # ------------------------
    
#     len_db = len(state.get("db_results", []))
#     len_research = len(state.get("research_data", []))
#     has_blog_post = bool(state.get("blog_post"))
#     email_sent = state.get("email_sent_status", False)
    
#     # Get the latest user message
#     messages = state.get("messages", [])
#     # 1. Look ONLY at the very last message
#     last_msg = messages[-1] if messages else None
    
#     # 2. Check if the AI just finished a task
#     is_completion_msg = (
#         isinstance(last_msg, AIMessage) and 
#         "[TASK COMPLETE" in str(last_msg.content).upper()
#     )
    
#     # 3. Only block if the AI just finished AND there is no new HumanMessage 
#     #    between the last completion and now.
#     if is_completion_msg:
#         # If the last message was a completion, check if the user has 
#         # sent a NEW message that we haven't processed yet.
#         # If the last message is completion, and the one before was the one 
#         # that triggered it, we should FINISH.
#         print("✅ DB task completed in last turn. Finishing.")
#         return {"next_node": "FINISH"}
    
#     last_user_msg = ""
#     for msg in reversed(messages):
#         if isinstance(msg, HumanMessage):
#             last_user_msg = str(msg.content).lower()
#             break
    
#     # === IMPROVED HARD GUARDS (more intelligent) ===
#     if email_sent:
#         print("✅ Email already sent → FINISH")
#         return {"next_node": "FINISH"}
    
#     # Only block re-running db_agent if we just did DB work for this specific request
#     recent_messages = [str(m.content).lower() for m in messages[-10:]]
#     db_just_completed = any(phrase in msg for msg in recent_messages 
#                           for phrase in ["database query complete", "executed react", 
#                                        "task complete", "[task complete]"])
    
#     if db_just_completed and len_db > 0:
#         print("✅ DB task completed this turn → FINISH")
#         return {"next_node": "FINISH"}
    
#     # New: Allow db_agent again if the user is asking a new DB-related question
#     db_keywords = ["schema", "database", "db", "stocks.db", "list", "contents", 
#                    "companies", "financial", "query", "table", "select"]
#     user_wants_db = any(kw in last_user_msg for kw in db_keywords)
    
#     if user_wants_db and not db_just_completed:
#         print("User is requesting new DB work → route to db_agent")
#         return {"next_node": "db_agent"}
    
#     # === LLM fallback only when needed ===
#     llm = get_resilient_llm(model_name="llama-3.3-70b-versatile", temperature=0)
#     structured_llm = llm.with_structured_output(Route)
    
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", f"""You are a strict supervisor. Follow priority order:

#                 1. If the user is asking about databases, schemas, files, tables, or SQL → route to db_agent
#                 2. If email_sent_status is True → FINISH
#                 3. If research data exists but no blog post yet → writer_agent
#                 4. Otherwise FINISH

#                 Current metrics:
#                 - db_results: {len_db}
#                 - research_data: {len_research}
#                 - has_blog_post: {has_blog_post}
#                 - email_sent: {email_sent}

#                 Last user request: {last_user_msg[:150]}"""),
#         MessagesPlaceholder(variable_name="messages")
#     ])
    
#     chain = prompt | structured_llm
#     result = chain.invoke({
#         "messages": messages[-12:],   # Keep history short
#         "len_research": len_research,
#         "len_db": len_db,
#         "has_blog_post": has_blog_post,
#         "email_target": state.get("email_target_type", "None"),
#         "email_sent": email_sent
#     })

#     print(f"Supervisor decision: {result.next_node}")
#     return {"next_node": result.next_node}
 


# # SUPERVISOR NODE
# class Route(BaseModel):
#     next_node: str = Field(description="The next agent to route to: 'db_agent', 'writer_agent', 'researcher_agent', 'email_agent', or 'FINISH'.")
#     topic: Optional[str] = Field(None, description="Extracted main topic if relevant")
    
# def supervisor_node(state: AgentState) -> AgentState:
#     print("Supervisor Node activated")
#     llm = get_resilient_llm(model_name="llama-3.3-70b-versatile", temperature=0)
#     #llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
#     #llm = ChatOllama(model="llama3", temperature=0)
#     structured_llm = llm.with_structured_output(Route)
    
#     prompt = ChatPromptTemplate.from_messages([
#         ("system", """You are a supervisor routing agent responsible for orchestrating a multi-agent workflow.
        
#         Available agents:
#         - db_agent: For file system operations or database queries (list files, read file, SQL, etc.)
#         - researcher_agent: When fresh web research is needed.
#         - writer_agent: When the user wants a blog post or written summary based on research data.
#         - email_agent: Selected ONLY when the user's intent requires sending an email out, OR if an asset is fully completed and ready to be dispatched according to the explicit email target type requested.
#         - FINISH: When the tasks are completely done or an email has already been successfully dispatched.
        
#         Strict Routing Matrix & Termination Rules:
#         1. If email_sent_status is True, you MUST route to FINISH immediately.
#         2. If the user explicitly asks to email database findings or query outputs -> route to db_agent first, then route directly to email_agent.
#         3. If the user asks for raw research data or web information sent directly to email WITHOUT a write-up -> route to researcher_agent first, then route directly to email_agent (SKIPPING the writer_agent completely). Do NOT select researcher_agent again,
#         4. If research data has already been fetched (len_research > 0) but NO blog post has been drafted yet (has_blog_post = False), you MUST route to writer_agent to draft the post. Do NOT select researcher_agent again.
#         5. If the user asks for a blog post or formal writeup to be emailed -> route to researcher_agent, then writer_agent, then email_agent.
#         6. If a blog post or summary has already been drafted, and the user did NOT request an email, select FINISH.
#         7. CRITICAL PRE-EMPTION: Look closely at the last message in the conversation history. If it contains words like 'Error', 'failed to complete', or 'not a valid RFC 5321 address', an operation has broken down. You MUST select FINISH immediately to prevent an infinite loop.
#         8. ANTI-LOOP GUARD: If research data is already present (len_research > 0), you are strictly FORBIDDEN from choosing researcher_agent. Do not repeat web data collection.
#         9. ANTI-LOOP GUARD (DB): If database metrics indicate results are already present (len_db > 0), you are strictly FORBIDDEN from choosing db_agent again. Route to email_agent or FINISH instead.
        
        
#         Current workflow metrics:
#         - research_data length = {len_research}
#         - db_results length = {len_db}
#         - blog_post drafted = {has_blog_post}
#         - explicit email target = {email_target}
#         - email sent status = {email_sent}
        
#         Do NOT call db_agent again if len_db > 0.
        
#         """),

#         MessagesPlaceholder(variable_name="messages")
#     ])
    
    
#     chain = prompt | structured_llm
#     # Dynamically evaluate metrics from the real-time graph state
#     len_research = len(state.get("research_data", []))
#     has_blog_post = bool(state.get("blog_post"))
    
#     result = chain.invoke({
#         "messages": state["messages"],
#         "len_research": len_research,
#         "len_db": len(state.get("db_results", [])),
#         "has_blog_post": has_blog_post,
#         "email_target": state.get("email_target_type", "None"),
#         "email_sent": state.get("email_sent_status", False)
#     })

#     print(f"Supervisor decision: {result.next_node} | topic: {result.topic}")
    
#     updates: AgentState = {"next_node": result.next_node}
#     if result.topic:
#         updates["topic"] = result.topic
        
#     return updates
#     #return {"next_node": result.next_node, "topic": result.topic}

# WRITER NODE
def writer_node(state: AgentState):
    """ A node that writes a blog post based on the research data."""
    print("writer node is drafting the post")
    
    topic = state.get("topic") or "the given topic"
    data = state.get("research_data", [])[-1] if state.get("research_data") else "No research data available."    
    #llm = ChatOllama(model="llama3", temperature=0.1)
    llm = get_resilient_llm(model_name="llama-3.3-70b-versatile", temperature=0)
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
            "messages": [AIMessage(content=f"Drafted blog post on {topic}:\n {response}")],
            "task_status": "COMPLETE"
            }


# RESEARCHER NODE NOW ASYNC
async def researcher_node(state: AgentState) -> AgentState:
    """A node that performs research on the given topic."""
    topic = state.get("topic")
    # if not topic:
    #     topic = "how langGraph agents fail and succeed"
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
            "messages": [AIMessage(content=f"✅  Research completed on: {topic}")],
            "task_status": "COMPLETE"
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