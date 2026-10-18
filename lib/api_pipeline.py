import queue

from lib.api_sdk import AgentAPI, ApiConfig
from lib.segments import AggregatedSegmentEvent


class ApiPipeline:
    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.agent_api = AgentAPI(ApiConfig())

    def run_loop(self):
        while True:
            try:
                event = self.event_queue.get(timeout=1)
                self.send_event_to_api(AggregatedSegmentEvent.from_dict(event))
            except queue.Empty:
                pass

    def send_event_to_api(self, event: AggregatedSegmentEvent):
        self.agent_api.api_call(text=event.text, speaker=event.speaker)

    @classmethod
    def start_api_sync(cls, event_queue: queue.Queue):
        ApiPipeline(event_queue).run_loop()
