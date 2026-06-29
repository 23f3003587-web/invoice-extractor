from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import requests
import json
import re

app = FastAPI()

class InvoiceExtract(BaseModel):
    vendor: str = Field(..., min_length=2)
    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")

class Request(BaseModel):
    text: str

@app.post("/extract", response_model=InvoiceExtract)
async def extract_invoice(request: Request):
    if not request.text or len(request.text.strip()) < 10:
        raise HTTPException(status_code=422, detail="Text too short")

    prompt = f"""Extract invoice details. Return **only** valid JSON with these exact keys. No extra text.

Text: {request.text}

Output:"""

    try:
        # Use Ollama if local, or replace with Groq/OpenAI later
        resp = requests.post(
            "http://localhost:11434/v1/chat/completions",
            json={
                "model": "llama3.2:1b",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 300
            },
            timeout=45
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Robust JSON extraction
        match = re.search(r'(\{.*?\})', content, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = match.group(1)
        else:
            json_str = content.strip()

        data = json.loads(json_str)

        # Fallback fixes
        if isinstance(data.get("amount"), str):
            data["amount"] = float(re.sub(r'[^0-9.]', '', data["amount"]))

        if "date" in data:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(data["date"]))
            if date_match:
                data["date"] = date_match.group(1)

        return data

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
