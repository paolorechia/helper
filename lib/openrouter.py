"""OpenRouter's chat-completions API, using the existing HTTP dependency."""
import os
import httpx

class OpenRouterProvider:
    def __init__(self, model: str, max_tokens: int, timeout: float):
        self.model = model
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate(self, messages_prompt: list, session_id: str, ) -> str:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("Set OPENROUTER_API_KEY in your environment before calling OpenRouter.")

        status_code = None
        text = None
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "X-Session-Id": session_id,
                        "X-OpenRouter-Cache": "true",
                    },
                    json={
                        "model": self.model,
                        "messages": messages_prompt,
                        "max_tokens": self.max_tokens,
                        "temperature": 0.5,
                        "stream": False,
                    },
                )
                status_code = response.status_code
                text = response.text
                response.raise_for_status()

        except Exception as excp:
            raise ValueError(f"HTTP REQUEST FAILED (code: {status_code}): {text}") from excp

        payload = response.json()
        text = payload["choices"][0]["message"]["content"]
        if not text:
            raise Exception(f"Empty text in {payload}")
        return text