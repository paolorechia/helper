from dataclasses import dataclass
from enum import StrEnum


class SpeakerSegmentState(StrEnum):
    closed = "closed"
    open = "open"
    unknown = "unknown"


class EventType(StrEnum):
    abstract = "abstract"
    asr_segment = "asr_segment"
    diarization_segment = "diarization_segment"
    aggregated_segment = "aggregated_segment"


@dataclass
class SpeakerSegmentEvent:
    state: SpeakerSegmentState
    speaker: str
    start: float
    end: float | None = None
    type_ = EventType.diarization_segment  # Internal, don't override

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "speaker": self.speaker,
            "start": self.start,
            "end": self.end,
            "type_": self.type_,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpeakerSegmentEvent":
        if "state" not in d:
            d["state"] = "unknown"

        # ignore type_
        if "type_" in d:
            d.pop("type_")

        lower_case = {k.lower(): v for k, v in d.items()}
        return SpeakerSegmentEvent(**lower_case)


@dataclass
class ASRSegmentEvent:
    start: float
    end: float
    text: str
    type_ = EventType.asr_segment  # Internal, don't override

    def as_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "type_": self.type_,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ASRSegmentEvent":
        lower_case = {k.lower(): v for k, v in d.items()}

        # ignore type_
        if "type_" in lower_case:
            lower_case.pop("type_")

        return ASRSegmentEvent(**lower_case)

    def overlaps(self, segment: SpeakerSegmentEvent) -> float:
        if segment.state != SpeakerSegmentState.closed:
            raise ValueError("Cannot compute overlap on segment that is not closed")

        overlap_area = -1

        # case 1, self is inside segment
        if self.start > segment.start and self.end < segment.end:
            overlap_area = self.end - self.start
            return overlap_area

        # case 2, segment is inside self
        if segment.start > self.start and segment.end < self.end:
            overlap_area = segment.end - segment.start
            return overlap_area

        # case 3, partial overlap, self is on left side
        # e1 > s2 and e2 > s1
        if (
            self.end > segment.start
            and segment.end > self.start
            and self.end < segment.end
        ):
            overlap_area = self.end - segment.start
            return overlap_area

        # case 4, partial overlap, self is on right side
        # e2 > s1 and e1 > s2
        if segment.end > self.start and self.end > segment.start:
            overlap_area = segment.end - self.start
            return overlap_area

        return overlap_area


@dataclass
class AggregatedSegmentEvent:
    start: float
    end: float
    text: str
    speaker: str
    type_ = EventType.aggregated_segment  # Internal, don't override

    def as_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
            "type_": self.type_,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AggregatedSegmentEvent":
        lower_case = {k.lower(): v for k, v in d.items()}

        # ignore type_
        if "type_" in lower_case:
            lower_case.pop("type_")

        return AggregatedSegmentEvent(**lower_case)

    @classmethod
    def from_events(
        cls,
        asr_segment_event: ASRSegmentEvent,
        speaker_segment_event: SpeakerSegmentEvent,
    ) -> "AggregatedSegmentEvent":
        # Read only speaker from speaker segment, use timestamps from ASR Segmente Event as source of truth
        return AggregatedSegmentEvent(
            start=asr_segment_event.start,
            end=asr_segment_event.end,
            text=asr_segment_event.text,
            speaker=speaker_segment_event.speaker,
        )
