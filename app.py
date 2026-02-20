import streamlit as st
import PyPDF2
from processor import TextAnalysisProcessor
from docx import Document


st.set_page_config(page_title="matrixDNA Analysis Tool", layout="centered")


@st.cache_resource
def get_processor():
    return TextAnalysisProcessor()

processor = get_processor()

st.title("Text Analysis and SQL Generator Tool")
st.markdown("Analyze text using and query your Database.\n\n" 
    "Use Cases:\n"
    "1. Summarize long documents into concise bullet points and a key conclusion.\n"
    "2. Extract key topics/themes from text with explanations.\n"
    "3. Classify user intent into predefined categories with confidence scores and reasoning.\n"
    "4. Generate and execute SQL queries against a database based on natural language questions."
)

#  sidebar
task = st.sidebar.selectbox("Choose Analysis Type", 
    ["Summarize Long Text", "Extract Key Topics", "Intent Classification", "Query Database"])

user_input = ""

# Handle inputs for Summarization and Topic extraction
if task in ["Summarize Long Text", "Extract Key Topics"]:
    input_type = st.radio("Input Source", ["Upload PDF", "Paste Text"])
    
    if input_type == "Upload PDF":
        uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
        if uploaded_file:
            reader = PyPDF2.PdfReader(uploaded_file)
            user_input = " ".join([page.extract_text() or "" for page in reader.pages])
    else:
        user_input = st.text_area("Paste text (at least 500 words for summary)", height=300)

# Handle inputs for Intent Classification and Query Database
if task == "Intent Classification":
    user_input = st.text_input("Enter a user message (1-3 sentences):")
elif task == "Query Database":
    user_input = st.text_area("Enter a natural language question about the student_grades.db database.", height=150)  
        

# Processing logic
if st.button("Run Analysis"):
    if not user_input.strip():
        st.error("Please provide valid input text.")
    else:
        with st.spinner("Processing with LLM..."):
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
                    
                elif task == "Query Database":
                    result = processor.query_database(user_input)
                    st.subheader("Generated SQL Query")
                    st.code(result["sql"], language="sql")
                    st.subheader("Query Results")
                    st.write(result["results"])
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")