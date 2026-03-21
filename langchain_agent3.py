import os
import sqlite3
import argparse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase

load_dotenv()

# --- Pydantic Tool Schemas ---

class ReadFileSchema(BaseModel):
    path: str = Field(description="The path to the file to read.")

class ListFilesSchema(BaseModel):
    path: str = Field(default=".", description="The directory path to list.")

class QueryDatabaseSchema(BaseModel):
    question: str = Field(description="A natural language question about the student database.")

# --- Agent Implementation ---

class AIAgent:
    def __init__(self, api_key: str, working_dir: str = "."):
        self.llm = ChatGroq(
            groq_api_key=api_key, 
            model_name="llama-3.3-70b-versatile",
            temperature=0
        )
        self.working_dir = os.path.abspath(working_dir)
        self.db_path = os.path.join(self.working_dir, "student_grades.db")
        
        # 1. Ensure Database Exists (from create_db.py logic)
        self._ensure_database()
        
        # 2. Connect to Database (from processor.py logic)
        self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        
        self.messages = [
            SystemMessage(content=(
                f"You are a file and data assistant. Working directory: {self.working_dir}. "
                "You have access to a SQL database with student grades. "
                "Use 'query_database' for any questions about students, departments, or scores."
            ))
        ]
        
        # 3. Setup Tools using Pydantic schemas
        self._setup_tools()
        self.llm_with_tools = self.llm.bind_tools(self.langchain_tools)

    def _ensure_database(self):
        """Creates the database if missing using schema from create_db.py."""
        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Minimal schema to get started; full schema can be found in create_db.py
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT, building TEXT);
                CREATE TABLE IF NOT EXISTS students (student_id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, email TEXT);
                CREATE TABLE IF NOT EXISTS grades (grade_id INTEGER PRIMARY KEY, student_id INTEGER, score INTEGER, letter_grade TEXT);
            """)
            conn.commit()
            conn.close()

    def _setup_tools(self):
        """Manually define tools with Pydantic schemas to avoid name/validation errors."""
        self.langchain_tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file.",
                    "parameters": ReadFileSchema.model_json_schema(),
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List all files in a directory.",
                    "parameters": ListFilesSchema.model_json_schema(),
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_database",
                    "description": "Query the student database using natural language.",
                    "parameters": QueryDatabaseSchema.model_json_schema(),
                }
            }
        ]

    # --- Tool Methods ---

    def read_file(self, path: str) -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            with open(full_path, "r") as f: return f.read()
        except Exception as e: return str(e)

    def list_files(self, path: str = ".") -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            return "\n".join(os.listdir(full_path))
        except Exception as e: return str(e)

    def query_database(self, question: str) -> str:
        """Generates and executes SQL based on logic in processor.py."""
        try:
            prompt = ChatPromptTemplate.from_template("""
            Given the schema, write a SQL query to answer the question. Return ONLY the SQL.
            Schema: {schema}
            Question: {question}
            """)
            sql_chain = prompt | self.llm | StrOutputParser()
            
            generated_sql = sql_chain.invoke({
                "schema": self.db.get_table_info(),
                "question": question
            }).strip().replace("```sql", "").replace("```", "")
            
            results = self.db.run(generated_sql)
            return f"SQL executed: {generated_sql}\nResults: {results}"
        except Exception as e:
            return f"Database error: {str(e)}"

    # --- Main Loop ---

    def chat(self, user_input: str) -> str:
        self.messages.append(HumanMessage(content=user_input))
        while True:
            response = self.llm_with_tools.invoke(self.messages)
            self.messages.append(response)
            if not response.tool_calls:
                return response.content

            for tool_call in response.tool_calls:
                # Route calls to the actual class methods
                method = getattr(self, tool_call["name"])
                result = method(**tool_call["args"])
                self.messages.append(ToolMessage(tool_call_id=tool_call["id"], content=str(result)))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".")
    args = parser.parse_args()
    
    agent = AIAgent(api_key=os.getenv("GROQ_API_KEY"), working_dir=args.directory)
    print("Agent ready. Type 'exit' to quit.")
    while True:
        inp = input("You: ")
        if inp.lower() in ["exit", "quit"]: break
        print(f"\nAssistant: {agent.chat(inp)}\n")