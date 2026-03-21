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
import argparse
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler("agent.log")],
)

class AIAgent:
    def __init__(self, api_key: str, working_dir: str = "."):
        self.llm = ChatGroq(
            groq_api_key=api_key, 
            model_name="llama-3.3-70b-versatile",
            temperature=0
        )
        self.working_dir = os.path.abspath(working_dir)
        self.messages = [SystemMessage(content=f"You are a helpful file assistant. Your working directory is {self.working_dir}")]
        
        # Define tools in a format Groq/LangChain understands
        self._setup_tools()
        self.llm_with_tools = self.llm.bind_tools(self.tools) # Instead of converting to dicts, we can directly bind the functions
        print(f"Agent initialized with {len(self.tools)} tools in {self.working_dir}")

    def _setup_tools(self):
        # We define functions directly; LangChain converts them to schemas automatically
        def read_file(path: str) -> str:
            """Read the contents of a file at the specified path."""
            full_path = os.path.join(self.working_dir, path)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"Error reading file: {str(e)}"

        def list_files(directory: str = ".") -> str:
            """List files in the specified directory."""
            full_path = os.path.join(self.working_dir, directory)
            try:
                files = os.listdir(full_path)
                return "\n".join(files)
            except Exception as e:
                return f"Error listing files: {str(e)}"

        # Store as a list of functions
        self.tools = [read_file, list_files]
        self.tool_map = {t.__name__: t for t in self.tools}

    def chat(self, user_input: str) -> str:
        self.messages.append(HumanMessage(content=user_input))

        while True:
            # 1. Get response from Groq
            response = self.llm_with_tools.invoke(self.messages)
            self.messages.append(response)

            # 2. If the model doesn't want to use tools, return the text
            if not response.tool_calls:
                return response.content

            # 3. Handle Tool Calls
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                
                # Execute the actual Python function
                result = self.tool_map[tool_name](**tool_args)
                
                # Add the result back to the conversation
                self.messages.append(ToolMessage(
                    tool_call_id=tool_call["id"],
                    content=str(result)
                ))
            
            # The loop continues to let the LLM analyze the tool results

def main():
    parser = argparse.ArgumentParser(description="AI Agent using Groq and LangChain")
    parser.add_argument("--api-key", help="Groq API key (or set GROQ_API_KEY env var)")
    parser.add_argument("--directory", default=".", help="Working directory for the agent")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Error: Provide GROQ_API_KEY via flag or .env file.")
        sys.exit(1)

    target_dir = args.directory
    if not os.path.isdir(target_dir):
        print(f"Error: Directory '{target_dir}' not found.")
        sys.exit(1)

    agent = AIAgent(api_key, working_dir=target_dir)

    print("\nGroq-Powered File Assistant")
    print("===========================")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue

            print("\nAssistant: ", end="", flush=True)
            answer = agent.chat(user_input)
            print(answer + "\n")

        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()