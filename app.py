from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph_core.graph import graph
from agent5_async import ShortResearchAgent
from langchain_agent4 import AIAgent
import uuid

## FRONTEND
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

app = FastAPI(
    title="Multi-Agent System API",
    description="Multi-Agent System with LangGraph, Semantic RAG, and Safe NL2SQL",
    version="1.0.0",
    contact={
        "name": "Rodney Finkel",
        "email": "rodneyfinkel@gmail.com"
    },
    swagger_ui_parameters={
        "docExpansion": "none",
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
        "filter": True,
        "deepLinking": True,
    }
)

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = "User"
    email_target: Optional[str] = None  # Expected payload values: 'raw_research', 'blog_post', 'db_results'
    
class ResearchRequest(BaseModel):
    query: str
    search_results: int = 20
    
class ResearchResponse(BaseModel):
    query: str
    summary: str
    passages: List[dict]
    time: float
    
class DBRequest(BaseModel):
    message: str
    working_dir: str =  "."
    
### HELPER FUNCTION for ReACT agent endpoint
def get_db_agent(working_dir: str=".") -> AIAgent:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not set in environment variables")
    return AIAgent(api_key=api_key, working_dir=working_dir)


# NEW LANDING PAGE
@app.get("/")
async def serve_landing_page():
    return FileResponse("static/landing.html")


# NEW FRONTEND
@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse("static/index.html")

    
@app.get("/health")
def health():
    return {"status": "healthy"}

# Research endpoint using ShortResearchAgent from agent5_async.py
@app.post("/research", response_model=ResearchResponse)
async def research_endpoint(req: ResearchRequest):
    """Semantic RAG research endpoint"""
    agent = ShortResearchAgent()
    result = await agent.run(query=req.query, search_results=req.search_results)
    return ResearchResponse(**{k: result[k] for k in ["query", "summary", "passages", "time"]})

# Full chat endpoint using LangGraph orchestrating the db and filesystem agent and the research agent
@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Full LangGraph agent chat endpoint"""
    #working_dir = "."
    working_dir = os.path.abspath(".")
    
    # AUTOMATION GATE: Prevent thread contamination automatically
    active_thread = req.thread_id
    if not active_thread or active_thread.strip() in ["", "string", "new", "default"]:
        # Generate a pristine unique tracking id for this run
        active_thread = f"run_{uuid.uuid4().hex[:10]}"
        print(f"🔄 Notice: Generating isolated state container: {active_thread}")
    else:
        print(f"💾 Notice: Re-entering existing state session container: {active_thread}")
        
    config = {"configurable": {"thread_id": req.thread_id }}
    inputs = {
                    "messages": [HumanMessage(content=req.message)],
                    "db_results": [],
                    "working_dir": working_dir,
                    "research_data": [],
                    "blog_post": None,
                    "next_node": "FINISH", # default to FINISH, supervisor will update if needed
                    
                    # Hydrating explicit initialization contexts straight into the graph
                    "recipient_email": req.email,
                    "recipient_name": req.name,
                    "email_target_type": req.email_target,
                    "email_sent_status": False
                } 
    #result = graph.invoke(inputs, config)
    result = await graph.ainvoke(inputs, config)
    last_msg = result["messages"][-1]
    return {"response": getattr(last_msg, "content",  str(last_msg))}

# DB and FileSystem agent endpoint for testing ReACT agent seperately
@app.post("/agent")
async def db_agent_endpoint(req:DBRequest):
    """NL2SQL, list files, read files, schema introspection"""
    try:
        agent = get_db_agent(req.working_dir)
        result = agent.chat(req.message)
        
        if result["type"] == "db_result":
            res = result["result"]
            return {
                "type": "db_result",
                "sql": getattr(res, "sql", None),
                "row_count": getattr(res, "row_count", 0),
                "error": getattr(res, "error", None),
                "columns": getattr(res, "columns", []),
                "rows_preview": getattr(res, "rows", [])[:10] if hasattr(res, "rows") else [],
                "file_path": getattr(res, "file_path", None)
            }
        else:
            return {
                "type": "text",
                "content": result.get("content", str(result))
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Agent error: {str(e)}")
    
    

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    
