# Roadmap

0. Smooth ASR
1. Decision layer
2. Tool calling layer
3. Memory persistence

# Installation

## Install Dependencies
Install uv

Run `uv sync`

## Download audio model

uv run moonshine-voice download --stt --language en

Note down the model path

export MOONSHINE_MODEL_PATH=path_to_your_model