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


# ---------------- Configuration ----------------

SAMPLE_RATE = 16_000
BLOCK_SIZE = 1_600  # 100 ms
MODEL_ID = "nvidia/Nemotron-3-Diarization"

# Re-decode accumulated diarization predictions at this interval.
DIARIZATION_UPDATE_INTERVAL = 1.0

MOONSHINE_MODEL_PATH = os.environ["MOONSHINE_MODEL_PATH"]
MOONSHINE_MODEL_ARCH = ModelArch.MEDIUM_STREAMING

moonshine_queue = queue.Queue()
nemotron_queue = queue.Queue()

stop_event = threading.Event()
output_lock = threading.Lock()
timeline_lock = threading.Lock()

# Latest available diarization timeline.
speaker_segments = []

# Finalized transcript lines waiting for enough diarization data.
pending_transcripts = []

# Track the current Moonshine draft so revisions replace one another.
current_draft = ""


def log(message):
    """Keep console output from different threads readable."""
    with output_lock:
        print(message, flush=True)


# ---------------- Transcript / diarization alignment ----------------

def get_line_interval(line):
    start = getattr(line, "start_time", None)
    duration = getattr(line, "duration", None)

    if start is None or duration is None:
        return None

    start = float(start)
    end = start + float(duration)

    if end < start:
        return None

    return start, end


def find_speakers(start, end, segments):
    """
    Return speakers whose diarization intervals overlap the transcript.

    A transcript line may overlap multiple speakers. Overlap duration
    is used to rank the speakers rather than assigning the most recent
    speaker unconditionally.
    """
    overlaps = {}

    for segment in segments:
        seg_start = float(segment["Start"])
        seg_end = float(segment["End"])
        speaker = segment["Speaker"]

        overlap = max(
            0.0,
            min(end, seg_end) - max(start, seg_start),
        )

        if overlap > 0:
            overlaps[speaker] = overlaps.get(speaker, 0.0) + overlap

    return sorted(
        overlaps.items(),
        key=lambda item: item[1],
        reverse=True,
    )


def format_speaker_attribution(start, end, segments):
    matches = find_speakers(start, end, segments)

    if not matches:
        return "Speaker unknown"

    if len(matches) == 1:
        return f"Speaker {matches[0][0]}"

    return "Speakers: " + ", ".join(
        f"{speaker} ({duration:.2f}s)"
        for speaker, duration in matches
    )


def process_pending_transcripts():
    """
    Attribute completed transcripts once diarization covers their end time.

    This avoids prematurely assigning a speaker when the two independent
    model workers are temporarily out of sync.
    """
    with timeline_lock:
        segments = list(speaker_segments)

        if not segments:
            return

        diarized_until = max(float(s["End"]) for s in segments)

        ready = []
        waiting = []

        for line, text in pending_transcripts:
            interval = get_line_interval(line)

            if interval is None:
                # We cannot reliably align a line without both timestamps.
                ready.append((line, text, None))
                continue

            _, end = interval

            if end <= diarized_until:
                ready.append((line, text, interval))
            else:
                waiting.append((line, text))

        pending_transcripts.clear()
        pending_transcripts.extend(waiting)

    for line, text, interval in ready:
        if interval is None:
            attribution = "Speaker unknown (timestamps unavailable)"
        else:
            start, end = interval
            attribution = format_speaker_attribution(
                start,
                end,
                segments,
            )

        log(
            f"\n[Final] {getattr(line, 'start_time', 0.0):.2f}s "
            f"| {attribution} | {text}"
        )


# ---------------- Moonshine ----------------
class TranscriptListener(TranscriptEventListener):
    def __init__(self):
        super().__init__()
        self.last_audio_capture_time = time.monotonic()

    def on_line_text_changed(self, event):
        global current_draft

        with output_lock:
            current_draft = event.line.text

    def on_line_completed(self, event):
        global current_draft

        line = event.line
        text = line.text

        with output_lock:
            print(
                f"[Perf] Transcript completed | "
                f"line_start={line.start_time:.2f}s | "
                f"line_duration={line.duration:.2f}s",
                flush=True,
            )

        with timeline_lock:
            pending_transcripts.append((line, text))

        process_pending_transcripts()


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
                first = moonshine_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            batch = [first]

            # Match MicTranscriber's queue-coalescing behavior.
            while True:
                try:
                    batch.append(moonshine_queue.get_nowait())
                except queue.Empty:
                    break

            audio = np.concatenate([item[1] for item in batch])

            t0 = time.perf_counter()
            moonshine.add_audio(audio, SAMPLE_RATE)
            elapsed_ms = (time.perf_counter() - t0) * 1000

            log(
                f"[Perf] Moonshine add_audio: {elapsed_ms:.0f}ms "
                f"| chunks: {len(batch)} "
                f"| queue: {moonshine_queue.qsize()}"
            )
    finally:
        moonshine.stop()


# ---------------- Nemotron ----------------

log("Loading Nemotron...")

processor = AutoProcessor.from_pretrained(MODEL_ID)

model = AutoModelForAudioFrameClassification.from_pretrained(
    MODEL_ID,
    device_map="auto",
)

model.eval()
processor.set_streaming_mode("low_latency")

FIRST_CHUNK = processor.num_samples_first_audio_chunk
CHUNK_SIZE = processor.num_samples_per_audio_chunk

log(
    f"Nemotron ready. "
    f"Streaming latency: {processor.streaming_latency_ms} ms"
)


def nemotron_worker():
    global speaker_segments

    buffer = np.empty(0, dtype=np.float32)
    speaker_cache = None
    all_logits = []

    samples_processed = 0
    last_decode_time = time.monotonic()

    while not stop_event.is_set():
        try:
            _, audio = nemotron_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        buffer = np.concatenate((buffer, audio))

        # Process only complete chunks of the required size.
        while True:
            required = (
                FIRST_CHUNK
                if speaker_cache is None
                else CHUNK_SIZE
            )

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

            t0 = time.perf_counter()

            with torch.inference_mode():
                outputs = model(
                    **inputs,
                    speaker_cache=speaker_cache,
                )

            inference_ms = (time.perf_counter() - t0) * 1000

            log(
                f"[Perf] Nemotron inference: {inference_ms:.0f}ms "
                f"| queue: {nemotron_queue.qsize()}"
            )

            speaker_cache = outputs.speaker_cache
            all_logits.append(outputs.logits.cpu())

            samples_processed += len(chunk)

        # Decode accumulated logits less frequently, not on every chunk.

        now = time.monotonic()

        if (
            not all_logits
            or now - last_decode_time < DIARIZATION_UPDATE_INTERVAL
        ):
            continue

        last_decode_time = now

        t0 = time.perf_counter()

        logits = torch.cat(all_logits, dim=1)
        decoded = processor.extract_speaker_dict(logits)

        decode_ms = (time.perf_counter() - t0) * 1000

        log(
            f"[Perf] Decode: {decode_ms:.0f}ms "
            f"| history: {samples_processed / SAMPLE_RATE:.1f}s "
            f"| queue: {nemotron_queue.qsize()}"
        )

        if not decoded:
            continue

        segments = decoded[0]

        # Replace the shared timeline with the latest decoded version.
        # The model can revise recent boundaries as more audio arrives.
        with timeline_lock:
            speaker_segments = list(segments)

        process_pending_transcripts()


# ---------------- Microphone ----------------

sample_counter = 0


def audio_callback(indata, frames, time_info, status):
    global sample_counter

    if status:
        log(f"Audio input status: {status}")

    audio = indata[:, 0].copy()

    start_sample = sample_counter
    sample_counter += len(audio)

    item = (start_sample, audio)
   
    captured_at = time.monotonic()

    moonshine_queue.put((start_sample, audio, captured_at))
   
    nemotron_queue.put(item)


def main():
    workers = [
        threading.Thread(target=moonshine_worker, daemon=True),
        threading.Thread(target=nemotron_worker, daemon=True),
    ]

    for worker in workers:
        worker.start()

    log("Starting microphone...")
    log("Press Ctrl+C to stop.")

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
        log("\nStopping...")

    finally:
        stop_event.set()

        for worker in workers:
            worker.join(timeout=3)


if __name__ == "__main__":
    main()