from dataclasses import dataclass


@dataclass
class ApiConfig:
    hostname: str = "http://127.0.0.1"
    port: int = 8000

    def as_url(self) -> str:
        return f"{hostname:port}"


class AgentAPI:
    def __init__(self, config: ApiConfig):
        self.config = config

    def api_call(self, text, speaker):
        response = requests.post(
            API_URL,
            json={
                "data": {
                    "transcription": text,
                    "speaker": speaker,
                }
            },
        )
