"""Client entrypoint: wires the real-time audio pipelines together as processes.

Spawns one process per stage — microphone capture, diarization (Nemotron),
ASR (Moonshine), event aggregation, and the API sink that forwards
aggregated transcription events to the server in `main.py`.
"""

import multiprocessing as mp

from lib.api_pipeline import ApiPipeline
from lib.audio_pipeline import AudioPipeline, AudioPipelineConfig
from lib.event_aggregation_pipeline import EventAggregationPipeline
from lib.moonshine_pipeline import MoonshineRealTimePipeline
from lib.nemotron_pipeline import NemotronRealTimePipeline

if __name__ == "__main__":
    # Create base queues for inter-process communication
    mp.set_start_method("spawn")

    event_queue = mp.Queue()
    aggregated_event_queue = mp.Queue()
    nemotron_audio_queue = mp.Queue()
    moonshine_audio_queue = mp.Queue()

    # Create processes
    audio_pipeline_config = AudioPipelineConfig()  # use default values
    audio_pipeline_process = mp.Process(
        target=AudioPipeline.start_audio_pipeline,
        args=(
            [nemotron_audio_queue, moonshine_audio_queue],
            audio_pipeline_config,
        ),
    )
    nemotron_process = mp.Process(
        target=NemotronRealTimePipeline.start_nemotron,
        args=(
            nemotron_audio_queue,
            audio_pipeline_config,
            event_queue,
        ),
    )
    moonshine_process = mp.Process(
        target=MoonshineRealTimePipeline.start_moonshine,
        args=(
            moonshine_audio_queue,
            audio_pipeline_config,
            event_queue,
        ),
    )
    event_aggregation_process = mp.Process(
        target=EventAggregationPipeline.start_event_aggregation,
        args=(
            event_queue,
            aggregated_event_queue,
        ),
    )
    api_process = mp.Process(
        target=ApiPipeline.start_api_sync, args=(aggregated_event_queue,)
    )
    created_processes = [
        ("audio_pipeline", audio_pipeline_process),
        ("nemotron", nemotron_process),
        ("moonshine", moonshine_process),
        ("event_aggregation", event_aggregation_process),
        ("api_process", api_process),
    ]

    # Start processes
    for name, p in created_processes:
        p.start()

    # TODO: implement stop event handling
    keep_running = True
    while keep_running:
        for p_name, p in created_processes:
            if not p.is_alive():
                print(f"process {p} died")
                keep_running = False
