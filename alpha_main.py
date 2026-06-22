import os 
import asyncio
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from graph_core.alpha_graph import graph

load_dotenv()

async def main():
    working_dir = "."
    config = {"configurable": {"thread_id": "default"}}
    
    print("LangGraph Agent System Ready (DB + FS)")
    print("Type 'exit', 'quit', or 'q' to stop.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ["exit", "quit", "q"]:
                print("👋 Goodbye!")
                break
                
            if not user_input:
                continue

            print("🤔 Agent thinking...\n")
            
            inputs = {
                "messages": [HumanMessage(content=user_input)],
                "working_dir": working_dir,
                "db_results": [],
                "fs_results": [],
                "research_data": [],
                "blog_post": None,
                "next_node": "FINISH",
                "recipient_email": None,
                "recipient_name": None,
                "email_target_type": None,
                "email_sent_status": False
            }
            
            result = await graph.ainvoke(inputs, config)
            
            # === SUPER FORGIVING EXTRACTION ===
            messages = result.get("messages", [])
            response_text = "No response generated."
            
            if messages:
                for msg in reversed(messages):
                    if isinstance(msg, AIMessage) and msg.content and msg.content.strip():
                        response_text = msg.content.strip()
                        break
                else:
                    # Fallback: take any string content
                    for msg in reversed(messages):
                        if hasattr(msg, 'content') and str(msg.content).strip():
                            response_text = str(msg.content).strip()
                            break
            
            print(f"Agent: {response_text}\n")
            
            # Debug
            db_count = len(result.get("db_results", []))
            fs_count = len(result.get("fs_results", []))
            if db_count > 0 or fs_count > 0:
                print(f"📊 State: DB={db_count} | FS={fs_count}\n")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())