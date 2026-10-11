import numpy as np
import sounddevice as sd
from fastapi import FastAPI
from kokoro import KPipeline
import uuid

from lib.openrouter import OpenRouterProvider
from lib.chat import Chat

SAMPLE_RATE = 24000
MAX_TOKENS = 150
TIMEOUT = 5
SESSION_ID = str(uuid.uuid4())
LANG_CODE = "a"  # American english, use English as models work better
MODEL = "google/gemini-2.5-flash-lite"  # Use a low latency model
VOICE = "af_heart"

DEFAULT_PROMPT = """You're an AI assistant.
The user is dictating you messages through an ASR model. Expect errors from the transcription model.
Below you'll have the entire chat history from this session.

Try to respond as succintly and naturally as possible, assume this is a voice chat.

USE ONLY ONE SENTENCE AT A TIME

EXCEPT WHEN EXPLICITLY ASKED OTHERWISE BY THE USER.

Try to keep word count as low as possible, and let user guide the direction of the chat.

When facing with ambiguity, ask the user back with the least amount of words, like a human.

NEVER ULTRAPASS 150 characters in a single response, your response will be hard limited.

IF THE SENTENCE IS GIBBERISH, ASK THE USER TO REPEAT. DON'T TRY TO GUESS THE MEANING.
DON'T TRY TO INTERPRET THE SENTENCE IF IT'S NOT CLEAR.
ASK FOR CLARIFICATIONS.

IF YOU MADE A QUESTION, STOP IMMEDIATELY.

DON'T JUSTIFY YOUR QUESTION. MAKE IT AS A NATURAL CONVERSATION AS POSSIBLE.

IF YOU WERE ASKED MULTIPLE QUESTIONS, FOCUS ONLY ONE THE FIRST ONE, UNLESS THEY'RE INTIMATELY CONNECTED.
"""


app = FastAPI()

pipeline = KPipeline(lang_code=LANG_CODE)

open_router_provider = OpenRouterProvider(MODEL, MAX_TOKENS, TIMEOUT)

global_chat = Chat()
global_chat.add_system_instruction(DEFAULT_PROMPT)

@app.post("/")
async def root(body: dict):
    if transcription := body.get("data", {}).get("transcription", None):
        global_chat.add_user_message(transcription)
        messages = global_chat.to_openai_prompt()
        print("Calling open router...")
        model_reply = open_router_provider.generate(messages, SESSION_ID)

        global_chat.add_model_response(model_reply)
        print("Converting text to speech...")
        generator = pipeline(model_reply, voice=VOICE, speed=1.0)

        audio_chunks = []
        for _, _, audio in generator:
            if audio is not None:
                audio_chunks.append(audio)
                
        if not audio_chunks:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
            
        # Concatena os arrays NumPy diretamente na memória
        full_audio = np.concatenate(audio_chunks)
        
        # sd.play envia o áudio diretamente para o CoreAudio do macOS em background.
        # O FastAPI responde imediatamente enquanto o som começa a tocar.
        sd.play(full_audio, SAMPLE_RATE)
        
    return {"chat": global_chat.to_openai_prompt()}
