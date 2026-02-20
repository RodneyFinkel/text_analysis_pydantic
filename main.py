from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import PyPDF2
from processor import TextAnalysisProcessor

app = FastAPI(title="matrixDNA Text Analysis API")

processor = TextAnalysisProcessor()


def extract_text_from_pdf(uploaded_file: UploadFile) -> str:
    reader = PyPDF2.PdfReader(uploaded_file.file)
    return " ".join(page.extract_text() or "" for page in reader.pages)


@app.post("/summarize")
async def summarize(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    if file:
        user_input = extract_text_from_pdf(file)
    elif text:
        user_input = text
    else:
        raise HTTPException(status_code=400, detail="Provide text or PDF file.")

    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Input text is empty.")

    return processor.summarize(user_input)


@app.post("/topics")
async def extract_topics(
    text: str = Form(None),
    file: UploadFile = File(None)
):
    if file:
        user_input = extract_text_from_pdf(file)
    elif text:
        user_input = text
    else:
        raise HTTPException(status_code=400, detail="Provide text or PDF file.")

    if not user_input.strip():
        raise HTTPException(status_code=400, detail="Input text is empty.")

    return processor.extract_topics(user_input)


@app.post("/intent")
async def classify_intent(request: TextRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Input text is empty.")

    return processor.classify_intent(request.text)
