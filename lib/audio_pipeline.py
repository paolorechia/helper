"""Microphone capture pipeline that fans raw PCM blocks out to downstream queues."""

import queue
import time
from dataclasses import dataclass

import sounddevice as sd

DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_BLOCK_SIZE = 1600
DEFAULT_DTYPE = "float32"
DEFAULT_CHANNELS = 1


@dataclass
class AudioPipelineConfig:
    """Capture settings shared by all audio pipelines."""

    sample_rate = DEFAULT_SAMPLE_RATE
    channels = DEFAULT_CHANNELS
    dtype = DEFAULT_DTYPE
    blocksize = DEFAULT_BLOCK_SIZE


class AudioPipeline:
    """Produces a audio input stream (microphone) for downstream consumption."""

    def __init__(self, config: AudioPipelineConfig, audio_queues: list[queue.Queue]):
        self.config = config
        self.audio_queues = audio_queues

    def run_loop(self):
        """Stream microphone audio into the registered queues until interrupted."""
        try:
            with sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                callback=self.audio_callback,
                blocksize=self.config.blocksize,
            ):
                print("Recording. Press Ctrl+C to stop.")
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping recording.")

    def audio_callback(self, indata, _frames, _time_info, _status):
        """Capture mono PCM from the microphone."""

        for q in self.audio_queues:
            q.put(indata[:, 0].copy())

    @classmethod
    def start_audio_pipeline(
        cls, audio_queues: list[queue.Queue], audio_pipeline_config: AudioPipelineConfig
    ):
        """Starts base audio pipeline to capture microphone audio."""
        AudioPipeline(
            config=audio_pipeline_config, audio_queues=audio_queues
        ).run_loop()
