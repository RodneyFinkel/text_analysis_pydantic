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
from sqlglot import parse_one, exp
from sqlglot.errors import ParseError
from langchain_core.tools import StructuredTool
import re


load_dotenv()

# Tool Input Schemas

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
    
class ListAvailableDatabasesSchema(BaseModel):
    """No input parameters needed"""
    pass

# Structured DB Result Format 

class DbQueryResult(BaseModel):
    sql: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    error: Optional[str] = None
    
# NEW SCHEMA INTROSPECTION TOOL
class GetDatabaseSchemaSchema(BaseModel):
    db_filename: str = Field(description="Exact filename of the .db file in the working directory (e.g., student_grades.db)")
    


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

    #     self.messages = [
    #         SystemMessage(content=(
    #             f"You are an expert file and database assistant. "
    #     f"Current working directory: {self.working_dir}\n\n"

    #     "AVAILABLE CAPABILITIES:\n"
    #     "- You can list files and discover any SQLite (.db) databases in the working directory.\n"
    #     "- You can read files.\n"
    #     "- You can query any database using natural language.\n\n"

    #     "DATABASE WORKFLOW:\n"
    #     "1. If the user doesn't specify a database, first use 'list_available_databases' or 'list_files' "
    #     "to see what .db files exist.\n"
    #     "2. Use 'query_any_database' with the EXACT filename when querying a specific database.\n"
    #     "3. Use 'query_database' only when the user clearly wants the default student_grades.db.\n"
    #     "4. When exploring a new/unknown database, you may need to run exploratory queries to understand the schema.\n\n"

    #     "Best Practices:\n"
    #     "- Always be concise in your final answers.\n"
    #     "- Never try to manually format or summarize large result sets — just return the data.\n"
    #     "- Think step-by-step before calling tools.\n"
    #     "- If you're unsure about the schema, query the database to explore it."
    # ))
    #     ]
        
        self.messages = [
            SystemMessage(content=(
        f"You are an expert file and database assistant. "
        f"Current working directory: {self.working_dir}\n\n"

        "You are a ReAct agent. Think step-by-step before every action.\n\n"

        "REACT REASONING CYCLE:\n"
        "1. Thought: Understand the user request and plan what to do.\n"
        "2. Action: Use the right tool(s) if needed.\n"
        "3. Observation: Analyze the tool results carefully.\n"
        "4. Reflection: Decide if you need more information or can answer.\n\n"

        "AVAILABLE CAPABILITIES:\n"
        "- List files and discover SQLite databases\n"
        "- Read files\n"
        "- Query databases using natural language\n\n"

        "DATABASE WORKFLOW:\n"
        "1. If no database is specified, first use 'list_available_databases' or 'list_files'.\n"
        "2. Use 'query_any_database' with the exact filename for any non-default database.\n"
        "3. Use 'query_database' only for the default student_grades.db.\n\n"

        "BEST PRACTICES:\n"
        "- Be concise in your final answers.\n"
        "- Never guess. Use tools to verify.\n"
        "- After getting tool results, think about what they mean before replying.\n"
        "- Do not call tools unnecessarily once you have enough information.\n"
        
        "DATABASE WORKFLOW & RULES:\n"
        "1. NEVER explore database tables using raw SQL (e.g., SELECT * FROM sqlite_master).\n"
        "2. If you need to know which tables exist or what the columns are, you MUST use the 'get_database_schema' tool.\n"
    
    ))
        ]

        self._setup_tools2()
        # Bind the tools
        #self.llm_with_tools = self.llm.bind_tools(self.langchain_tools)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

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

    # USING raw JSON schemas directly
    def _setup_tools(self):
        self.langchain_tools = [
            {"type": "function", "function": {"name": "read_file",        "description": "Read the contents of a file.",        "parameters": ReadFileSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "list_files",       "description": "List all files in a directory.",       "parameters": ListFilesSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "query_database",   "description": "Query the default student_grades.db",  "parameters": QueryDatabaseSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "suggest_interesting_queries", "description": "Suggest 4-6 interesting questions.", "parameters": SuggestQueriesSchema.model_json_schema()}},
            {"type": "function", "function": {"name": "query_any_database","description": "Query ANY .db file in the working directory.", "parameters": QueryAnyDatabaseSchema.model_json_schema()}},
            {"type": "function", "function": {
                "name": "list_available_databases", 
                "description": "List only the SQLite .db database files available in the working directory. "
                              "Use this first when the user asks about available databases or doesn't specify which one.",
                "parameters": ListAvailableDatabasesSchema.model_json_schema()}},
        ]
    
    # USING StructuredTool.from_function for tighter langchain coupling  
    def _setup_tools2(self):
        print("NOW USING MODERN TOOL BINDINGS WITH LANGCHAIN!!")
        """Modern and more reliable tool binding"""
   
    
        self.tools = [
            StructuredTool.from_function(
                func=self.read_file,
                name="read_file",
                description="Read the contents of a file at the given path.",
                args_schema=ReadFileSchema,
            ),
            StructuredTool.from_function(
                func=self.list_files,
                name="list_files",
                description="List all files and directories in the given path.",
                args_schema=ListFilesSchema,
            ),
            StructuredTool.from_function(
                func=self.list_available_databases,
                name="list_available_databases",
                description="List only the SQLite .db database files in the working directory.",
                args_schema=ListAvailableDatabasesSchema,
            ),
            StructuredTool.from_function(
                func=self.query_database,
                name="query_database",
                description="Query the default student_grades.db database using natural language.",
                args_schema=QueryDatabaseSchema,
            ),
            StructuredTool.from_function(
                func=self.query_any_database,
                name="query_any_database",
                description="Query any .db file in the working directory using its exact filename.",
                args_schema=QueryAnyDatabaseSchema,
            ),
            StructuredTool.from_function(
                func=self.suggest_interesting_queries,
                name="suggest_interesting_queries",
                description="Suggest interesting natural language questions about the database.",
                args_schema=SuggestQueriesSchema,
            ),
            StructuredTool.from_function(
                func=self.get_database_schema,
                name="get_database_schema",
                description="Retrieve schema information, tables, and column DDL structures for a specific database.",
                args_schema=GetDatabaseSchemaSchema,
            )
        ]

        

    # Tool implementations

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
        
    def list_available_databases(self) -> str:
        """List only .db files in the working directory."""
        try:
            db_files = [
                f for f in sorted(os.listdir(self.working_dir))
                if f.lower().endswith(".db")
            ]
            if not db_files:
                return "No .db files found in the working directory."
            
            result = f"Found {len(db_files)} database(s) in {self.working_dir}:\n\n"
            for db in db_files:
                result += f"• {db}\n"
            return result.strip()
        except Exception as e:
            return f"Error listing databases: {str(e)}"

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
            schema = db.get_table_info()
            prompt = ChatPromptTemplate.from_template("""
            Given the schema, write a correct SQL query to answer the question.
            Return ONLY the SQL query - no explanation, no markdown.

            Schema:
            {schema}

            Question:
            {question}
            """)
            chain = prompt | self.llm | StrOutputParser()

            raw_sql = chain.invoke({
                "schema": schema,
                "question": question
            })

            # Clean common markdown fences
            generated_sql = raw_sql.strip()
            
            # INTERCEPT WITH SQLGLOT GUARDRAI.    -----NEW----
            validation = SQLGuardrail.validate_and_optimize(generated_sql)
            
            if not validation["valid"]:
                # We return the error *as an observation* to the agent
                return {
                    "sql": generated_sql,
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "error": f"Guardrail Blocked Execution. Reason: {validation['error']}"
                }
                
            
            # if generated_sql.startswith("```"):
            #     generated_sql = generated_sql.split("```")[1]
            #     if generated_sql.startswith("sql"):
            #         generated_sql = generated_sql[3:]
            #     generated_sql = generated_sql.strip()
            # elif generated_sql.lower().startswith("sql "):
            #     generated_sql = generated_sql[4:].strip()
               # sql = sql.split("```", 2)[1 if sql.startswith("```sql") else 0].strip()
               
            validated_sql = validation["sql"]   

            results = db._execute(validated_sql)  # returns list of dicts

            return {
                "sql": generated_sql,
                "columns": list(results[0].keys()) if results else [],
                "rows": [list(row.values()) for row in results],
                "row_count": len(results),
                "error": None
            }

        except Exception as e:
            return {
                "sql": generated_sql if 'generated_sql' in locals() else "",
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
            
    def get_database_schema(self, db_filename: str) -> str:
        """Safely retrieve table schemas (CREATE TABLE statements) for a database file."""
        full_path = os.path.join(self.working_dir, db_filename)
        if not os.path.exists(full_path) or not db_filename.lower().endswith(".db"):
            return f"Error: Database file '{db_filename}' not found or is not a .db file."
        try:
            # Initialize the SQLDatabase instance on-the-fly for the requested DB
            db = SQLDatabase.from_uri(f"sqlite:///{full_path}")
            schema_info = db.get_table_info()
            if not schema_info:
                return f"Database '{db_filename}' is empty or has no tables."
            return schema_info
        except Exception as e:
            return f"Error reading schema metadata for '{db_filename}': {str(e)}"

    # Main chat method 

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
    
    
class SQLGuardrail:
    FORBIDDEN_NODES = (exp.Drop, exp.Delete, exp.Update, exp.Insert, exp.Alter)
    
    @classmethod
    def _clean_raw_llm_string(cls, sql_str: str) -> str:
        """Strips markdown code fences, leading 'sql' blocks, and extra whitespace."""
        cleaned = sql_str.strip()
        
        # 1. Strip markdown fences if they exist (e.g., ```sql ... ``` or ``` ... ```)
        cleaned = re.sub(r"^```(?:sql)?\s*","", cleaned,flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        
        # 2. Check if the string starts with the literal prefix "sql" and strip it
        if cleaned.lower().startswith("sql"):
                cleaned = cleaned[3:].strip()
        
        # 3. Detect and strip wrapping double or single quotes around the entire output
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
                cleaned = cleaned[1:-1].strip()
        
        return cleaned.strip()
            
            
    
    @classmethod
    def validate_and_optimize(cls, sql_str: str) -> dict:
        """
        Parses and verifies the AST of a generated SQL string.
        Returns a dict indicating validity, errors or the sanitized SQL.
        """
        try:
            # Parse into an Abstrat Syntax Tree (AST)
            ast = parse_one(sql_str, read="sqlite")
        except ParseError as e:
            return {"valid": False, "error": f"SQL Syntax Error: {str(e)}"}
        
        # Enforce Read_only Boundaries using expression types
        for forbidden_type in cls.FORBIDDEN_NODES:
            if list(ast.find_all(forbidden_type)):
                return {
                    "valid": False,
                    "error": f"Security Violation: Mutating operation '{forbidden_type.__name__}' detected."
                }
                
        # Programmatically inject a LIMIT clause if it doesn't exist
        # We look for a Select expression node in the AST
        select_node = ast.find(exp.Select)
        if select_node and not ast.find(exp.Limit):
            # Mutate the AST to add a Limit node safely
            ast = ast.limit(100)

        return {
            "valid": True,
            "sql": ast.sql(dialect="sqlite")
        }
    
    
    
    
    
    
    


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