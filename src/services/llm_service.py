"""
LLM service — all Ollama calls are isolated here.
To swap Mistral → GPT-4 or Gemini, only this file needs changing.
"""
import os
import ollama

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")


def chat(messages: list, temperature: float = 0.4, top_p: float = 0.9) -> str:
    """
    Send a chat request to the local Ollama LLM.

    Args:
        messages: List of {role, content} dicts (OpenAI-compatible format)
        temperature: Sampling temperature
        top_p: Nucleus sampling

    Returns:
        Response string from the model
    """
    response = ollama.chat(
        model=OLLAMA_MODEL,
        options={
            "num_ctx":     2048,
            "temperature": temperature,
            "top_p":       top_p,
        },
        messages=messages,
    )
    return response["message"]["content"]


def vision_chat(prompt: str, image_b64: str, temperature: float = 0.2) -> str:
    """
    Send an image + prompt to the Ollama vision model (LLaVA).

    Args:
        prompt: Text prompt to accompany the image
        image_b64: Base64-encoded image string
        temperature: Sampling temperature

    Returns:
        Response string from the vision model
    """
    response = ollama.chat(
        model="llava",
        messages=[{
            "role":    "user",
            "content": prompt,
            "images":  [image_b64],
        }],
        options={"temperature": temperature},
    )
    return response["message"]["content"]
