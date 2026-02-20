from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

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
            model="llama-3.3-70b-versatile",
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 4000,
            chunk_overlap = 200
        )
              
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
    
        