import os
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

# Pydantic Schemas for Structured Output

class SummaryOutput(BaseModel):
    """Schema for Use Case 1: Summarization"""
    bullet_points: List[str] = Field(description="Exactly 3 to 6 concise summary points.")
    key_conclusion: str = Field(description="A single sentence representing the main takeaway.")

class TopicOutput(BaseModel):
    """Schema for Use Case 2: Topic Extraction"""
    topics: List[str] = Field(description="3 to 7 distinct themes, each 1-3 words.")
    explanation: str = Field(description="A brief explanation of how these topics were identified.")

class IntentOutput(BaseModel):
    """Schema for Use Case 3: Intent Classification"""
    intent: str = Field(description="The category: Technical issue, Billing question, Feature request, Complaint, General inquiry, Uncategorized, or Ambiguous.")
    confidence_score: float = Field(description="Confidence score between 0 and 1.")
    reasoning: str = Field(description="The logic used to classify the user message.")



class TextAnalysisProcessor:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0, 
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.db = SQLDatabase.from_uri("sqlite:///student_grades.db")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 4000,
            chunk_overlap = 200
        )

    def summarize(self, text: str) -> SummaryOutput:
        """Use Case 1: Summarization"""
        structured_llm = self.llm.with_structured_output(SummaryOutput)
        prompt = ChatPromptTemplate.from_template(
            "Summarize the following text into 3-6 bullet points and provide a key conclusion. "
            "Preserve main ideas and key facts.\n\nText: {text}"
        )
        chain = prompt | structured_llm
        return chain.invoke({"text": text})
    
    def summarize2(self, text: str, depth: int = 0) -> SummaryOutput:
        MAX_DEPTH = 2
        if len(text) > 6000 and depth < MAX_DEPTH:
            chunks = self.text_splitter.split_text(text)
            # make partial summaries a list
            partial_summaries = [self.summarize2(chunk, depth + 1 ).key_conclusion for chunk in chunks] # each partial summary is a pydantic object and the key conclussion is extracted from it
            # combined text inserts a new instuction: 
            # " ".join(partial_summaries) just feeds the concatenated summaries as plain text with no extra instruction, so the model may treat it as one long passage and not perform an explicit synthesis step.
            combined_text = "Combine these summaries into a final coherent summary:\n" + "\n".join(partial_summaries)
            return self.summarize2(combined_text, depth + 1)
        
        
        prompt = ChatPromptTemplate.from_template(
            "Summarize the following text into 3-6 bullet points and provide a key conclusion. "
            "Preserve main ideas and key facts.\n\nText: {text}"
        )
        structured_llm = self.llm.with_structured_output(SummaryOutput)
        chain = prompt | structured_llm
        return chain.invoke({"text": text})

    def extract_topics(self, text: str) -> TopicOutput:
        """Use Case 2: Topic Extraction"""
        structured_llm = self.llm.with_structured_output(TopicOutput)
        prompt = ChatPromptTemplate.from_template(
            "Identify 3-7 key topics from the text. Each topic must be 1-3 words. "
            "Ensure topics are meaningful and distinct.\n\nText: {text}"
        )
        chain = prompt | structured_llm
        return chain.invoke({"text": text})

    def classify_intent(self, message: str) -> IntentOutput:
        """Use Case 3: Intent Classification"""
        structured_llm = self.llm.with_structured_output(IntentOutput)
        prompt = ChatPromptTemplate.from_template(
            "Classify the intent of the following user message: '{message}'.\n"
            "Use labels: Technical issue, Billing question, Feature request, Complaint, General inquiry. "
            "Label as 'Ambiguous' if unclear or 'Uncategorized' if it doesn't fit."
        )
        chain = prompt | structured_llm
        return chain.invoke({"message": message})
    
    def query_database(self, query: str) -> dict:
        """Execute an SQL query against the student_grades.db database.
        
        Returns a dict with 'sql' and 'results' keys.
        """
        try:
            # Prompt (LCEL Style)
            prompt = ChatPromptTemplate.from_template("""
            You are a senior data analyst and SQL expert.

            Given the database schema below, write a correct SQL query
            that answers the user's question.

            Rules:
            - Use only the tables and columns in the schema
            - Do NOT explain anything
            - Return ONLY the SQL query

            Schema:
            {schema}

            Question:
            {question}
            """)

            # LCEL Runnable Pipeline
            sql_chain = (
                prompt
                | self.llm
                | StrOutputParser()
            )

            schema = self.db.get_table_info()
            generated_sql = sql_chain.invoke({"schema": schema, "question": query})
            
            # Clean up markdown formatting if present
            generated_sql = generated_sql.strip()
            if generated_sql.startswith("```"):
                generated_sql = generated_sql.split("```")[1]
                if generated_sql.startswith("sql"):
                    generated_sql = generated_sql[3:]
                generated_sql = generated_sql.strip()
            
            # Execute the generated SQL and return both SQL and results
            results = self.db.run(generated_sql)
            return {"sql": generated_sql, "results": results}
        except Exception as e:
            return {"sql": "", "results": f"Error executing database query: {str(e)}"}  