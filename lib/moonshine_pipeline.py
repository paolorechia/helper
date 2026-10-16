import queue
from moonshine_voice import MicTranscriber

from lib.segments import ASRSegmentEvent

class MoonshineRealTimePipeline:
    def __init__(self, event_queue: queue.Queue):

        self.event_queue = event_queue
        self.mic = mic = (
            MicTranscriber()    
                .language("en")
                .on_line(self.on_line)
        )
        mic.load()

    def on_line(self, line):
        event = ASRSegmentEvent(
            start=line.start_time,
            end=line.start_time + line.duration,
            text=line.text,
        )
        self.event_queue.put(event.as_dict())
    
    def run_loop(self):
        self.mic.start()
        print("Ready")
        print("*" * 50)
        while True:
            continue