import queue


class EventAggregationPipeline:
    def __init__(self, input_event_queue: queue.Queue):
        self.input_event_queue = input_event_queue

    def run_loop(self):
        while True:
            try:
                event = self.input_event_queue.get(timeout=1)
                print("Got event: ", event)
            except queue.Empty:
                pass

    @classmethod
    def start_event_aggregation(cls, input_event_queue: queue.Queue):
        EventAggregationPipeline(input_event_queue).run_loop()
