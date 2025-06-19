import os
import requests
import re
from typing import Optional
from pydantic import BaseModel
from google import genai


def download(url, filename, replace=False):
    """Download the file (check if it already exists)"""
    if os.path.exists(filename) and not replace:
        print(f"File {filename} already exists")
        return
    response = requests.get(url)
    with open(filename, "wb") as f:
        f.write(response.content)


def run_gemini(
    prompt,
    model="gemini-2.5-flash",
    response_model: Optional[BaseModel] = None,
    temperature: float = 0.0,
) -> BaseModel | str:
    """Get a response from the Gemini API"""
    client = genai.Client()
    if response_model is not None:
        config = {
            "response_mime_type": "application/json",
            "response_schema": response_model.model_json_schema(),
            "temperature": temperature,
        }
    else:
        config = {"response_mime_type": "text/plain"}
    resp = client.models.generate_content(model=model, contents=prompt, config=config)
    text = resp.candidates[0].content.parts[0].text
    if response_model is not None:
        return response_model.model_validate_json(text)
    else:
        return text


def format_template(template_path, **kwargs):
    """Format a template with the given kwargs"""
    template = template_path.read_text()
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", value)
    return template
