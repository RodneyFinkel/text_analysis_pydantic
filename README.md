### Deployed Live at https://multi-agent-platform-alpha.onrender.com

Or locally after cloning and supplying Groq API key

uvicorn app:app --reload --port 8000

Fully dockerized and continuosly updated


## System Architecture & Data Pipeline Matrix

<img width="1669" height="2527" alt="Mutli Agent Supervisor" src="https://github.com/user-attachments/assets/794baadc-83e5-427a-8df7-43e6b3842002" />

<img width="1918" height="969" alt="Screenshot 2026-06-12 at 6 53 58" src="https://github.com/user-attachments/assets/b82e028c-4ea5-4d42-b318-f6201e790eab" />




<img width="1680" height="1050" alt="Screenshot 2026-06-12 at 20 32 40" src="https://github.com/user-attachments/assets/7cac24b1-bd62-44b3-a21f-ce4bb978930a" />

<img width="1191" height="910" alt="Screenshot 2026-06-14 at 7 13 48" src="https://github.com/user-attachments/assets/7dac1baf-48e8-4921-b503-5b658ba9d851" />


GROQ_API_KEY is needed inside a .env file
Clone the repository

Create a virtual environment
python -m venv venv

Activate the virtual environment
On macOS/Linux:
source venv/bin/activate
On Windows:
.\venv\Scripts\activate

Install all required libraries using the requirements.txt file provided in the repository:
pip install -r requirements.txt

Launch the Streamlit server to view the app in your browser:
streamlit run streamlit_app4.py



uvicorn app:app --reload --port 8000

#ReACT Agent for Filesystem and NL2SQL
<img width="1072" height="1915" alt="Screenshot 2026-04-28 at 11 14 22" src="https://github.com/user-attachments/assets/c657de24-b4f0-4824-95ca-44769282e408" />

<img width="1072" height="1915" alt="Screenshot 2026-04-28 at 11 13 50" src="https://github.com/user-attachments/assets/39f833ed-853a-40df-84c3-7720723015d6" />



<img width="1898" height="966" alt="Screenshot 2026-03-05 at 23 30 12" src="https://github.com/user-attachments/assets/b400b5bb-0c6e-45a7-ba30-89ac457ec5e2" />

<img width="1905" height="966" alt="Screenshot 2026-03-05 at 23 30 49" src="https://github.com/user-attachments/assets/0138e516-8167-4720-88f3-370c7c4edb6d" />


FastAPI Swagger UI for LangGraph Multi Agent and endpoints for DB/Filesystem ReACT Agent and Asyn Semantic Web-Search with ChromaDb persistence

<img width="954" height="965" alt="Screenshot 2026-06-07 at 4 43 54" src="https://github.com/user-attachments/assets/81cb4910-e0f7-474d-b5e8-aaad1d3289e4" />

<img width="954" height="965" alt="Screenshot 2026-06-07 at 4 41 39" src="https://github.com/user-attachments/assets/82439e0d-a733-4613-899b-5e2ee37d538a" />


Why Llama 3.3 70B Versatile?

It is specifically tuned to excel at JSON mode and Function Calling
128K Context Window: Supports a very large 128,000-token context.  No need to build chunking or map-reduce logic.


Using Pydantic replaces traditional prompt-engineering for output formatting by providing a schema contract that forces the LLM to return valid, structured data. This was chosen to eliminate unpredictable text chatter and ensure type-safe validation. Moving logic from raw strings to Python objects makes the app becomes more robust. 










