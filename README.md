GROQ_API_KEY is needed inside a .env file
Clone the repository

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

Install all required libraries using the requirements.txt file provided in the repository:
pip install -r requirements.txt

Launch the Streamlit server to view the app in your browser:
streamlit run app.py

Alternatively use this link for a live demo: http://rodneyfinkel-text-analysis-pydantic-streamlit-app4-h4ppca.streamlit.app




<img width="1072" height="1915" alt="Screenshot 2026-04-28 at 11 14 22" src="https://github.com/user-attachments/assets/c657de24-b4f0-4824-95ca-44769282e408" />

<img width="1072" height="1915" alt="Screenshot 2026-04-28 at 11 13 50" src="https://github.com/user-attachments/assets/39f833ed-853a-40df-84c3-7720723015d6" />





<img width="1909" height="954" alt="Screenshot 2026-02-20 at 21 20 38" src="https://github.com/user-attachments/assets/3018ad5d-e9f4-47c0-bf95-6c1610c21978" />



<img width="1898" height="966" alt="Screenshot 2026-03-05 at 23 30 12" src="https://github.com/user-attachments/assets/b400b5bb-0c6e-45a7-ba30-89ac457ec5e2" />

<img width="1905" height="966" alt="Screenshot 2026-03-05 at 23 30 49" src="https://github.com/user-attachments/assets/0138e516-8167-4720-88f3-370c7c4edb6d" />

<img width="1909" height="954" alt="Screenshot 2026-02-20 at 21 21 04" src="https://github.com/user-attachments/assets/7a9cf355-75b8-40e7-9836-f42fb399917c" />

FastAPI Swagger UI for LangGraph Multi Agent and endpoints for DB/Filesystem ReACT Agent and Asyn Semantic Web-Search with ChromaDb persistence

<img width="954" height="965" alt="Screenshot 2026-06-07 at 4 43 54" src="https://github.com/user-attachments/assets/81cb4910-e0f7-474d-b5e8-aaad1d3289e4" />

<img width="954" height="965" alt="Screenshot 2026-06-07 at 4 41 39" src="https://github.com/user-attachments/assets/82439e0d-a733-4613-899b-5e2ee37d538a" />




Why Llama 3.3 70B Versatile?

Llama 3.3 70B's performance is comparable to much larger models. This model also scores high on benchmarks (92.1 on IFEval) for following user instructions. This is important  because it ensures the model adheres strictly to the constraints defined in the Pydantic schemas without chatter or formatting errors.

It is specifically tuned to excel at JSON mode and Function Calling

128K Context Window: Supports a very large 128,000-token context.  No need to build chunking or map-reduce logic.




Using Pydantic replaces traditional prompt-engineering for output formatting by providing a schema contract that forces the LLM to return valid, structured data. This was chosen to eliminate unpredictable text chatter and ensure type-safe validation (like forcing confidence scores in Use Case 3 to be floats). Moving logic from raw strings to Python objects makes the app becomes more robust. 


graph TD
    %% Define User Interface / Client Layer
    subgraph Clients ["Client / Interface Layer"]
        CLI
        UI
        API_POST
    end

    %% The Orchestration Layer: LangGraph
    subgraph LangGraph ["Orchestration Layer: LangGraph graph.py"]
        direction TB
        State[]

        %% Hub & Spoke Routing Engine
        SUPERVISOR(cite: supervisor_node nodes.py<br/>Llama-3.3-70B via Groq)

        %% Worker Nodes
        WORKER_RESEARCH(cite: researcher_node nodes.py<br/>Semantic Search & RAG)
        WORKER_DB(cite: agent_node nodes.py<br/>DB/FileSystem Operations)
        WORKER_WRITER(cite: writer_node nodes.py<br/>Blog Post Drafting)

        %% Specialized Internal Logic
        SQL_GUARD(cite: AST SQL Validator<br/>via sqlglot)
    end

    %% Execution and Tool Layer (Async Workers)
    subgraph Execution_Layer ["Execution Layer: Async Workers & Models"]
        RAG_PIPELINE(cite: ShortResearchAgent agent5_async.py)
        REACT_DB(cite: AIAgent langchain_agent4.py)
    end

    %% External Data Sources
    subgraph Data_Sources ["External Data & Persistence Layer"]
        DDGS
        SQLite
        ChromaDB
    end

    %% Flow: Clients to LangGraph
    CLI ==>|cite: graph.invoke inputs| LangGraph
    UI ==>|cite: graph.invoke inputs| LangGraph
    API_POST ==>|cite: graph.invoke inputs| LangGraph

    %% Flow: Internal LangGraph Execution Loop (CRITICAL)
    START(cite: Graph START) --> SUPERVISOR
    SUPERVISOR -.->|cite: Decide NEXT based on State| NEXT_DECISION{cite: Routing Decision}

    NEXT_DECISION ==>|cite: next_node = researcher_agent<br/>with topic| WORKER_RESEARCH
    NEXT_DECISION ==>|cite: next_node = db_agent| WORKER_DB
    NEXT_DECISION ==>|cite: next_node = writer_agent<br/>Hand-off for drafting| WORKER_WRITER
    NEXT_DECISION ==>|cite: next_node = FINISH| END(cite: Graph END)

    %% Flow: Workers Loop Back to Supervisor for Re-evaluation
    WORKER_RESEARCH ==>|cite: State Updated: Research Data| SUPERVISOR
    WORKER_DB ==>|cite: State Updated: DB results| SUPERVISOR
    WORKER_WRITER ==>|cite: State Updated: blog_post drafted| SUPERVISOR

    %% Flow: Workers interfacing with Execution Layer
    WORKER_RESEARCH -.->|cite: Execute RAG Pipeline| RAG_PIPELINE
    WORKER_DB -.->|cite: Pass ReAct Prompt| REACT_DB
    REACT_DB -.->|cite: Extract SQL for Validation| SQL_GUARD
    SQL_GUARD -.->|cite: If Valid & Read-Only| SQLite

    %% Flow: Execution interfacing with External Tools
    RAG_PIPELINE -.->|cite: Parallel Scrape aiohttp| DDGS
    RAG_PIPELINE -.->|cite: Local Embedding Model| ChromaDB

    %% Styling for clarity
    classDef supervisor fill:#f9f,stroke:#333,stroke-width:2px,color:black;
    classDef worker fill:#bbf,stroke:#333,stroke-width:1px,color:black;
    classDef data fill:#dfd,stroke:#333,stroke-width:1px,stroke-dasharray: 5 5,color:black;
    classDef orchestrator fill:#eee,stroke:#333,stroke-width:2px,color:black;

    class SUPERVISOR supervisor;
    class WORKER_RESEARCH,WORKER_DB,WORKER_WRITER worker;
    class DDGS,SQLite,ChromaDB data;
    class LangGraph orchestrator;




