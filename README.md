# helper

A local voice assistant. It listens to your microphone, works out who is
speaking, sends the utterance to an LLM, and speaks the reply back through
your speakers.

Everything runs on your machine except the LLM call, which goes to
[OpenRouter](https://openrouter.ai).

## How it works

1. Your microphone is captured continuously in small blocks.
2. Two models read that audio in parallel: a **diarizer** decides *who* is
   talking, and a **transcriber** decides *what* was said.
3. A third stage joins the two by time overlap, so every transcript is
   attributed to a speaker.
4. The attributed text is POSTed to a local server that keeps the chat
   history, asks the LLM for a reply, and synthesizes that reply into audio.
5. The audio is played back on your speakers.

Because the assistant's own voice comes back through the microphone, the
server refuses events from the agent's speaker slot so it doesn't answer
itself.

## Architecture

Two entry points, run in separate processes.

### `client.py` — capture and understanding

Spawns one process per stage and connects them with multiprocessing queues.

```
                     ┌─► nemotron (diarization) ─┐
mic ─► audio_pipeline│                            ├─► event_aggregation ─► api_pipeline ─► POST /
                     └─► moonshine (ASR) ──────────┘
```

| Stage | Module | What it does |
| --- | --- | --- |
| Capture | `lib/audio_pipeline.py` | Opens the mic with `sounddevice` and copies each 1600-sample block (16 kHz, mono, float32) into two queues. |
| Diarization | `lib/nemotron_pipeline.py` | Runs `nvidia/Nemotron-3-Diarization` in ultra-low-latency streaming mode over one queue and emits speaker segment events (`open` / `closed`). The model's speaker cache is carried across chunks so speakers stay consistent. |
| ASR | `lib/moonshine_pipeline.py` | Runs the Moonshine streaming transcriber over the other queue and emits transcript lines with start/end timestamps. |
| Aggregation | `lib/event_aggregation_pipeline.py` | Attributes each transcript to the speaker segment it overlaps most, producing `{text, speaker}` events. |
| Forwarding | `lib/api_pipeline.py` | POSTs each aggregated event to the assistant server. |

The event types exchanged between stages are defined in `lib/segments.py`.
All of them serialize to plain dicts so they can cross process queues;
timestamps are seconds relative to the start of the audio stream.

### `main.py` — the assistant

A FastAPI app that owns the session's chat history, calls OpenRouter for a
reply, and speaks it with Kokoro.

- **Model**: `google/gemini-2.5-flash-lite`, `max_tokens` 150, 5 s timeout,
  temperature 0.5.
- **Voice**: Kokoro TTS, `lang_code="a"` (American English), voice `af_heart`,
  24 kHz output.
- **Playback**: `sounddevice` writes to CoreAudio; the HTTP response returns
  as soon as playback is queued, not when the audio finishes.
- **Prompt**: the system prompt keeps replies to a single short sentence and
  tells the model to ask the user to repeat anything the transcription mangles,
  rather than guess.

## HTTP API

`POST http://127.0.0.1:8000/`

Request:

```json
{
  "data": {
    "transcription": "what is the weather like today",
    "speaker": 0
  }
}
```

Response (`200`):

```json
{
  "chat": [
    { "role": "system", "content": "You're an AI assistant. ..." },
    { "role": "user", "content": "what is the weather like today" },
    { "role": "assistant", "content": "It is sunny and warm." }
  ]
}
```

| Status | Meaning |
| --- | --- |
| `200` | Reply generated and queued for playback. The body is the full chat history. |
| `400` | `speaker` was missing, or the event came from the agent itself. |
| `500` | TTS produced no audio. |

## Setup

### 1. Python 3.12 (pyenv)

This project requires Python 3.12 (`requires-python = ">=3.12, <3.13"`). The
exact version is pinned in `.python-version`, so pyenv and uv agree on it.

```sh
brew install pyenv
pyenv install            # builds the version pinned in .python-version
pyenv global 3.12.9      # optional: default interpreter outside this repo
```

Put the shims on `PATH` in `~/.zshenv` (every shell) and initialise pyenv in
`~/.zshrc` (interactive shells):

```sh
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/shims:$PATH"
eval "$(pyenv init -)"
```

`[tool.uv]` in `pyproject.toml` pins uv to the pyenv interpreter
(`python-preference = "only-system"`, `python-downloads = "never"`), so uv never
silently downloads a second, unpinned Python.

### 2. Dependencies

Install [uv](https://docs.astral.sh/uv/), then:

```sh
uv sync
```

### 3. TLS roots

`certifi` and `virtualenv` are pinned at versions carrying the fix for the
October 2026 eMudhra/emSign CA incident
(<https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576>).
Keep `pip >= 26.2.2` and `certifi >= 2026.10.19` in any environment you create
outside uv.

### 4. Models and assets

Only one model has to be fetched by hand. The other two are pulled
automatically from Hugging Face the first time they run.

| Asset | How it is obtained |
| --- | --- |
| Moonshine STT model | Downloaded explicitly — see below. |
| `nvidia/Nemotron-3-Diarization` | Downloaded by `transformers` on the first run of the diarization stage. |
| Kokoro voices (`hexgrad/Kokoro-82M`) | Downloaded by `kokoro` the first time the voice is synthesised. |

Download the Moonshine transcription model:

```sh
uv run moonshine-voice download --stt --language en
```

The command prints a `Downloaded model path:` line. Copy that path — the
client needs it at runtime.

### 5. Environment variables

| Variable | Needed by | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | `main.py` | API key for the OpenRouter chat-completions call. The server raises `ValueError` on the first request if it is missing. |
| `MOONSHINE_MODEL_PATH` | `client.py` | Path to the downloaded Moonshine model. Read with `os.environ[...]`, so the client fails to start if it is missing. |

## Running

Two terminals.

**Terminal 1 — the assistant server:**

```sh
export OPENROUTER_API_KEY=sk-or-...
uv run fastapi run main.py
```

It serves on `http://0.0.0.0:8000`. The client is hard-wired to
`http://127.0.0.1:8000` (`ApiConfig` in `lib/api_sdk.py`).

**Terminal 2 — the client pipelines:**

```sh
export MOONSHINE_MODEL_PATH=/path/to/downloaded/model
uv run python client.py
```

Speak, and the assistant answers out loud. On macOS the first run will ask for
microphone access.

To keep secrets out of your shell history, put them in a `.env` file (it is
git-ignored) and start the server with:

```sh
uv run uvicorn main:app --env-file .env
```

Note that `fastapi run` does **not** load `.env` on its own — only the
`--env-file` flag does.

## Configuration

The knobs currently live as module-level constants in `main.py`:

| Constant | Value | What it controls |
| --- | --- | --- |
| `MODEL` | `google/gemini-2.5-flash-lite` | The chat model. |
| `MAX_TOKENS` | `150` | Hard cap on the reply length. |
| `TIMEOUT` | `5` | OpenRouter request timeout, in seconds. |
| `VOICE` | `af_heart` | Kokoro voice. |
| `LANG_CODE` | `a` | Kokoro language (American English). |
| `SAMPLE_RATE` | `24000` | Playback sample rate. |
| `AGENT_SPEAKER` | `1` | Speaker slot treated as the agent, and therefore ignored. |

The client-side capture settings live in `AudioPipelineConfig`
(`lib/audio_pipeline.py`): 16 kHz, mono, float32, 1600-sample blocks.

## Development

```sh
uv run pytest                                     # tests
uv run pytest --cov=lib --cov-report=term-missing # with coverage
uv run ruff check . && uv run ruff format .       # lint and format
uv run pre-commit run --all-files                 # pre-commit hooks
```

Tests currently cover the segment overlap math and the event aggregation
pipeline (`tests/test_event_aggregation_pipeline.py`).

## Known limitations

- **The chat history is a single in-memory list.** The server keeps the session's
  messages in a module-level `Chat` object (`global_chat` in `main.py`, backed
  by `lib/chat.py`), shared by every speaker, and it is lost whenever the
  server restarts. There is no persistence layer yet.
- **Aggregation can drop a transcript.** The aggregation stage flushes all
  pending ASR and diarization segments as soon as it publishes one aggregated
  event, so a transcript whose speaker segment has not closed yet can be
  discarded along with it. The code also assumes ASR events always arrive
  after diarization events for the same span — watermarking would be the fix
  for out-of-order arrival.
- **The loop guard depends on speaker numbering.** Diarizer slots are numbered
  in order of first arrival, so `AGENT_SPEAKER = 1` means "the second speaker
  to talk". The assistant only stops answering itself if it happens to take
  that slot.
- **No graceful shutdown in the client.** `client.py` has a TODO for stop-event
  handling, and because the stage processes are spawned rather than daemonic,
  stopping the client can leave them running.
- **No tool calling.** The model can only answer with text.

## Roadmap

| # | Item | Status |
| --- | --- | --- |
| 0 | Smooth ASR | Done — Moonshine streaming transcriber. |
| 1 | Decision layer | Done — OpenRouter completion over the session chat history, spoken with Kokoro. |
| 2 | Tool calling layer | Not started. |
| 3 | Memory persistence | Not started. |
