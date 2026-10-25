"""HTTP client for the voice assistant server in `main.py`."""

from dataclasses import dataclass

import requests


@dataclass
class ApiConfig:
    """Connection settings for the assistant server."""

    hostname: str = "http://127.0.0.1"
    port: int = 8000

    @property
    def as_url(self) -> str:
        """Base URL of the server."""
        return f"{self.hostname}:{self.port}"


class AgentAPI:
    """Thin wrapper that POSTs transcription events to the server."""

    def __init__(self, config: ApiConfig):
        self.config = config

    def api_call(self, text, speaker):
        """Send one transcription event (text + speaker id) to the server."""
        print(f"Sending [speaker {speaker}]: {text}")
        response = requests.post(
            self.config.as_url,
            json={
                "data": {
                    "transcription": text,
                    "speaker": speaker,
                }
            },
        )
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Text: {response.text}")
