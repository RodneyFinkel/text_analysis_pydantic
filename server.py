import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
import uuid
from graph_core.graph import graph

app = FastAPI(title="Multi-Agent Supervisor API", version="1.0")

@app.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # In a production environment, this thread_id needs to be generated dynamically 
    # per user session to isolate their MemorySaver checkpointer state.
    # SESSION MANAGEMENT
    session_id = None
    working_dir = "."
       
    try:
         # First message from client can contain session_id and working_dir
        raw_data = await websocket.receive_text()
        data = json.loads(raw_data)
        
        session_id = data.get("session_id") or str(uuid.uuid4())
        working_dir = data.get("working_dir", ".")
        
        #Send confimation with assigned session_id
        await websocket.send_json({
                "type": "system",
                "node": "session",
                "session_id": session_id,
                "message": "Connected Succesfully"
                })
        
        config = {"configurable": {"thread_id": session_id}}
        
        # Main Loop to keep the Websocket connection alive
        while True:
            # 1. Wait for incoming user message
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            user_message = data.get("message")
            working_dir = data.get("working_dir", working_dir)
            
            if not user_message:
                continue

            # Send immediate acknowledgement
            await websocket.send_json({
                "type": "system", 
                "node": "system", 
                "message": "Processing request..."
            })

            # 2. Prepare the input state for LangGraph
            inputs = {
                "messages": [HumanMessage(content=user_message)],
                "db_results": [],
                "working_dir": working_dir
            }

            # 3. Stream the graph execution asynchronously
            #    graph.astream() yields the state updates from each node as it finishes
            async for output in graph.astream(inputs, config):
                # Output is a dict mapping the node_name to its state_update
                for node_name, state_update in output.items():
                    
                    # Extract the latest message content to send to the UI
                    latest_content = ""
                    if "messages" in state_update and state_update["messages"]:
                        last_msg = state_update["messages"][-1]
                        latest_content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

                    payload = {
                        "type": "update",
                        "node": node_name,
                        "message": latest_content
                    }
                    
                    # Push the telemetry back to the client
                    await websocket.send_json(payload)
            
            # 4. Signal that the routing loop has concluded
            await websocket.send_json({
                "type": "system", 
                "node": "FINISH", 
                "message": "Workflow complete."
            })

    except WebSocketDisconnect:
        print(f"Client disconnected (session {session_id})")
    except Exception as e:
        print(f"Error in session {session_id}: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    # Run the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)