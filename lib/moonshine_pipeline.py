"""Real-time speech-to-text pipeline built on the Moonshine streaming transcriber."""

import os
import queue

import numpy as np
from moonshine_voice import ModelArch, Transcriber, TranscriptEventListener

from lib.audio_pipeline import AudioPipelineConfig
from lib.segments import ASRSegmentEvent


class MoonshineRealTimePipeline:
    """Streams microphone blocks through Moonshine and emits ASR segment events.

    Requires the MOONSHINE_MODEL_PATH environment variable to point at a
    downloaded Moonshine model (see README). Only float32 audio is supported.
    """

    def __init__(
        self,
        input_audio_queue: queue.Queue,
        audio_pipeline_config: AudioPipelineConfig,
        output_event_queue: queue.Queue,
    ):
        # TODO: use input audio queue and audio pipeline config
        self.input_audio_queue = input_audio_queue
        self.output_event_queue = output_event_queue
        self.model_path = os.environ["MOONSHINE_MODEL_PATH"]
        self.model_arch = ModelArch.MEDIUM_STREAMING
        self.audio_pipeline_config = audio_pipeline_config

        if audio_pipeline_config.dtype != "float32":
            raise ValueError(
                f"Moonshine pipeline does not support this dtype: {audio_pipeline_config.dtype}"
            )

        self.transcriber = Transcriber(
            model_path=self.model_path,
            model_arch=self.model_arch,
        )
        self.transcriber.add_listener(ASRListener(self.output_event_queue))

    def run_loop(self):
        """Feed queued audio blocks into the transcriber until the process exits."""
        self.transcriber.start()
        print("Moonshine Ready")
        print("*" * 50)
        try:
            while True:
                audio_block = self.input_audio_queue.get()
                self.transcriber.add_audio(
                    np.asarray(audio_block, dtype=np.float32),
                    self.audio_pipeline_config.sample_rate,
                )
        finally:
            self.transcriber.stop()

    @classmethod
    def start_moonshine(
        cls,
        input_audio_queue: queue.Queue,
        audio_pipeline_config: AudioPipelineConfig,
        output_event_queue: queue.Queue,
    ):
        """Starts ASR pipeline."""
        MoonshineRealTimePipeline(
            input_audio_queue=input_audio_queue,
            audio_pipeline_config=audio_pipeline_config,
            output_event_queue=output_event_queue,
        ).run_loop()


class ASRListener(TranscriptEventListener):
    """Converts completed Moonshine transcript lines into ASRSegmentEvents."""

    def __init__(self, output_event_queue: queue.Queue):
        super().__init__()
        self.output_event_queue = output_event_queue

    def on_line_completed(self, event):
        """Publish an ASRSegmentEvent for each finalized transcript line."""
        line = event.line

        event = ASRSegmentEvent(
            start=line.start_time,
            end=line.start_time + line.duration,
            text=line.text,
        )
        self.output_event_queue.put(event.as_dict())
