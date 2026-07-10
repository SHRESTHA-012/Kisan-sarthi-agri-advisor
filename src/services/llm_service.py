"""
LLM service — all Groq calls are isolated here.
To swap models, only this file needs changing.
"""
import os
from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")


def chat(messages: list, temperature: float = 0.4, top_p: float = 0.9) -> str:
    """
    Send a chat request to Groq's hosted LLM.

    Args:
        messages: List of {role, content} dicts (OpenAI-compatible format)
        temperature: Sampling temperature
        top_p: Nucleus sampling

    Returns:
        Response string from the model
    """
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=temperature,
        top_p=top_p,
        max_tokens=512,
        messages=messages,
    )
    return response.choices[0].message.content


def vision_chat(prompt: str, image_b64: str, temperature: float = 0.2) -> str:
    """
    Send an image + prompt to Groq's vision model.

    Args:
        prompt: Text prompt to accompany the image
        image_b64: Base64-encoded image string
        temperature: Sampling temperature

    Returns:
        Response string from the vision model
    """
    response = client.chat.completions.create(
        model=GROQ_VISION_MODEL,
        temperature=temperature,
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
            ],
        }],
    )
    return response.choices[0].message.content
