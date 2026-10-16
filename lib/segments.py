from enum import StrEnum
from dataclasses import dataclass

class SpeakerSegmentState(StrEnum):
    closed = "closed"
    open = "open"
    unknown = "unknown"

class EventType(StrEnum):
    abstract = "abstract"
    asr_segment = "asr_segment"
    diarization_segment = "diarization_segment"

@dataclass
class Event:
    type_ = "Abstract"


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
            "type_": self.type_
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpeakerSegmentEvent":
        if "state" not in d:
            d["state"] = "unknown"

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
            "type_": self.type_
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ASRSegmentEvent":
        lower_case = {k.lower(): v for k, v in d.items()}
        return ASRSegmentEvent(**lower_case)
