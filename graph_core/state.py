from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
import operator

class DbQueryResult(BaseModel):
    sql: str
    columns: List[str] = []
    rows: List[List] = []
    row_count: int = 0
    file_path: Optional[str] = None
    error: Optional[str] = None
    
class AgentState(TypedDict):
    """LangGraph State"""
    messages: Annotated[List[BaseMessage], operator.add]
    db_results: Annotated[List[DbQueryResult], operator.add]
    working_dir: str
    next_node: str = "FINISH" # added for supervisor routing
    topic: Optional[str] = None
    research_data: Annotated[List[str], "List of research findings"] = [] # A list of findings
    blog_post: Optional[str]  = None # The final output
   
    # --- ADDED FOR EMAIL ROUTING & TARGETING ---
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    email_target_type: Optional[str] = None  # Options: 'raw_research', 'blog_post', 'db_results'
    email_sent_status: bool = False
    
class WriterState(BaseModel):
    """State for the writer agent"""
    messages: Annotated[List[BaseMessage], operator.add]
    topic: str
    research_data: Annotated[List[str], "List of research findings"] # A list of findings
    blog_post: str # The final output
    
class ResearcherState(BaseModel):
    """State for the researcher agent"""
    messages: Annotated[List[BaseMessage], operator.add]
    topic: str
    research_data: Annotated[List[str], "List of research findings"] # A blog style write up of the research findings
    
    
    