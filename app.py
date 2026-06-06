from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph_core.graph import graph
from agent5_async import ShortResearchAgent

load_dotenv()

app = FastAPI(
    title="Multi-Agent System API",
    description="Multi-Agent System with LangGraph, Semantic RAG, and Safe NL2SQL",
    version="1.0"
)

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] =  "default"
    
class ResearchRequest(BaseModel):
    query: str
    search_results: int = 20
    
class ResearchResponse(BaseModel):
    query: str
    summary: str
    passages: List[dict]
    time: float
    
@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/research", response_model=ResearchResponse)
async def research_endpoint(req: ResearchRequest):
    """Semantic RAG research endpoint"""
    agent = ShortResearchAgent()
    result = agent.run(query=req.query, search_results=req.search_results)
    return ResearchResponse(**{k: result[k] for k in ["query", "summary", "passages", "time"]})

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    """Full LangGraph agent chat endpoint"""
    config = {"configurable": {"thread_id": req.thread_id }}
    inputs = {...} # same as in main.py, build inputs dict
    result = graph.invoke(inputs, config)
    last_msg = result["messages"][-1]
    return {"response": getattr(last_msg, "content",  str(last_msg))}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
    
