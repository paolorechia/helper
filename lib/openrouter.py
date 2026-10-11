"""OpenRouter's chat-completions API, using the existing HTTP dependency."""
import os

import httpx


TIMEOUT = 60
MAX_TOKENS = 8192

class OpenRouterProvider:
    def __init__(self, model: str):
        self.model = model

    def generate(self, prompt: str) -> str:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("Set OPENROUTER_API_KEY in your environment before calling OpenRouter.")
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                response = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": MAX_TOKENS,
                        "stream": False,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                f"OpenRouter request failed (HTTP {exc.response.status_code}). "
                "Check your key, model, and quota."
            ) from None
        except httpx.TransportError:
            raise ProviderError("Could not reach OpenRouter. Check your connection and try again.") from None
        try:
            payload = response.json()
            if isinstance(payload, dict) and "error" in payload:
                raise ProviderError("OpenRouter reported a generation error. Check model availability and quota.")
            text = payload["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderError("OpenRouter returned an invalid response or no text.") from None
        if not isinstance(text, str) or not text.strip():
            raise ProviderError("OpenRouter returned no text (possibly blocked or output-limited).")
        return text