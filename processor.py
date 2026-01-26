import os
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
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

    def summarize(self, text: str) -> SummaryOutput:
        """Use Case 1: Summarization"""
        structured_llm = self.llm.with_structured_output(SummaryOutput)
        prompt = ChatPromptTemplate.from_template(
            "Summarize the following text into 3-6 bullet points and provide a key conclusion. "
            "Preserve main ideas and key facts.\n\nText: {text}"
        )
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