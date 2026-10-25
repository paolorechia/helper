"""Forwards aggregated transcription events from a queue to the voice assistant API."""

import queue

from lib.api_sdk import AgentAPI, ApiConfig
from lib.segments import AggregatedSegmentEvent


class ApiPipeline:
    """Consumes aggregated events and POSTs each one to the assistant server."""

    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.agent_api = AgentAPI(ApiConfig())

    def run_loop(self):
        """Poll the event queue forever, forwarding each event to the API."""
        while True:
            try:
                event = self.event_queue.get(timeout=1)
                self.send_event_to_api(AggregatedSegmentEvent.from_dict(event))
            except queue.Empty:
                pass

    def send_event_to_api(self, event: AggregatedSegmentEvent):
        """Send a single aggregated event's text and speaker to the API."""
        self.agent_api.api_call(text=event.text, speaker=event.speaker)

    @classmethod
    def start_api_sync(cls, event_queue: queue.Queue):
        """Entrypoint for running the pipeline in a dedicated process."""
        ApiPipeline(event_queue).run_loop()
