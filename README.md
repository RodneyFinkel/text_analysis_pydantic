GROQ_API_KEY is needed inside a .env file
Clone the repository

# Create a virtual environment
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

Alternatively use this link for a live demo: 

For the app to run correctly, ensure your folder looks like this:
.
├── .env                # API Keys (git-ignored)
├── app.py              # Streamlit UI logic
├── processor.py        # Pydantic schemas and LLM logic
├── dataset.csv         # The 50-example intent dataset
└── requirements.txt    # Project dependencies

<img width="1902" height="899" alt="Screenshot 2026-02-20 at 21 20 06" src="https://github.com/user-attachments/assets/f02b4832-e197-4977-8545-5c661ec6755d" />

<img width="1909" height="954" alt="Screenshot 2026-02-20 at 21 20 38" src="https://github.com/user-attachments/assets/3018ad5d-e9f4-47c0-bf95-6c1610c21978" />

<img width="1909" height="954" alt="Screenshot 2026-02-20 at 21 21 04" src="https://github.com/user-attachments/assets/7a9cf355-75b8-40e7-9836-f42fb399917c" />

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


