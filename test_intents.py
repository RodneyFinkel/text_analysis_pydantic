import os
import pandas as pd
from dotenv import load_dotenv
from processor import TextAnalysisProcessor  


load_dotenv()

# Initialize processor 
processor = TextAnalysisProcessor()

# Load test dataset
csv_file = 'intent_test.csv'
if not os.path.exists(csv_file):
    raise FileNotFoundError(f"{csv_file} not found. Create it with the provided examples.")

df = pd.read_csv(csv_file)

print(f"Loaded {len(df)} test examples.")

results = []
correct_count = 0

for idx, row in df.iterrows():
    message = row['message']
    target = row['target_intent']
    
    try:
        result = processor.classify_intent(message)
        predicted = result.intent
        conf = result.confidence_score
        reasoning = result.reasoning
        
        is_correct = predicted.strip().lower() == target.strip().lower()  # Case-insensitive
        if is_correct:
            correct_count += 1
        
        results.append({
            'message': message,
            'target': target,
            'predicted': predicted,
            'confidence': f"{conf:.2f}",
            'reasoning': reasoning,
            'correct': is_correct
        })
        
        print(f"Processed: {message[:50]}... | Predicted: {predicted} | Target: {target} | Correct: {is_correct}")
    
    except Exception as e:
        print(f"Error on message '{message[:50]}...': {str(e)}")
        results.append({
            'message': message,
            'target': target,
            'error': str(e)
        })

# Save results
results_df = pd.DataFrame(results)
results_df.to_csv('intent_test_results.csv', index=False)
print("\nResults saved to 'intent_test_results.csv'")


# Calculate Accuracy
total = len(results_df)
accuracy = (correct_count / total) * 100 if total > 0 else 0
print(f"Accuracy: {accuracy:.2f}% ({correct_count}/{total} correct)")

# --- FIXED SECTION: Safe Mismatch Printing ---
mismatches = results_df[results_df['correct'] == False]

if not mismatches.empty:
    print("\nMismatches (Confusion Cases):")
    # Define desired columns
    desired_cols = ['message', 'target', 'predicted', 'confidence', 'reasoning', 'error']
    # Only select columns that actually exist in the DataFrame
    available_cols = [col for col in desired_cols if col in mismatches.columns]
    print(mismatches[available_cols])
else:
    print("\nNo mismatches found! Perfect accuracy.")