import multiprocessing as mp
import queue

from lib.audio_pipeline import AudioPipeline, AudioPipelineConfig
from lib.moonshine_pipeline import MoonshineRealTimePipeline
from lib.nemotron_pipeline import NemotronRealTimePipeline
from lib.segments import SpeakerSegmentEvent

def start_audio_pipeline(
    audio_queues: list[queue.Queue],
    audio_pipeline_config: AudioPipelineConfig
):
    """Starts base audio pipeline to capture microphone audio."""
    AudioPipeline(
        config=audio_pipeline_config,
        audio_queues=audio_queues
    ).run_loop()

def start_moonshine(
    input_audio_queue: queue.Queue,
    audio_pipeline_config: AudioPipelineConfig,
    output_event_queue: queue.Queue
):
    """Starts ASR pipeline."""
    MoonshineRealTimePipeline(
        input_audio_queue=input_audio_queue,
        audio_pipeline_config=audio_pipeline_config,
        output_event_queue=output_event_queue
    ).run_loop()

def start_nemotron(
    input_audio_queue: queue.Queue,
    audio_pipeline_config: AudioPipelineConfig,
    output_event_queue: queue.Queue
):
    """Starts Diarization pipeline."""
    NemotronRealTimePipeline(
        input_audio_queue=input_audio_queue,
        audio_pipeline_config=audio_pipeline_config,
        output_event_queue=output_event_queue
    ).run_loop()


if __name__ == "__main__":
    # Create base queues for inter-process communication
    mp.set_start_method("spawn")

    event_queue = mp.Queue()
    nemotron_audio_queue = mp.Queue()
    moonshine_audio_queue = mp.Queue()

    # Create processes
    audio_pipeline_config = AudioPipelineConfig()  # use default values
    audio_pipeline_process = mp.Process(
        target=start_audio_pipeline, args=([nemotron_audio_queue, moonshine_audio_queue], audio_pipeline_config,)
    )
    nemotron_process = mp.Process(
        target=start_nemotron, args=(nemotron_audio_queue, audio_pipeline_config, event_queue,)
    )
    moonshine_process = mp.Process(
        target=start_moonshine, args=(moonshine_audio_queue, audio_pipeline_config, event_queue,)
    )
    created_processes = [
        ("audio_pipeline", audio_pipeline_process),
        ("nemotron", nemotron_process),
        ("moonshine", moonshine_process),
    ]
    
    # Start processes
    for name, p in created_processes:
        p.start()

    while True:
        for p_name, p in created_processes:
            if not p.is_alive():
                print(f"process {p} died")
                break

        try:
            event = event_queue.get(timeout=1)
            print("Got event: ", event)
        except queue.Empty:
            pass
