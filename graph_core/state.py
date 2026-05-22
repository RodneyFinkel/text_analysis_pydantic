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
    next_node: str # added for supervisor routing
    
    
  
    
    