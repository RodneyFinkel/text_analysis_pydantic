import os
import sqlite3
import argparse
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.utilities import SQLDatabase

load_dotenv()

# ─── Tool Input Schemas ────────────────────────────────────────────────────────

class ReadFileSchema(BaseModel):
    path: str = Field(description="The path to the file to read.")

class ListFilesSchema(BaseModel):
    path: str = Field(default=".", description="The directory path to list.")

class QueryDatabaseSchema(BaseModel):
    question: str = Field(description="A natural language question about the student database.")

class SuggestQueriesSchema(BaseModel):
    focus: str = Field(default="general", description="Optional focus: general, performance, trends, students, departments")

class QueryAnyDatabaseSchema(BaseModel):
    db_filename: str = Field(description="Exact filename of the .db file in the working directory (e.g. student_grades.db)")
    question: str = Field(description="Natural language question about this database.")

# ─── Structured DB Result Format ───────────────────────────────────────────────

class DbQueryResult(BaseModel):
    sql: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    error: Optional[str] = None

# ─── Agent ─────────────────────────────────────────────────────────────────────

class AIAgent:
    def __init__(self, api_key: str, working_dir: str = "."):
        self.llm = ChatGroq(
            groq_api_key=api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0
        )
        self.working_dir = os.path.abspath(working_dir)
        self.db_path = os.path.join(self.working_dir, "student_grades.db")

        self._ensure_database()
        self.default_db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")

        self.messages = [
            SystemMessage(content=(
                f"You are a helpful file and database assistant. Working directory: {self.working_dir}.\n"
                "You can read/list files and query ANY .db file in this folder.\n"
                "Use 'suggest_interesting_queries' when the user might want ideas.\n"
                "Use 'query_any_database' for any SQLite database (give exact filename).\n"
                "When answering database questions, be concise. Do not try to format or summarize large result sets yourself."
            ))
        ]

        self._setup_tools()
        self.llm_with_tools = self.llm.bind_tools(self.langchain_tools)

    def _ensure_database(self):
        if not os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT, building TEXT);
                CREATE TABLE IF NOT EXISTS students (student_id INTEGER PRIMARY KEY, name TEXT, dept_id INTEGER, email TEXT);
                CREATE TABLE IF NOT EXISTS grades (grade_id INTEGER PRIMARY KEY, student_id INTEGER, score INTEGER, letter_grade TEXT);
            """)
            conn.commit()
            conn.close()

    def _setup_tools(self):
        self.langchain_tools = [
            {"type": "function", "function": {"name": "read_file",        "description": "Read the contents of a file.",        "parameters": ReadFileSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "list_files",       "description": "List all files in a directory.",       "parameters": ListFilesSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "query_database",   "description": "Query the default student_grades.db",  "parameters": QueryDatabaseSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "suggest_interesting_queries", "description": "Suggest 4-6 interesting questions.", "parameters": SuggestQueriesSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "query_any_database","description": "Query ANY .db file in the working directory.", "parameters": QueryAnyDatabaseSchema.model_json_schema()}},
        ]

    # ─── Tool implementations ──────────────────────────────────────────────────

    def read_file(self, path: str) -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def list_files(self, path: str = ".") -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            return "\n".join(sorted(os.listdir(full_path)))
        except Exception as e:
            return f"Error listing files: {str(e)}"

    def suggest_interesting_queries(self, focus: str = "general") -> str:
        try:
            schema = self.default_db.get_table_info()
            prompt = ChatPromptTemplate.from_template("""
            Schema:
            {schema}

            Suggest 5 diverse, insightful natural language questions a user could ask.
            Focus area: {focus}

            Return only a numbered list, no extra explanation.
            """)
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke({"schema": schema, "focus": focus})
        except Exception as e:
            return f"Could not generate suggestions: {str(e)}"

    def _execute_db_query(self, db: SQLDatabase, question: str) -> Dict[str, Any]:
        try:
            prompt = ChatPromptTemplate.from_template("""
            Given the schema, write a correct SQL query to answer the question.
            Return ONLY the SQL query - no explanation, no markdown.

            Schema:
            {schema}

            Question:
            {question}
            """)
            chain = prompt | self.llm | StrOutputParser()

            sql = chain.invoke({
                "schema": db.get_table_info(),
                "question": question
            }).strip()

            # Clean common markdown fences
            if sql.startswith("```"):
                sql = sql.split("```", 2)[1 if sql.startswith("```sql") else 0].strip()

            rows = db._execute(sql)  # returns list of dicts

            return {
                "sql": sql,
                "columns": list(rows[0].keys()) if rows else [],
                "rows": [list(row.values()) for row in rows],
                "row_count": len(rows),
                "error": None
            }

        except Exception as e:
            return {
                "sql": "",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }

    def query_database(self, question: str) -> Dict[str, Any]:
        """Query the default student_grades.db — returns structured result for frontend rendering."""
        return self._execute_db_query(self.default_db, question)

    def query_any_database(self, db_filename: str, question: str) -> Dict[str, Any]:
        """Query any .db file in the working directory — returns structured result."""
        full_path = os.path.join(self.working_dir, db_filename)
        if not os.path.exists(full_path) or not db_filename.lower().endswith(".db"):
            return {
                "sql": "", "columns": [], "rows": [], "row_count": 0,
                "error": f"File '{db_filename}' not found or is not a .db file."
            }

        try:
            db = SQLDatabase.from_uri(f"sqlite:///{full_path}")
            return self._execute_db_query(db, question)
        except Exception as e:
            return {
                "sql": "", "columns": [], "rows": [], "row_count": 0,
                "error": f"Failed to open database {db_filename}: {str(e)}"
            }

    # ─── Main chat method ──────────────────────────────────────────────────────

    def chat(self, user_input: str) -> Dict[str, Any]:
        """
        Returns either:
          - {"type": "text", "content": str}          → normal text answer
          - {"type": "db_result", "result": DbQueryResult}  → database query result to be rendered as table
        """
        self.messages.append(HumanMessage(content=user_input))

        while True:
            response: AIMessage = self.llm_with_tools.invoke(self.messages)
            self.messages.append(response)

            if not response.tool_calls:
                return {"type": "text", "content": response.content}

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                tool_id = tool_call["id"]

                if tool_name in ("query_database", "query_any_database"):
                    # Execute DB query → get structured result
                    if tool_name == "query_database":
                        result_dict = self.query_database(**args)
                    else:
                        result_dict = self.query_any_database(**args)

                    # Do **NOT** put the full result back into messages
                    # Only put a short note so the LLM knows something happened
                    short_note = f"Query executed. {result_dict['row_count']} row(s) returned."
                    if result_dict["error"]:
                        short_note += f" Error: {result_dict['error']}"

                    self.messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=short_note
                    ))

                    # Return structured result to frontend
                    return {
                        "type": "db_result",
                        "result": DbQueryResult(**result_dict)
                    }

                else:
                    # Normal tools → return string result to LLM
                    method = getattr(self, tool_name)
                    tool_result = method(**args)
                    self.messages.append(ToolMessage(
                        tool_call_id=tool_id,
                        content=str(tool_result)
                    ))

        # Fallback (should not reach here)
        return {"type": "text", "content": "Finished processing."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".")
    args = parser.parse_args()

    agent = AIAgent(api_key=os.getenv("GROQ_API_KEY"), working_dir=args.directory)
    print("Agent ready. Type 'exit' to quit.")
    while True:
        inp = input("You: ")
        if inp.lower() in ["exit", "quit"]:
            break
        result = agent.chat(inp)
        if result["type"] == "text":
            print(f"Agent: {result['content']}")
        else:
            print("Database result received (would be rendered in UI)")