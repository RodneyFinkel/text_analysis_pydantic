from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from langchain_flask_agent2 import AIAgent 

load_dotenv()

app = Flask(__name__)

api_key = os.getenv("GROQ_API_KEY")
# You can set the initial directory the agent should watch here
agent = AIAgent(api_key=api_key, working_dir="./workspace")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get("message", "")
    
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    try:
        # The chat method handles the tool-loop logic internally
        response = agent.chat(user_input)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Ensure the workspace directory exists before starting
    if not os.path.exists("./workspace"):
        os.makedirs("./workspace")
    app.run(debug=True, port=5000)