from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END, START
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class AgentState(TypedDict):
    """Defines the structure of the agent's state."""
    topic: str
    research_data: Annotated[List[str], "List of research findings"] # A list of findings
    blog_post: str # The final output
    

def researcher_node(state: AgentState):
    """A node that performs research on the given topic."""
    topic = state["topic"]
    print(f"Researcher node is looking up: {topic}")
    
    search  = DuckDuckGoSearchRun()
    
    try:
        results = search.run(f"key facts and latest news about {topic}")
    except Exception as e:
        results = f"Error during search: {str(e)}"
        
    print("Research complete,")
    
     # Only return the keys you want to update
    return {"research_data": state.get("research_data", []) + [results]}


def writer_node(state: AgentState):
    """ A node that writes a blog post based on the research data."""
    print("writer node is drafting the post")
    
    topic = state["topic"]
    data = state["research_data"][-1] if state["research_data"] else ""
    
    llm = ChatOllama(model="llama3", temperature=0.1)
    prompt = ChatPromptTemplate.from_template((
        """You are a tech blog writer. Write a short, engaging blog post about "{topic}" base ONLY on the following research data:
        {research_data}
        Return just the blog post content"""
    )
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"topic": topic, "data": data})
    print("Drafting complete.")
    return {"blog_post": response.content}


# ----- Build the LangGraph -----
workflow = StateGraph(AgentState)
workflow.add_node("Researcher", researcher_node)
workflow.add_node("Writer", writer_node)

# FLow: Start -> Researcher -> Writer -> END
workflow.add_edge(START, "Researcher")
workflow.add_edge("Researcher", "Writer")
workflow.add_edge("Writer", END)

app = workflow.compile()

if __name__ == "__main__":
    print("Starting multi-agent System...\n")
    
    inputs: AgentState = {
        "topic": "The future of AI Agents",
        "research_data": [],
        "blog_post": "",
    }
    
    result = app.invoke(inputs)
    
    print("\n---------------- FINAL OUTPUT ----------------\n")
    print(result["blog_post"])