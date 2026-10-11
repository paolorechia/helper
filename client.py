import multiprocessing as mp

import queue
from lib.moonshine_pipeline import MoonshineRealTimePipeline
from lib.nemotron_pipeline import NemotronRealTimePipeline
from lib.segments import SpeakerSegmentEvent

# MoonshineRealTimePipeline().run_loop()

# Setup and start Nemotron
def start_nemotron(event_queue):
    NemotronRealTimePipeline(event_queue).run_loop()

if __name__ == "__main__":
    nemotron_event_queue = mp.Queue()

    nemotron_process = mp.Process(target=start_nemotron, args=(nemotron_event_queue,))
    nemotron_process.start()

    while True:
        try:
            speaker_segment_event = SpeakerSegmentEvent.from_dict(nemotron_event_queue.get(timeout=1))
        except queue.Empty:
            if not nemotron_process.is_alive():
                print("Nemotron process died")
                break
            continue
        print("Got speaker segmenet event:", speaker_segment_event)
