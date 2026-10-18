import queue

import pytest

from lib.event_aggregation_pipeline import EventAggregationPipeline
from lib.segments import (
    ASRSegmentEvent,
    SpeakerSegmentEvent,
    SpeakerSegmentState,
)


@pytest.mark.parametrize(
    "s1,e1,s2,e2,expected_overlap_area",
    [
        pytest.param(0.1, 0.5, 1.0, 2.0, -1, id="no-overlap-seg1-left-seg2"),
        pytest.param(0.1, 1.0, 1.0, 2.0, -1, id="no-overlap-seg1-left-exclusive-seg2"),
        pytest.param(3.0, 4.5, 1.0, 2.0, -1, id="no-overlap-seg1-right-seg2"),
        pytest.param(3.0, 4.5, 2.0, 3.0, -1, id="no-overlap-seg1-right-exclusive-seg2"),
        pytest.param(1.2, 1.7, 1.0, 2.0, 0.5, id="seg1-inside-seg2"),
        pytest.param(1.0, 2.0, 1.0, 2.0, 1.0, id="seg1-equals-seg2"),
        pytest.param(0.1, 1.0, 0.6, 2.0, 0.4, id="seg1-overlap-left-seg2"),
        pytest.param(1.0, 3.0, 1.2, 2.5, 1.3, id="seg2-inside-seg1"),
        pytest.param(1.8, 3.0, 1.0, 2.0, 0.2, id="seg1-overlap-right-seg2"),
    ],
)
def test_segment_overlap(s1, e1, s2, e2, expected_overlap_area):
    overlap_area = ASRSegmentEvent(start=s1, end=e1, text="bah").overlaps(
        SpeakerSegmentEvent(
            state=SpeakerSegmentState.closed, start=s2, end=e2, speaker="bleh"
        )
    )

    assert abs(overlap_area - expected_overlap_area) < 0.1


def test_event_aggregation_pipeline():
    input_event_queue = queue.Queue()
    aggregated_event_queue = queue.Queue()

    input_event_queue.put(ASRSegmentEvent(start=0.1, end=1.0, text="bah").as_dict())
    input_event_queue.put(
        SpeakerSegmentEvent(
            start=0.5,
            end=0.9,
            speaker="alice",
            state=SpeakerSegmentState.closed,
        ).as_dict()
    )

    event_aggregation_pipeline = EventAggregationPipeline(
        input_event_queue, aggregated_event_queue
    )
    event_aggregation_pipeline.read_events_from_queue()
    # Read method reads all available events
    assert input_event_queue.empty() is True

    assert len(event_aggregation_pipeline.active_asr_segments) == 1
    assert len(event_aggregation_pipeline.active_diarization_segments) == 1

    event_aggregation_pipeline.aggregate_events()
    assert len(event_aggregation_pipeline.aggregated_events) == 1

    event_aggregation_pipeline.publish_aggregated_events()

    aggregated_event = aggregated_event_queue.get(timeout=0.1)

    assert aggregated_event["start"] == 0.1
    assert aggregated_event["end"] == 1.0
    assert aggregated_event_queue.empty() is True

    event_aggregation_pipeline.clear_aggregation_state()
    assert len(event_aggregation_pipeline.aggregated_events) == 0
    assert len(event_aggregation_pipeline.active_asr_segments) == 0
    assert len(event_aggregation_pipeline.active_diarization_segments) == 0
