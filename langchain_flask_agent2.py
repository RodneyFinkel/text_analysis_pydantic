# /// script
# requires-python = ">=3.12"
# dependencies = [
#      "langchain-groq",
#      "pydantic",
#      "python-dotenv",
# ]
# ///

import os
import sys
from typing import List, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

load_dotenv()

class Tool(BaseModel):
    """Explicit schema management."""
    name: str
    description: str
    input_schema: Dict[str, Any]

class AIAgent:
    def __init__(self, api_key: str, working_dir: str = "."):
        
        self.llm = ChatGroq(
            groq_api_key=api_key, 
            model_name="llama-3.3-70b-versatile",
            temperature=0
        )
        self.working_dir = os.path.abspath(working_dir)
        self.messages = [
            SystemMessage(content=f"You are a file assistant. Working directory: {self.working_dir}")
        ]
        self.tools: List[Tool] = []
        self._setup_tools()
        
        # Convert our custom Tool objects to LangChain-compatible dicts
        self.langchain_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                }
            } for t in self.tools
        ]
        self.llm_with_tools = self.llm.bind_tools(self.langchain_tools) # Bind the tools to the LLM
        print(f"Agent initialized with {len(self.tools)} tools in {self.working_dir}")

    def _setup_tools(self):
        """Explicit tool definitions."""
        self.tools = [
            Tool(
                name="read_file",
                description="Read the contents of a file at the specified path",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            Tool(
                name="list_files",
                description="List all files and directories in the specified path",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string", "default": "."}},
                    "required": [],
                },
            ),
            Tool(
                name="edit_file",
                description="Edit a file by replacing old_text with new_text.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                    "required": ["path", "new_text"],
                },
            ),
        ]

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Explicit routing logic."""
        try:
            if tool_name == "read_file":
                return self._read_file(tool_input["path"])
            elif tool_name == "list_files":       
                return self._list_files(tool_input.get("path", "."))
            elif tool_name == "edit_file":
                return self._edit_file(
                    tool_input["path"], 
                    tool_input.get("old_text", ""), 
                    tool_input["new_text"]
                )
            return f"Error: Unknown tool '{tool_name}'"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def _read_file(self, path: str) -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error: {str(e)}"

    def _list_files(self, path: str) -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            items = os.listdir(full_path)
            return "\n".join([f"[DIR] {i}/" if os.path.isdir(os.path.join(full_path, i)) else f"[FILE] {i}" for i in items])
        except Exception as e:
            return f"Error: {str(e)}"

    def _edit_file(self, path: str, old_text: str, new_text: str) -> str:
        full_path = os.path.join(self.working_dir, path)
        try:
            if os.path.exists(full_path) and old_text:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if old_text not in content:
                    return f"Text not found: {old_text}"
                content = content.replace(old_text, new_text)
            else:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                content = new_text
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully updated {path}"
        except Exception as e:
            return f"Error: {str(e)}"

    def chat(self, user_input: str) -> str:
        """Main Agent Loop - Explicit tool execution."""
        self.messages.append(HumanMessage(content=user_input))

        while True:
            response = self.llm_with_tools.invoke(self.messages)
            self.messages.append(response)

            # If no tool calls, return text content
            if not response.tool_calls:
                return response.content

            # Process tool calls explicitly
            for tool_call in response.tool_calls:
                result = self._execute_tool(tool_call["name"], tool_call["args"])
                
                # Feedback to the LLM
                self.messages.append(ToolMessage(
                    tool_call_id=tool_call["id"],
                    content=str(result)
                ))