import queue
import sounddevice as sd
import time

from dataclasses import dataclass

DEFAULT_SAMPLE_RATE = 16_000
DEFAULT_BLOCK_SIZE = 1600
DEFAULT_DTYPE = "float32"
DEFAULT_CHANNELS = 1


@dataclass
class AudioPipelineConfig:
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

    def audio_callback(self, indata, frames, time_info, status):
        """Capture mono PCM from the microphone."""

        for queue in self.audio_queues:
            queue.put(indata[:, 0].copy())

    @classmethod
    def start_audio_pipeline(
        cls, audio_queues: list[queue.Queue], audio_pipeline_config: AudioPipelineConfig
    ):
        """Starts base audio pipeline to capture microphone audio."""
        AudioPipeline(
            config=audio_pipeline_config, audio_queues=audio_queues
        ).run_loop()
