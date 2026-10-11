from enum import StrEnum
from dataclasses import dataclass

class SpeakerSegmentState(StrEnum):
    closed = "closed"
    open = "open"
    unknown = "unknown"

@dataclass
class SpeakerSegmentEvent:
    state: SpeakerSegmentState
    speaker: str
    start: float
    end: float | None = None

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "speaker": self.speaker,
            "start": self.start,
            "end": self.end
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SpeakerSegmentEvent":
        if "state" not in d:
            d["state"] = "unknown"

        lower_case = {k.lower(): v for k, v in d.items()}
        return SpeakerSegmentEvent(**lower_case)
