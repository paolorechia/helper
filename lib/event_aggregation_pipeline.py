import queue

from lib.segments import (
    AggregatedSegmentEvent,
    ASRSegmentEvent,
    EventType,
    SpeakerSegmentEvent,
    SpeakerSegmentState,
)


class EventAggregationPipeline:
    def __init__(
        self, input_event_queue: queue.Queue, aggregated_event_queue: queue.Queue
    ):
        self.input_event_queue: queue.Queue = input_event_queue
        self.aggregated_event_queue: queue.Queue = aggregated_event_queue
        self.queue_timeout = 0.1
        self.min_timestamp_watermark: float = 0
        self.max_timestamp_watermark: float = 0
        self.active_asr_segments: list[ASRSegmentEvent] = []
        self.active_diarization_segments: list[SpeakerSegmentEvent] = []
        self.aggregated_events: list[AggregatedSegmentEvent] = []

    def run_loop(self):
        while True:
            # Always
            self.read_events_from_queue()

            # If we have active segments of both types, try to aggregate them
            if (
                len(self.active_asr_segments) >= 1
                and len(self.active_diarization_segments) >= 1
            ):
                self.aggregate_events()

            # If we aggregated events, publish them
            if len(self.aggregated_events) >= 1:
                self.publish_aggregated_events()

                # For now clear in a Naive away
                # Assumes ASR segments always arrive later than diarization segments
                # If events come out of order, a better solution such as watermarking
                # may be required to clear events correctly
                self.clear_aggregation_state()

    def read_events_from_queue(self):
        """Reads all available events.

        Uses the queue timeout parameter as a way to create a window of
        variable size.

        While events keep arriving close together in time (e.g., < 0.1s apart),
        keep waiting/pulling events from queue.

        This adds some latency but ensures events within this boundary are processed
        together.
        """
        try:
            while event := self.input_event_queue.get(timeout=self.queue_timeout):
                if event["type_"] == EventType.asr_segment:
                    self.active_asr_segments.append(ASRSegmentEvent.from_dict(event))
                elif event["type_"] == EventType.diarization_segment:
                    self.active_diarization_segments.append(
                        SpeakerSegmentEvent.from_dict(event)
                    )
                print("Got event: ", event)
        except queue.Empty:
            pass

    def publish_aggregated_events(self):
        """Publishes aggregated events into next event bus."""
        for aggregated_event in self.aggregated_events:
            print("Publishing aggregated event: ", aggregated_event)
            self.aggregated_event_queue.put(aggregated_event.as_dict())

    def clear_aggregation_state(self):
        """Clears all current state, naively.

        Assumes ASR segments always arrive later than diarization segments.

        If events come out of order, a better solution such as watermarking
        may be required to clear events correctly.
        """
        self.active_asr_segments = []
        self.active_diarization_segments = []
        self.aggregated_events = []

    def aggregate_events(self):
        """Aggregates ASR Segments and Diarization Segments."""
        for asr_segment in self.active_asr_segments:
            max_overlap = -1
            max_overlap_segment = None

            for diarization_segment in self.active_diarization_segments:
                # for now, simply ignore segments that are not in closed state
                if diarization_segment.state != SpeakerSegmentState.closed:
                    continue

                overlap_area = asr_segment.overlaps(diarization_segment)
                if overlap_area > max_overlap:
                    max_overlap_segment = diarization_segment
                    max_overlap = overlap_area

            if max_overlap_segment:
                self.aggregated_events.append(
                    AggregatedSegmentEvent.from_events(
                        asr_segment,
                        diarization_segment,
                    )
                )

    @classmethod
    def start_event_aggregation(
        cls, input_event_queue: queue.Queue, output_event_queue: queue.Queue
    ):
        EventAggregationPipeline(input_event_queue, output_event_queue).run_loop()
