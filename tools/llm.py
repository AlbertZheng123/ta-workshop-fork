"""One bounded JSON model call; importing this module spends nothing."""

import json
import os

from openai import OpenAI


def call_llm_json(
    prompt: str, system_prompt: str = "You output valid JSON.",
    *, response_schema: dict | None = None,
) -> dict:
    """Require an approved key and reject malformed or truncated responses."""
    key = os.getenv("OPENAI_API_KEY")
    if not key or key == "INSERT_YOUR_API_KEY_HERE":
        raise RuntimeError("Set OPENAI_API_KEY before running an agent")
    response_format = {"type": "json_object"}
    if response_schema is not None:
        response_format = {"type": "json_schema", "json_schema": {
            "name": "workshop_response", "strict": True,
            "schema": response_schema,
        }}
    with OpenAI(api_key=key, timeout=90, max_retries=0) as client:
        response = client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-5.6-luna"),
            messages=[{"role": "system", "content": system_prompt},
                      {"role": "user", "content": prompt}],
            response_format=response_format,
            max_completion_tokens=8_000,
            store=False,
        )
    choice = response.choices[0]
    if choice.finish_reason != "stop" or not choice.message.content:
        raise RuntimeError("Model response was refused, empty, or incomplete")
    try:
        result = json.loads(choice.message.content)
    except json.JSONDecodeError as error:
        raise ValueError("Model did not return valid JSON") from error
    if not isinstance(result, dict):
        raise ValueError("Expected a JSON object from the model")
    return result
