from dataclasses import dataclass

import requests


@dataclass
class ApiConfig:
    hostname: str = "http://127.0.0.1"
    port: int = 8000

    def as_url(self) -> str:
        return f"{self.hostname:self.port}"


class AgentAPI:
    def __init__(self, config: ApiConfig):
        self.config = config

    def api_call(self, text, speaker):
        requests.post(
            self.config.as_url,
            json={
                "data": {
                    "transcription": text,
                    "speaker": speaker,
                }
            },
        )
