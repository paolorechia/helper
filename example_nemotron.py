import queue
import numpy as np
import sounddevice as sd
import torch

from transformers import (
    AutoModelForAudioFrameClassification,
    AutoProcessor,
)

MODEL_ID = "nvidia/Nemotron-3-Diarization"
SAMPLE_RATE = 16_000

audio_queue = queue.Queue()


def audio_callback(indata, frames, time_info, status):
    """Capture mono PCM from the microphone."""
    if status:
        print(status)

    audio_queue.put(indata[:, 0].copy())


def main():
    print("Loading Nemotron...")

    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForAudioFrameClassification.from_pretrained(
        MODEL_ID,
        device_map="auto",
    )
    model.eval()

    processor.set_streaming_mode("low_latency")

    print(f"Model ready. Buffer latency: {processor.streaming_latency_ms} ms")

    first_chunk_size = processor.num_samples_first_audio_chunk
    chunk_size = processor.num_samples_per_audio_chunk

    buffer = np.empty(0, dtype=np.float32)
    speaker_cache = None
    all_logits = []

    print("Listening. Press Ctrl+C to stop.")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            callback=audio_callback,
            blocksize=1600,
        ):
            while True:
                # Wait for another block of microphone audio.
                block = audio_queue.get()
                buffer = np.concatenate((buffer, block))

                # The first chunk has a different required size.
                required = (
                    first_chunk_size if speaker_cache is None
                    else chunk_size
                )

                while len(buffer) >= required:
                    chunk = buffer[:required]
                    buffer = buffer[required:]

                    inputs = processor(
                        chunk,
                        sampling_rate=SAMPLE_RATE,
                        is_streaming=True,
                        is_first_audio_chunk=(speaker_cache is None),
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
                    all_logits.append(outputs.logits.cpu())

                    # Prototype: decode all accumulated predictions.
                    logits = torch.cat(all_logits, dim=1)
                    segments = processor.extract_speaker_dict(logits)[0]

                    if segments:
                        latest = segments[-1]
                        print(
                            f"\rSpeaker {latest['Speaker']} "
                            f"through {latest['End']:.2f}s",
                            end="",
                            flush=True,
                        )

                    required = chunk_size

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()