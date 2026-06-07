# graph_core/nodes.py
import os
from typing import Optional
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from graph_core.state import AgentState
from langchain_agent4 import AIAgent
from agent5 import ShortResearchAgent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_community.tools import TavilySearchResults
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun # drop this when semantic agent is integrated
from langchain_core.output_parsers import StrOutputParser

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
    """Main LangGraph node wrapping the original ReAct agent"""
    print("Initializing ReAct Agent")
    agent = get_agent(state["working_dir"])
    
    # Call original ReAct agent
    result = agent.chat(state["messages"])
    
    updates: AgentState = {"messages": [], "db_results": []}
    
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
    topic: Optional[str] = Field(None, description="Extracted main topic if relevant")
    
def supervisor_node(state: AgentState) -> AgentState:
    print("Supervisor Node activated")
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
    #llm = ChatOllama(model="llama3", temperature=0)
    structured_llm = llm.with_structured_output(Route)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a supervisor routing agent responsible for orchestrating a multi-agent workflow.
        
        Available agents:
        - db_agent: ONLY for file system operations or database queries (list files, read file, SQL, etc.)
        - researcher_agent: ONLY when fresh web research is needed
        - writer_agent: when user wants a blog post or written summary
        - FINISH: when the task is complete or enough information has been gathered
        
        Strict Termination Rules:
        1. If a blog post or summary has already been drafted (blog_post drafted = True), you MUST select FINISH. Do not call writer_agent again.
        2. If a database query or file operation has already been executed and answered in the conversation history, you MUST select FINISH.
        3. If research_data already exists in the state AND the last message mentions "Research completed", go to writer_agent.
        4. Do NOT call researcher_agent or writer_agent repeatedly for the same topic.
        5. Extract the main topic when routing to researcher_agent or writer_agent.
        6. For casual chat, greetings, or empty requests → FINISH.
        
        Current workflow state metrics:
        - research_data length = {len_research}
        - blog_post drafted = {has_blog_post}"""),
        MessagesPlaceholder(variable_name="messages")
    ])
    chain = prompt | structured_llm
    # Dynamically evaluate metrics from the real-time graph state
    len_research = len(state.get("research_data", []))
    has_blog_post = bool(state.get("blog_post"))
    result = chain.invoke({
        "messages": state["messages"],
        "len_research": len_research,
        "has_blog_post": has_blog_post
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


# RESEARCHER NODE
def researcher_node(state: AgentState) -> AgentState:
    """A node that performs research on the given topic."""
    topic = state.get("topic")
    if not topic:
        topic = "how langGraph agents fail and succeed"
    print(f"Researcher node is looking up: {topic}")
    
    try:
        research_agent = get_research_agent()
        research_output = research_agent.run(topic)
        results = research_output.get("summary", "No summary could be generated.") # not sure this extra step is needed, but it allows us to control what we return to the supervisor and avoid overwhelming it with too much text
    except Exception as e:
        results = f"Error during semantic web research: {str(e)}"
        
    
    # search  = DuckDuckGoSearchRun()
    # try:
    #     results = search.run(f"key facts and latest news about {topic}")
    # except Exception as e:
    #     results = f"Error during search: {str(e)}"
        
    print("Research complete,")
    
     # Only return the keys you want to update
    return {"research_data": state.get("research_data", []) + [results],
            "messages": [AIMessage(content=f"✅  Research completed on: {topic}")]
            }
