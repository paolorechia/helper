from fastapi import FastAPI
from lib.openrouter import OpenRouterProvider

app = FastAPI()

open_router_provider = OpenRouterProvider("nvidia/nemotron-3.5-lightning:free")

chat = []


@app.post("/")
async def root(body: dict):
    if transcription := body.get("data", {}).get("transcription", None):
        print(f"got text: {transcription}")
        chat.append(f"user: {transcription}")
        model_reply = open_router_provider.generate(chat)
        print(f"model: {model_reply}")
        chat.append(model_reply)
    return {"chat": chat}
