GROQ_API_KEY is needed inside a .env file

# Create a virtual environment to keep dependencies isolated
python -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

Install all required libraries using the requirements.txt file provided in the repository:
pip install -r requirements.txt

Launch the Streamlit server to view the app in your browser:
streamlit run app.py

For the app to run correctly, ensure your folder looks like this:
.
├── .env                # API Keys (git-ignored)
├── app.py              # Streamlit UI logic
├── processor.py        # Pydantic schemas and LLM logic
├── dataset.csv         # The 50-example intent dataset
└── requirements.txt    # Project dependencies

Why Llama 3.3 70B Versatile?

Llama 3.3 70B's performance is comparable to much larger models. This model also scores high on benchmarks (92.1 on IFEval) for following user instructions. This is important  because it ensures the model adheres strictly to the constraints defined in the Pydantic schemas without chatter or formatting errors.

It is specifically tuned to excel at JSON mode and Function Calling

128K Context Window: Supports a very large 128,000-token context.  No need to build chunking or map-reduce logic.



Use Case 1:
Using Pydantic replaces traditional prompt-engineering for output formatting by providing a schema contract that forces the LLM to return valid, structured data. This was chosen to eliminate unpredictable text chatter and ensure type-safe validation (like forcing confidence scores in Use Case 3 to be floats). Moving logic from raw strings to Python objects makes the app becomes more robust. 

Use Case 2:
Again using pydantic instead of traditional prompt engineering ensured that the prompts where lightweight but effective.

Use Case 3:
Dataset: Created a CSV with 50 diverse short messages covering all labels (see intent_test.csv).
Dataset is tested using test_intents.py which will assemble the intent_test_results.csv
Handling ambiguous/not-fitting: Prompt explicitly instructs 'Ambiguous' for unclear, 'Uncategorized' for unfit.
Confusion discussion: Mismatches mostly on edge cases (e.g., vague complaints misclassified as technical)."
Qualitative: limitation: prompt could be more robust with examples.


POSSIBLE IMPROVEMENTS

Few-Shot Prompting: The current system uses "Zero-Shot" (no examples). Adding 3-5 Examples inside the processor.py prompts would reduce misclassifications for edge cases in the Intent task.

Chunked Processing: For the Summarization task, implementing a Map-Reduce approach—summarizing individual chapters first and then combining them—would resolve the context window limitations for long documents.

Confidence Thresholds: Implement a logic gate where if the confidence_score is below 0.6, the system automatically routes the message instead of attempting to categorize it.

Multi Modal: Upgrading the type and variety of documents able to be analysed. OCR pipeline, Docling.


