from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
from pydantic import BaseModel

class DbQueryResult(BaseModel):
    sql: str
    columns: List[str] = []
    rows: List[List] = []
    row_count: int = 0
    error: Optional[str] = None
    
class AgentState(TypedDict):
    """LangGraph State"""
    messages: Annotated[List[BaseMessage], "The chat message history"]
    db_results: Annotated[List[DbQueryResult], "Structured database results for UI"]
    working_dir: str
    
    
    