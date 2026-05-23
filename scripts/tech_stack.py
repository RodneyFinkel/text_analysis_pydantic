import streamlit as st

def display_tech_stack():
    st.markdown("## 🛠️ Tech Stack")
    st.markdown("---")

    # You can adjust column widths as needed
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.markdown("**Languages & Core**")
        st.markdown("""
        ![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
        ![SQL](https://img.shields.io/badge/SQL-4479A1?logo=sql&logoColor=white)
        ![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)
        """)

        st.markdown("**AI & LLM Ecosystem**")
        st.markdown("""
        ![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?logo=langchain&logoColor=white)
        ![LangGraph](https://img.shields.io/badge/LangGraph-000000?logo=langchain&logoColor=white)
        ![Groq](https://img.shields.io/badge/Groq-00A3FF?logo=groq&logoColor=white)
        ![RAG](https://img.shields.io/badge/RAG-FF6B6B?logo=ai&logoColor=white)
        ![HuggingFace](https://img.shields.io/badge/Hugging%20Face-FFD21E?logo=huggingface&logoColor=black)
        """)

    with col2:
        st.markdown("**Databases & Data**")
        st.markdown("""
        ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
        ![MySQL](https://img.shields.io/badge/MySQL-4479A1?logo=mysql&logoColor=white)
        ![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
        ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-FF4B4B?logo=sqlalchemy&logoColor=white)
        ![ChromaDB](https://img.shields.io/badge/ChromaDB-000000?logo=vector&logoColor=white)
        ![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
        """)

        st.markdown("**Machine Learning & Analytics**")
        st.markdown("""
        ![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikit-learn&logoColor=white)
        ![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)
        ![NumPy](https://img.shields.io/badge/NumPy-013243?logo=numpy&logoColor=white)
        ![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
        """)

    with col3:
        st.markdown("**Backend & APIs**")
        st.markdown("""
        ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
        ![Flask](https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=white)
        ![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
        """)

        st.markdown("**DevOps & Infrastructure**")
        st.markdown("""
        ![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
        ![Gunicorn](https://img.shields.io/badge/Gunicorn-499848?logo=gunicorn&logoColor=white)
        ![Redis](https://img.shields.io/badge/Redis-DC382D?logo=redis&logoColor=white)
        """)

        st.markdown("**Data Extraction & Automation**")
        st.markdown("""
        ![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-8CB0A4?logo=python&logoColor=white)
        ![yfinance](https://img.shields.io/badge/yfinance-000000?logo=yahoo&logoColor=white)
        """)

    st.markdown("---")
    st.caption("**Demonstrated through production-grade projects in AI, RAG, multi-agent systems, and quantitative finance.**")

# Call this function in your main landing page
if __name__ == "__main__":
    st.title("Your Name - AI/ML Engineer")
    display_tech_stack()