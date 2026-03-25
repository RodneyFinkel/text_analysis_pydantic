import streamlit as st
import PyPDF2
import pandas as pd
from processor import TextAnalysisProcessor
from langchain_agent4 import AIAgent  # the refactored agent with structured DB output
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Tool Calling Agent", layout="wide")

# ─── Cached instances ──────────────────────────────────────────────────────────

@st.cache_resource
def get_processor():
    return TextAnalysisProcessor()

@st.cache_resource
def get_agent(working_dir: str):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not found in .env")
        st.stop()
    return AIAgent(api_key=api_key, working_dir=working_dir)

processor = get_processor()

# ─── UI ────────────────────────────────────────────────────────────────────────

st.title("matrixDNA Analysis Tool")
st.markdown(
    "Text analysis • Intent classification • Database querying • "
    "**Conversational AI Agent with multi-DB support**"
)

# Sidebar selector
task = st.sidebar.selectbox(
    "Choose Mode",
    [
        "Summarize Long Text",
        "Extract Key Topics",
        "Intent Classification",
        "Query Database (one-shot)",
        "Conversational AI Agent",
    ]
)

# ─── Input handling ────────────────────────────────────────────────────────────

user_input = ""

if task in ["Summarize Long Text", "Extract Key Topics"]:
    input_type = st.radio("Input Source", ["Upload PDF", "Paste Text"])

    if input_type == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
        if uploaded_file is not None:
            reader = PyPDF2.PdfReader(uploaded_file)
            user_input = " ".join(page.extract_text() or "" for page in reader.pages)
    else:
        user_input = st.text_area("Paste text (min ~500 words for summary)", height=300)

elif task == "Intent Classification":
    user_input = st.text_input("Enter a user message (1–3 sentences):")

elif task == "Query Database (one-shot)":
    user_input = st.text_area("🧠 Enter natural language question for student_grades.db", height=120)

elif task == "Conversational AI Agent":
    st.subheader("🛠️ File System + Multi-DB Conversational Agent")
    working_dir_input = st.sidebar.text_input("Working Directory", value=".", help="Folder with your .db files")

    # Agent instance
    if "agent" not in st.session_state or st.session_state.get("_last_working_dir") != working_dir_input:
        st.session_state.agent = get_agent(working_dir_input)
        st.session_state._last_working_dir = working_dir_input

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display conversation
    for msg in st.session_state.chat_history:
        role = msg["role"]
        content = msg["content"]
        with st.chat_message(role):
            if isinstance(content, dict) and content.get("type") == "db_result":
                res = content["result"]
                if res.get("error"):
                    st.error(res["error"])
                else:
                    if res.get("sql"):
                        st.code(res["sql"], language="sql")
                    if res.get("row_count", 0) > 0:
                        df = pd.DataFrame(res["rows"], columns=res["columns"])
                        st.dataframe(df, use_container_width=True)
                        st.caption(f"{res['row_count']} row{'s' if res['row_count'] != 1 else ''}")
                    else:
                        st.info("Query returned no rows.")
            else:
                st.markdown(content)

    # Chat input
    if prompt := st.chat_input("Ask about files, suggest queries, or query any .db file..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Agent thinking..."):
                result = st.session_state.agent.chat(prompt)

                if result["type"] == "text":
                    st.markdown(result["content"])
                    st.session_state.chat_history.append({"role": "assistant", "content": result["content"]})

                elif result["type"] == "db_result":
                    res = result["result"]
                    display_content = {"type": "db_result", "result": res}

                    if res.get("error"):
                        st.error(res["error"])
                    else:
                        if res.get("sql"):
                            st.code(res["sql"], language="sql")
                        if res.get("row_count", 0) > 0:
                            df = pd.DataFrame(res["rows"], columns=res["columns"])
                            st.dataframe(df, use_container_width=True)
                            st.caption(f"{res['row_count']} row{'s' if res['row_count'] != 1 else ''}")
                        else:
                            st.info("Query returned no rows.")

                    st.session_state.chat_history.append({"role": "assistant", "content": display_content})

# ─── One-shot processing (non-agent modes) ─────────────────────────────────────

if st.button("Run Analysis") and task != "Conversational AI Agent":
    if not user_input.strip():
        st.error("Please provide input.")
    else:
        with st.spinner("Processing..."):
            try:
                if task == "Summarize Long Text":
                    result = processor.summarize(user_input)
                    st.subheader("Summary Points")
                    for point in result.bullet_points:
                        st.write(f"- {point}")
                    st.success(f"**Conclusion:** {result.key_conclusion}")

                elif task == "Extract Key Topics":
                    result = processor.extract_topics(user_input)
                    st.subheader("Extracted Themes")
                    st.write(", ".join(result.topics))
                    st.info(f"**Methodology:** {result.explanation}")

                elif task == "Intent Classification":
                    result = processor.classify_intent(user_input)
                    st.metric("Predicted Intent", result.intent, f"{result.confidence_score:.2f} confidence")
                    st.write(f"**Reasoning:** {result.reasoning}")

                elif task == "Query Database (one-shot)":
                    st.subheader("Talk to student_grades.db")
                    result = processor.query_database(user_input)
                    st.subheader("Generated SQL")
                    st.code(result["sql"], language="sql")
                    st.subheader("Query Results")
                    if isinstance(result["results"], str) and "Error" in result["results"]:
                        st.error(result["results"])
                    else:
                        try:
                            df = pd.DataFrame(result["results"])
                            st.dataframe(df, use_container_width=True)
                        except Exception as e:
                            st.error(f"Display error: {str(e)}")

            except Exception as e:
                st.error(f"Processing error: {str(e)}")