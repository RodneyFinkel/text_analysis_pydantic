import gradio as gr
from transformers import ViltProcessor, ViltForQuestionAnswering
from PIL import Image


processor = ViltProcessor.from_pretrained("dandelin/vilt-b32-finetuned-vqa")
model = ViltForQuestionAnswering.from_pretrained("dandelin/vilt-b32-finetuned-vqa")

def answer_question(image, text):
    try:
        encoding = processor(image, text, return_tensors="pt")
        outputs = model(**encoding)
        logits = outputs.logits
        idx = logits.argmax(-1).item()
        answer = model.config.id2label[idx]
        return answer
    except Exception as e:
        print(f"Error processing the input: {e}")
        return "Error occurred while processing the input."
    
iface = gr.Interface(
    fn=answer_question,
    inputs=[gr.Image(type="pil"), gr.Textbox(label="Question")],
    outputs=gr.Textbox(label="Answer"),
    title="Multimodal Question Answering",
    description="Upload an image and ask a question about it. The model will provide an answer based on the content of the image and the question.",
)
iface.launch()  