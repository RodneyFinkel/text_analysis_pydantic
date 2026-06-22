import os 
import asyncio
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph_core.graph import graph

async def main():
    working_dir = "."
    config = {"configurable": {"thread_id": "default"}}
    
    print("LangGraph agent ready")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ["exit", "quit", "q"]:
                print("👋 Goodbye!")
                break
                
            if not user_input:
                continue

            print("🤔 Agent thinking...")
            
            # Prepare input for LangGraph
            inputs = {
                "messages": [HumanMessage(content=user_input)],
                "db_results": [],
                "working_dir": working_dir,
                "research_data": [],
                "blog_post": None,
                "next_node": "FINISH" # default to FINISH, supervisor will update if needed
            }
            
            # Run the graph
            result = await graph.ainvoke(inputs, config)
            
            # Extract response
            last_message = result["messages"][-1]
            response = last_message.content if hasattr(last_message, "content") else str(last_message)
            
            print(f"Agent: {response}\n")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        
if __name__ == "__main__":
    asyncio.run(main())
        
    