import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


def _extract_platform_context(prompt: str) -> str:
    marker = "Available platform context:"
    if marker not in prompt:
        return "No platform context was available."

    context = prompt.split(marker, maxsplit=1)[1]
    context = context.split("Answer using only this context", maxsplit=1)[0].strip()
    return context or "No platform context was available."


def _extract_output_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    for item in payload.get("output", []):
        for content_item in item.get("content", []):
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                return text.strip()

    return "I could not generate a response from the available context."


def _extract_chat_completion_text(payload: dict) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return "I could not generate a response from the available context."

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return "I could not generate a response from the available context."

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return "I could not generate a response from the available context."

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    return "I could not generate a response from the available context."


async def generate_assistant_response(
    prompt: str,
    instructions: str,
) -> str:
    settings = get_settings()
    api_key = settings.groq_api_key or settings.openai_api_key
    provider_name = "Groq" if settings.groq_api_key else "OpenAI"
    request_url = GROQ_CHAT_COMPLETIONS_URL if settings.groq_api_key else OPENAI_RESPONSES_URL
    model = settings.groq_model if settings.groq_api_key else settings.openai_model

    if not api_key:
        return (
            "An AI provider is not configured yet, so I cannot generate a full AI explanation. "
            "Here is the platform context I found:\n\n"
            f"{_extract_platform_context(prompt)}\n\n"
            "This is informational research context only, not financial advice."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = (
        {
            "model": model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }
        if settings.groq_api_key
        else {
            "model": model,
            "instructions": instructions,
            "input": prompt,
            "store": False,
            "max_output_tokens": 700,
        }
    )

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(request_url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{provider_name} request failed: {detail}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{provider_name} request failed. Please try again.",
        ) from exc

    payload = response.json()
    if settings.groq_api_key:
        return _extract_chat_completion_text(payload)

    return _extract_output_text(payload)
