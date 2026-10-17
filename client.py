import multiprocessing as mp

import queue
from lib.moonshine_pipeline import MoonshineRealTimePipeline
from lib.nemotron_pipeline import NemotronRealTimePipeline
from lib.segments import SpeakerSegmentEvent


def start_moonshine(event_queue):
    MoonshineRealTimePipeline(event_queue).run_loop()

def start_nemotron(event_queue):
    NemotronRealTimePipeline(event_queue).run_loop()


if __name__ == "__main__":
    event_queue = mp.Queue()

    nemotron_process = mp.Process(target=start_nemotron, args=(event_queue,))
    nemotron_process.start()

    moonshine_process = mp.Process(target=start_moonshine, args=(event_queue,))
    moonshine_process.start()

    fired_processes = [("moonshine", moonshine_process)]

    while True:
        for p_name, p in fired_processes:
            if not p.is_alive():
                print(f"process {p} died")
                break

        try:
            event = event_queue.get(timeout=1)
            print("Got event: ", event)
        except queue.Empty:
            pass
