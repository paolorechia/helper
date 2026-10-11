import os
import queue
import threading
import time

import numpy as np
import sounddevice as sd
import torch

from moonshine_voice import Transcriber, TranscriptEventListener, ModelArch
from transformers import (
    AutoModelForAudioFrameClassification,
    AutoProcessor,
)

# Configuration
SAMPLE_RATE = 16_000
BLOCK_SIZE = 1_600  # 100 ms
MODEL_ID = "nvidia/Nemotron-3-Diarization"

# Set this to the path printed by the Moonshine download command.
MOONSHINE_MODEL_PATH = os.environ["MOONSHINE_MODEL_PATH"]
MOONSHINE_MODEL_ARCH = ModelArch.MEDIUM_STREAMING

# Independent queues prevent one model from blocking the other.
moonshine_queue = queue.Queue()
nemotron_queue = queue.Queue()

stop_event = threading.Event()


# ---------------- Moonshine ----------------

class TranscriptListener(TranscriptEventListener):
    def on_line_text_changed(self, event):
        line = event.line
        print(f"\n[Moonshine] {line.text}")

    def on_line_completed(self, event):
        line = event.line
        print(
            f"\n[Final] {line.start_time:.2f}s | "
            f"{line.text}"
        )


moonshine = Transcriber(
    model_path=MOONSHINE_MODEL_PATH,
    model_arch=MOONSHINE_MODEL_ARCH,
    update_interval=0.25,
    options={
        "word_timestamps": True,
        "identify_speakers": False,
    },
)

moonshine.add_listener(TranscriptListener())


def moonshine_worker():
    moonshine.start()

    try:
        while not stop_event.is_set():
            try:
                item = moonshine_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            _, audio = item
            moonshine.add_audio(audio, SAMPLE_RATE)

    finally:
        moonshine.stop()


# ---------------- Nemotron ----------------

print("Loading Nemotron...")

processor = AutoProcessor.from_pretrained(MODEL_ID)

model = AutoModelForAudioFrameClassification.from_pretrained(
    MODEL_ID,
    device_map="auto",
)

model.eval()
processor.set_streaming_mode("low_latency")

FIRST_CHUNK = processor.num_samples_first_audio_chunk
CHUNK_SIZE = processor.num_samples_per_audio_chunk

print(
    f"Nemotron ready. "
    f"Streaming latency: {processor.streaming_latency_ms} ms"
)


def nemotron_worker():
    buffer = np.empty(0, dtype=np.float32)

    speaker_cache = None
    all_logits = []

    samples_processed = 0
    last_printed_end = -1.0

    while not stop_event.is_set():
        try:
            _, audio = nemotron_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        buffer = np.concatenate((buffer, audio))

        while True:
            required = FIRST_CHUNK if speaker_cache is None else CHUNK_SIZE

            if len(buffer) < required:
                break

            chunk = buffer[:required]
            buffer = buffer[required:]

            is_first = speaker_cache is None

            inputs = processor(
                chunk,
                sampling_rate=SAMPLE_RATE,
                is_streaming=True,
                is_first_audio_chunk=is_first,
            )

            inputs = inputs.to(
                model.device,
                dtype=model.dtype,
            )

            with torch.inference_mode():
                outputs = model(
                    **inputs,
                    speaker_cache=speaker_cache,
                )

            speaker_cache = outputs.speaker_cache

            # Retain predictions so timestamps stay on one continuous
            # recording timeline.
            all_logits.append(outputs.logits.cpu())

            samples_processed += len(chunk)

            # Diagnostic implementation: decode accumulated predictions.
            # Optimize this once the audio alignment is validated.
            logits = torch.cat(all_logits, dim=1)
            segments = processor.extract_speaker_dict(logits)[0]

            if segments:
                latest = segments[-1]
                end = float(latest["End"])

                if end > last_printed_end:
                    print(
                        f"[Nemotron] Speaker {latest['Speaker']} "
                        f"{latest['Start']:.2f}s–{end:.2f}s"
                    )
                    last_printed_end = end


# ---------------- Microphone ----------------

sample_counter = 0


def audio_callback(indata, frames, time_info, status):
    global sample_counter

    if status:
        print(f"Audio input status: {status}")

    # One mono PCM chunk, shared by both models.
    audio = indata[:, 0].copy()

    start_sample = sample_counter
    sample_counter += len(audio)

    item = (start_sample, audio)

    moonshine_queue.put(item)
    nemotron_queue.put(item)


def main():
    workers = [
        threading.Thread(target=moonshine_worker, daemon=True),
        threading.Thread(target=nemotron_worker, daemon=True),
    ]

    for worker in workers:
        worker.start()

    print("Starting microphone...")
    print("Press Ctrl+C to stop.")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=BLOCK_SIZE,
            callback=audio_callback,
        ):
            while True:
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        stop_event.set()

        for worker in workers:
            worker.join(timeout=3)


if __name__ == "__main__":
    main()