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

st.markdown("<h1 style='color: #ADD8E6;'>Tool Calling Agent Demo</h1>", unsafe_allow_html=True)
st.markdown(
    "<span style='color: #ADD8E6;'>Text analysis • Intent classification • Database querying • "
    "**Conversational AI Agent with multi-DB support for natural language processing**</span>",
    unsafe_allow_html=True
)

# Sidebar selector
task = st.sidebar.selectbox(
    "Choose Mode",
    [
        "Summarize Long Text",
        "Extract Key Topics",
        "Intent Classification",
        "Query Database (one-shot)",
        "Database Explorer",           # ← NEW
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
    
# ====================== NEW: DATABASE EXPLORER ======================
elif task == "Database Explorer":
    st.subheader("🔍 Database Explorer")
    st.markdown("Discover, inspect, and query all SQLite databases in the working directory.")

    working_dir_input = st.sidebar.text_input("Working Directory", value=".", key="explorer_wd")

    # Initialize explorer agent
    if "explorer_agent" not in st.session_state or st.session_state.get("_explorer_dir") != working_dir_input:
        st.session_state.explorer_agent = get_agent(working_dir_input)
        st.session_state._explorer_dir = working_dir_input

    agent = st.session_state.explorer_agent

    # Auto-detect databases
    try:
        db_files = [f for f in sorted(os.listdir(working_dir_input)) if f.lower().endswith(".db")]
    except Exception:
        db_files = []

    if not db_files:
        st.warning("No `.db` files found in the directory. Run your creation scripts to generate databases.")
    else:
        selected_db = st.selectbox("Select Database to Explore", db_files, key="selected_db_explorer")

        st.caption(f"📁 **Currently exploring:** {selected_db}")

        # Quick Action Buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📋 Quick Schema", type="primary"):
                with st.spinner("Analyzing database schema..."):
                    prompt = f"Using the database '{selected_db}', list all tables with their columns and data types."
                    result = agent.chat(prompt)
                    if result["type"] == "text":
                        st.markdown(result["content"])
                    elif result["type"] == "db_result":
                        res = result["result"]
                        if res.error:
                            st.error(res.error)
                        else:
                            if res.sql:
                                with st.expander("Generated SQL", expanded=True):
                                    st.code(res.sql, language="sql")
                            if res.rows:
                                df = pd.DataFrame(res.rows, columns=res.columns)
                                st.dataframe(df, use_container_width=True)

        with col2:
            if st.button("📊 Tables Overview"):
                with st.spinner("Fetching overview..."):
                    result = agent.chat(f"Using '{selected_db}', list all tables with row counts if possible.")
                    if result["type"] == "text":
                        st.markdown(result["content"])

        with col3:
            if st.button("🔄 Refresh"):
                st.rerun()

        st.divider()

        # Natural Language Query
        st.subheader("💬 Natural Language Query")
        nl_question = st.text_area(
            "Ask anything about this database", 
            height=120,
            placeholder="Show the top 10 goal scorers this season..."
        )

        if st.button("🚀 Run Query", type="primary"):
            if nl_question.strip():
                with st.spinner(f"Querying {selected_db}..."):
                    prompt = f"Using the database file '{selected_db}', {nl_question}"
                    result = agent.chat(prompt)

                    if result["type"] == "text":
                        st.markdown(result["content"])
                    elif result["type"] == "db_result":
                        res = result["result"]
                        if res.error:
                            st.error(res.error)
                        else:
                            if res.sql:
                                with st.expander("🔎 Generated SQL", expanded=True):
                                    st.code(res.sql, language="sql")
                            if res.rows:
                                df = pd.DataFrame(res.rows, columns=res.columns)
                                st.dataframe(df, use_container_width=True)
                                st.caption(f"✅ {res.row_count} rows returned")
                            else:
                                st.info("Query returned no rows.")

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
                
                # FIX: Dot notation for the Pydantic object in history
                if res.error:
                    st.error(res.error)
                else:
                    if res.sql:
                        st.code(res.sql, language="sql")
                    if res.row_count > 0:
                        df = pd.DataFrame(res.rows, columns=res.columns)
                        st.dataframe(df, use_container_width=True)
                        st.caption(f"{res.row_count} row{'s' if res.row_count != 1 else ''}")
                
                # if res.get("error"):
                #     st.error(res["error"])
                # else:
                #     if res.get("sql"):
                #         st.code(res["sql"], language="sql")
                #     if res.get("row_count", 0) > 0:
                #         df = pd.DataFrame(res["rows"], columns=res["columns"])
                #         st.dataframe(df, use_container_width=True)
                #         st.caption(f"{res['row_count']} row{'s' if res['row_count'] != 1 else ''}")
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

                    # if res.get("error"):
                    #     st.error(res["error"])
                    
                    # 1. Check for errors (Attribute access, not .get)
                    if res.error:
                        st.error(f"Database Error: {res.error}")
                    else:
                        # 2. Display SQL (Attribute access)
                        if res.sql:
                            with st.expander("View Generated SQL"):                                
                                st.code(res.sql, language="sql")
                        #if res.get("sql"):
                            #st.code(res["sql"], language="sql")
                            
                        # if res.get("row_count", 0) > 0:
                        #     df = pd.DataFrame(res["rows"], columns=res["columns"])
                        #     st.dataframe(df, use_container_width=True)
                        #     st.caption(f"{res.row_count} row{'s' if res.row_count != 1 else ''}")
                            
                        # 3. Display Data (Attribute access)
                        if res.rows:
                            df = pd.DataFrame(res.rows, columns=res.columns)
                            st.dataframe(df, use_container_width=True)
                            st.caption(f"Query returned {res.row_count} rows.")
                        else:
                            st.info("Query returned no rows.")

                    st.session_state.chat_history.append({"role": "assistant", "content": display_content})

# ─── One-shot processing (non-agent modes) ─────────────────────────────────────

if st.button("Run Analysis") and task not in ["Conversational AI Agent", "Database Explorer"]:
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