from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests
import json
import re

app = FastAPI(title="Invoice Extractor")

class InvoiceExtract(BaseModel):
    vendor: str
    amount: float
    currency: str
    date: str

class Request(BaseModel):
    text: str

@app.post("/extract", response_model=InvoiceExtract)
async def extract_invoice(request: Request):
    if not request.text or len(request.text.strip()) < 5:
        raise HTTPException(status_code=422, detail="Text too short")

    prompt = f"""Extract exactly these fields from the invoice. Return ONLY clean JSON, no extra text.

Invoice:
{request.text}

JSON:"""

    try:
        resp = requests.post(
            "http://localhost:11434/v1/chat/completions",   # Render will need Ollama? Wait — Render free doesn't support Ollama easily.
            json={
                "model": "llama3.2:1b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0
            },
            timeout=60
        )
        content = resp.json()["choices"][0]["message"]["content"]
        json_str = re.search(r'\{.*\}', content, re.DOTALL).group(0)
        data = json.loads(json_str)
        return data
    except:
        raise HTTPException(status_code=422, detail="Extraction failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
